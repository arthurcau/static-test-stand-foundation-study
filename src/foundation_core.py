"""
Core Logical Module for Deep Foundation Analysis.
Author: Arthur E. Cau @ Unicamp - 2026

Designed following strict software paradigms:
- Separation of Concerns (No I/O or plotting in the core).
- Fixed bounds on iterative methods.
- Strict type hinting and validation.
- Stateless, pure functions.
"""

import math
import numpy as np
from typing import Tuple, Dict, Any

class FoundationAnalysisError(Exception):
    """Custom exception for numerical or physical instability during analysis."""
    pass

def circular_section_modulus(diameter_m: float) -> float:
    if diameter_m <= 0: raise ValueError("Diameter must be positive.")
    return math.pi * diameter_m**3 / 32.0

def l_angle_section_modulus(side_m: float) -> float:
    if side_m <= 0: raise ValueError("Side length must be positive.")
    thickness_m = side_m / 8.0
    vertical_leg_area = side_m * thickness_m
    y_vertical_leg = side_m / 2.0
    
    horizontal_leg_area = (side_m - thickness_m) * thickness_m
    y_horizontal_leg = thickness_m / 2.0
    
    total_area = vertical_leg_area + horizontal_leg_area
    y_cg = (vertical_leg_area * y_vertical_leg + horizontal_leg_area * y_horizontal_leg) / total_area
    
    ix_vertical_leg = (thickness_m * side_m**3 / 12.0 + vertical_leg_area * (y_vertical_leg - y_cg) ** 2)
    ix_horizontal_leg = ((side_m - thickness_m) * thickness_m**3 / 12.0 + horizontal_leg_area * (y_cg - y_horizontal_leg) ** 2)
    
    ix_total = ix_vertical_leg + ix_horizontal_leg
    y_max = max(y_cg, side_m - y_cg)
    return ix_total / y_max

def design_pile_broms(
    total_load_n: float, eccentricity_m: float, passive_zone_factor: float, number_of_piles: int,
    embedded_length_m: float, soil_cu_pa: float, steel_sy_pa: float, profile: str = "CIRCULAR",
    fs_soil: float = 4.0, fs_steel: float = 2.0, max_diameter_m: float = 2.0, step_mm: int = 1,
) -> dict:
    if number_of_piles <= 0: raise ValueError("Number of piles must be greater than zero.")
    if embedded_length_m <= 0: raise ValueError("Embedded length must be greater than zero.")
    if total_load_n <= 0: raise ValueError("Total load must be greater than zero.")
    
    profile = profile.upper()
    if profile not in {"CIRCULAR", "L_PROFILE"}: raise ValueError("Profile must be 'CIRCULAR' or 'L_PROFILE'.")

    load_per_pile_n = total_load_n / number_of_piles
    geotechnical_load_n = load_per_pile_n * fs_soil
    structural_load_n = load_per_pile_n * fs_steel

    max_diameter_mm = int(max_diameter_m * 1000)

    for diameter_mm in range(step_mm, max_diameter_mm + step_mm, step_mm):
        diameter_m = diameter_mm / 1000.0
        if embedded_length_m <= passive_zone_factor * diameter_m:
            return {"approved": False, "reason": "Insufficient embedded length.", "diameter_m": diameter_m}

        soil_resistance_n = 9.0 * soil_cu_pa * diameter_m * (embedded_length_m - passive_zone_factor * diameter_m)
        
        if profile == "CIRCULAR":
            section_modulus_m3 = circular_section_modulus(diameter_m)
            thickness_m = 0.0
        else:
            section_modulus_m3 = l_angle_section_modulus(diameter_m)
            thickness_m = diameter_m / 8.0

        yield_moment_nm = section_modulus_m3 * steel_sy_pa
        a = 0.5 / (9.0 * soil_cu_pa * diameter_m)
        b = eccentricity_m + passive_zone_factor * diameter_m
        c = -yield_moment_nm
        delta = b**2 - 4.0 * a * c
        structural_resistance_n = (-b + math.sqrt(delta)) / (2.0 * a) if delta >= 0 else 0.0

        soil_approved = soil_resistance_n >= geotechnical_load_n
        steel_approved = structural_resistance_n >= structural_load_n

        if soil_approved and steel_approved:
            soil_utilization = geotechnical_load_n / soil_resistance_n
            steel_utilization = structural_load_n / structural_resistance_n
            limiting_criterion = "Geotechnical" if soil_utilization > steel_utilization else "Structural"
            return {
                "approved": True, "profile": profile, "diameter_m": diameter_m, "thickness_m": thickness_m,
                "limiting_criterion": limiting_criterion, "load_per_pile_n": load_per_pile_n,
                "soil_resistance_n": soil_resistance_n, "structural_resistance_n": structural_resistance_n,
                "soil_utilization": soil_utilization, "steel_utilization": steel_utilization,
            }
    return {"approved": False, "reason": "Required dimension exceeds the specified limit."}

def evaluate_capacity_broms(
    applied_force_n: float, eccentricity_m: float, passive_zone_factor: float,
    number_of_piles: int, diameter_m: float, embedded_length_m: float,
    soil_cu_pa: float, steel_sy_pa: float, profile: str = "CIRCULAR"
) -> dict:
    load_per_pile_n = applied_force_n / number_of_piles

    if embedded_length_m <= passive_zone_factor * diameter_m:
        return {"approved": False, "reason": "Insufficient embedded length."}

    soil_resistance_n = 9.0 * soil_cu_pa * diameter_m * (embedded_length_m - passive_zone_factor * diameter_m)
    
    if profile == "CIRCULAR":
        section_modulus_m3 = circular_section_modulus(diameter_m)
    else:
        section_modulus_m3 = l_angle_section_modulus(diameter_m)

    yield_moment_nm = section_modulus_m3 * steel_sy_pa
    a = 0.5 / (9.0 * soil_cu_pa * diameter_m)
    b = eccentricity_m + passive_zone_factor * diameter_m
    c = -yield_moment_nm
    delta = b**2 - 4.0 * a * c
    structural_resistance_n = (-b + math.sqrt(delta)) / (2.0 * a) if delta >= 0 else 0.0

    soil_sf = soil_resistance_n / load_per_pile_n if load_per_pile_n > 0 else float('inf')
    steel_sf = structural_resistance_n / load_per_pile_n if load_per_pile_n > 0 else float('inf')

    return {
        "approved": True,
        "soil_resistance_n": soil_resistance_n,
        "structural_resistance_n": structural_resistance_n,
        "soil_sf": soil_sf,
        "steel_sf": steel_sf
    }

def beam_element_stiffness_matrix(E: float, I: float, Le: float) -> np.ndarray:
    K = np.zeros((4, 4))
    coef = (E * I) / (Le**3)
    K[0,0] = 12 * coef; K[0,1] = K[1,0] = 6 * Le * coef; K[0,2] = K[2,0] = -12 * coef; K[0,3] = K[3,0] = 6 * Le * coef
    K[1,1] = 4 * Le**2 * coef; K[1,2] = K[2,1] = -6 * Le * coef; K[1,3] = K[3,1] = 2 * Le**2 * coef
    K[2,2] = 12 * coef; K[2,3] = K[3,2] = -6 * Le * coef; K[3,3] = 4 * Le**2 * coef
    return K

def matlock_reese_py_curve(y: float, z: float, D: float, cu_pa: float, gamma: float, eps50: float) -> float:
    y_abs = max(abs(y), 1e-6)
    J = 0.5
    X_R = (6 * D) / ((gamma * D / cu_pa) + J) if ((gamma * D / cu_pa) + J) > 0 else 0
    p_ult = cu_pa * D * (3.0 + (gamma * z / cu_pa) + (J * z / D)) if z < X_R else 9.0 * cu_pa * D
    y_50 = 2.5 * eps50 * D
    p = 0.5 * p_ult * (y_abs / y_50)**(1/3) if y_abs <= 8 * y_50 else p_ult
    return p / y_abs

def solve_1d_fem(
    shear_force_n: float, D: float, L: float, E_steel: float, 
    cu_pa: float, gamma: float, eps50: float, top_condition: str
) -> Tuple[np.ndarray, np.ndarray, float]:
    I = (np.pi * D**4) / 64.0
    n_ele = 40; Le = L / n_ele; n_nodes = n_ele + 1; dofs = 2 * n_nodes

    K_global_struct = np.zeros((dofs, dofs))
    for i in range(n_ele):
        K_global_struct[2*i:2*i+4, 2*i:2*i+4] += beam_element_stiffness_matrix(E_steel, I, Le)

    U_old = np.zeros(dofs)
    max_iterations = 500
    converged = False

    for _ in range(max_iterations):
        K_sys = np.copy(K_global_struct)
        F_vec = np.zeros(dofs)
        for i in range(n_nodes):
            E_s = matlock_reese_py_curve(U_old[2*i], i*Le, D, cu_pa, gamma, eps50)
            # Add a small regularization term to avoid absolute zero lateral stiffness
            K_sys[2*i, 2*i] += E_s * (Le if 0 < i < n_ele else Le/2.0) + 1e-6

        F_vec[0] = shear_force_n
        if top_condition == "FIXED":
            K_sys[1, :] = 0; K_sys[:, 1] = 0; K_sys[1, 1] = 1.0; F_vec[1] = 0.0

        try:
            U_calc = np.linalg.solve(K_sys, F_vec)
        except (ValueError, np.linalg.LinAlgError):
            raise FoundationAnalysisError("Numerical collapse: matrix became singular due to zero soil stiffness (structure yielded).")

        # Under-relaxation to stabilize the non-linear soil spring iteration
        U_new = 0.2 * U_calc + 0.8 * U_old

        if np.max(np.abs(U_new - U_old)) < 1e-6:
            converged = True
            break
        U_old = U_new

    if not converged:
        raise FoundationAnalysisError("FEM solver failed to converge (excessive deflections).")

    Moments = np.zeros(n_nodes)
    for i in range(n_ele):
        u = U_new[2*i:2*i+4]
        Moments[i] += E_steel * I * (-6/Le**2 * u[0] - 4/Le * u[1] + 6/Le**2 * u[2] - 2/Le * u[3])
    return U_new, Moments, I

def evaluate_frame_capacity(
    applied_force_n: float, load_application_height_m: float,
    num_rows: int, spacing_between_rows_m: float, total_piles: int,
    diameter_m: float, length_m: float,
    cu_pa: float, gamma: float, eps50: float, sy_steel_pa: float,
    global_safety_factor: float = 2.0, deflection_limit_mm: float = 5.0,
    failure_criterion: str = "von Mises"
) -> dict:
    if total_piles % num_rows != 0: raise ValueError("Total piles must be a multiple of the number of rows.")

    E_steel = 200e9
    Area = (np.pi * diameter_m**2) / 4.0
    W_el = (np.pi * diameter_m**3) / 32.0

    if cu_pa <= 30e3: alpha = 0.8
    elif cu_pa >= 100e3: alpha = 0.5
    else: alpha = 0.8 - 0.3 * ((cu_pa - 30e3) / 70e3)

    piles_per_row = total_piles // num_rows
    sum_x_squared = sum(piles_per_row * ((i - (num_rows - 1) / 2.0) * spacing_between_rows_m)**2 for i in range(num_rows))
    x_max = max(np.abs([(i - (num_rows - 1) / 2.0) * spacing_between_rows_m for i in range(num_rows)])) if num_rows > 1 else 0.0

    nominal_shear = applied_force_n / total_piles
    nominal_overturning_moment = applied_force_n * load_application_height_m
    nominal_axial_load = (nominal_overturning_moment * x_max) / sum_x_squared if num_rows > 1 else 0.0

    try:
        U_els, Mom_els, _ = solve_1d_fem(nominal_shear, diameter_m, length_m, E_steel, cu_pa, gamma, eps50, "PINNED")
        max_deflection_mm = U_els[0] * 1000
        nominal_bending_moment = np.max(np.abs(Mom_els))
    except FoundationAnalysisError:
        max_deflection_mm = float('inf')
        nominal_bending_moment = float('inf')

    if num_rows == 1: nominal_bending_moment += (nominal_overturning_moment / total_piles)

    nominal_bending_stress = nominal_bending_moment / W_el
    nominal_axial_stress = nominal_axial_load / Area
    nominal_combined_stress = nominal_bending_stress + nominal_axial_stress

    effective_L = max(0.0, length_m - (1.5 * diameter_m))
    pullout_capacity = alpha * cu_pa * (np.pi * diameter_m * effective_L)

    real_structural_sf = sy_steel_pa / nominal_combined_stress if nominal_combined_stress > 0 else float('inf')
    real_pullout_sf = pullout_capacity / nominal_axial_load if nominal_axial_load > 0 else float('inf')

    design_F = applied_force_n * global_safety_factor
    design_shear = design_F / total_piles
    design_overturning_moment = design_F * load_application_height_m
    design_axial_load = (design_overturning_moment * x_max) / sum_x_squared if num_rows > 1 else 0.0

    try:
        _, Mom_uls, _ = solve_1d_fem(design_shear, diameter_m, length_m, E_steel, cu_pa, gamma, eps50, "PINNED")
        uls_bending_moment = np.max(np.abs(Mom_uls))
    except FoundationAnalysisError:
        uls_bending_moment = float('inf')

    if num_rows == 1: uls_bending_moment += (design_overturning_moment / total_piles)

    uls_bending_stress = uls_bending_moment / W_el
    uls_axial_stress = design_axial_load / Area
    
    # In extreme fibers, tau = 0. So von Mises and Tresca are identical: sigma_axial + sigma_bending
    uls_combined_stress = uls_bending_stress + uls_axial_stress
    uls_pullout_sf = pullout_capacity / design_axial_load if design_axial_load > 0 else float('inf')

    structural_check = uls_combined_stress < sy_steel_pa
    geotechnical_check = uls_pullout_sf >= 1.0 or num_rows == 1
    kinematic_check = max_deflection_mm <= deflection_limit_mm
    overall_approval = structural_check and geotechnical_check and kinematic_check

    return {
        "max_deflection_mm": max_deflection_mm,
        "real_structural_sf": real_structural_sf,
        "real_pullout_sf": real_pullout_sf,
        "structural_check": structural_check,
        "geotechnical_check": geotechnical_check,
        "overall_approval": overall_approval,
        "uls_combined_stress": uls_combined_stress,
        "design_axial_load": design_axial_load
    }

def compute_pile_stresses(
    applied_force_n: float, load_application_height_m: float,
    num_rows: int, spacing_between_rows_m: float, total_piles: int,
    diameter_m: float, length_m: float,
    cu_pa: float, gamma: float, eps50: float, global_safety_factor: float = 2.0,
    failure_criterion: str = "von Mises"
) -> dict:
    E_steel = 200e9
    Area = (np.pi * diameter_m**2) / 4.0
    W_el = (np.pi * diameter_m**3) / 32.0

    design_F = applied_force_n * global_safety_factor
    design_shear = design_F / total_piles
    design_overturning_moment = design_F * load_application_height_m

    piles_per_row = total_piles // num_rows
    sum_x_squared = sum(piles_per_row * ((i - (num_rows - 1) / 2.0) * spacing_between_rows_m)**2 for i in range(num_rows))
    x_max = max(np.abs([(i - (num_rows - 1) / 2.0) * spacing_between_rows_m for i in range(num_rows)])) if num_rows > 1 else 0.0

    design_axial_load = (design_overturning_moment * x_max) / sum_x_squared if num_rows > 1 else 0.0

    _, Mom_uls, _ = solve_1d_fem(design_shear, diameter_m, length_m, E_steel, cu_pa, gamma, eps50, "PINNED")

    if num_rows == 1: Mom_uls += (design_overturning_moment / total_piles)

    n_nodes = len(Mom_uls)
    Z = np.linspace(0, length_m, n_nodes)
    V_uls = np.gradient(Mom_uls, Z)

    Pa_to_MPa = 1e-6
    sigma_a = np.full(n_nodes, design_axial_load / Area) * Pa_to_MPa
    sigma_f = (np.abs(Mom_uls) / W_el) * Pa_to_MPa
    tau_max = ((4.0 / 3.0) * np.abs(V_uls) / Area) * Pa_to_MPa

    von_mises_edge = np.abs(sigma_a) + sigma_f
    von_mises_center = np.sqrt(sigma_a**2 + 3 * tau_max**2)
    von_mises_critical = np.maximum(von_mises_edge, von_mises_center)
    
    tresca_edge = np.abs(sigma_a) + sigma_f
    tresca_center = np.sqrt(sigma_a**2 + 4 * tau_max**2)
    tresca_critical = np.maximum(tresca_edge, tresca_center)

    if failure_criterion == "Tresca":
        equivalent_critical = tresca_critical
    else:
        equivalent_critical = von_mises_critical

    return {
        "Z": Z, "sigma_a": sigma_a, "sigma_f": sigma_f, "tau_max": tau_max,
        "equivalent_critical": equivalent_critical, "design_force_n": design_F
    }
