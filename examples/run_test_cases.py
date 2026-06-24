import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import foundation_core as fcore
import matplotlib.pyplot as plt
import io
import base64
import numpy as np

# Define the 5 cases
cases = [
    {
        "name": "Case 1: Baseline Safe Design (Stiff Soil, Moderate Load)",
        "desc": "A robust layout in compacted soil. Both limit equilibrium and non-linear checks should easily pass.",
        "params": {
            "applied_force_n": 5000, "eccentricity_m": 0.1, "passive_zone_factor": 1.5,
            "number_of_piles": 8, "n_rows": 4, "spacing_m": 0.3,
            "diameter_m": 0.05, "embedded_length_m": 1.5,
            "soil_cu_pa": 120000, "soil_gamma": 20000, "soil_eps50": 0.005,
            "steel_sy_pa": 250e6
        }
    },
    {
        "name": "Case 2: The Serviceability Trap (Flexible Piles in Soft Soil)",
        "desc": "Piles are too thin for the soft soil. Broms (Limit Equilibrium) might pass, but BNWF will fail due to excessive lateral deflection.",
        "params": {
            "applied_force_n": 2000, "eccentricity_m": 0.1, "passive_zone_factor": 1.5,
            "number_of_piles": 4, "n_rows": 2, "spacing_m": 0.3,
            "diameter_m": 0.015, "embedded_length_m": 2.0,
            "soil_cu_pa": 30000, "soil_gamma": 19000, "soil_eps50": 0.015,
            "steel_sy_pa": 250e6
        }
    },
    {
        "name": "Case 3: Structural Failure (High Bending Moment)",
        "desc": "The soil provides strong resistance, but the extreme load height causes huge bending moments, yielding the steel.",
        "params": {
            "applied_force_n": 15000, "eccentricity_m": 0.5, "passive_zone_factor": 1.5,
            "number_of_piles": 6, "n_rows": 3, "spacing_m": 0.3,
            "diameter_m": 0.02, "embedded_length_m": 1.0,
            "soil_cu_pa": 120000, "soil_gamma": 20000, "soil_eps50": 0.005,
            "steel_sy_pa": 250e6
        }
    },
    {
        "name": "Case 4: Axial Pullout Failure (Insufficient Embedment)",
        "desc": "Tall overturning moment creates massive uplift on the rear pile rows. The embedment length is too short to resist pullout friction.",
        "params": {
            "applied_force_n": 8000, "eccentricity_m": 0.8, "passive_zone_factor": 1.5,
            "number_of_piles": 4, "n_rows": 2, "spacing_m": 0.3,
            "diameter_m": 0.03, "embedded_length_m": 0.3,
            "soil_cu_pa": 60000, "soil_gamma": 16000, "soil_eps50": 0.010,
            "steel_sy_pa": 250e6
        }
    },
    {
        "name": "Case 5: Catastrophic Physical Instability (Waterlogged Soil)",
        "desc": "Extreme load in mud with zero cohesion. The piles plow through the soil without resistance. Highlights the solver's non-convergence safety net.",
        "params": {
            "applied_force_n": 25000, "eccentricity_m": 0.1, "passive_zone_factor": 1.5,
            "number_of_piles": 8, "n_rows": 4, "spacing_m": 0.3,
            "diameter_m": 0.02, "embedded_length_m": 1.0,
            "soil_cu_pa": 10000, "soil_gamma": 18500, "soil_eps50": 0.020,
            "steel_sy_pa": 250e6
        }
    }
]

def run_all_cases():
    print("="*60)
    print(" FOUNDATION ANALYSIS TOOLKIT - 5 EDUCATIONAL TEST CASES")
    print("="*60)
    
    for i, case in enumerate(cases):
        print(f"\n[{i+1}/5] {case['name']}")
        print(f"Goal: {case['desc']}")
        print("-" * 50)
        
        p = case["params"]
        
        # 1. Evaluate Broms
        res_broms = fcore.evaluate_capacity_broms(
            applied_force_n=p["applied_force_n"], 
            eccentricity_m=p["eccentricity_m"], 
            passive_zone_factor=p["passive_zone_factor"],
            number_of_piles=p["number_of_piles"], 
            diameter_m=p["diameter_m"], 
            embedded_length_m=p["embedded_length_m"],
            soil_cu_pa=p["soil_cu_pa"], 
            steel_sy_pa=p["steel_sy_pa"]
        )
        
        b_appr = res_broms.get('soil_sf', 0) >= 2.0 and res_broms.get('steel_sf', 0) >= 2.0
        print(f"  [BROMS METHOD] Satisfied: {b_appr}")
        print(f"    - Geotechnical SF: {res_broms.get('soil_sf', 0):.2f}")
        print(f"    - Structural SF:   {res_broms.get('steel_sf', 0):.2f}")
        
        # 2. Evaluate FEM / BNWF
        try:
            res_fem = fcore.evaluate_frame_capacity(
                applied_force_n=p["applied_force_n"], 
                load_application_height_m=p["eccentricity_m"],
                num_rows=p["n_rows"], 
                spacing_between_rows_m=p["spacing_m"], 
                total_piles=p["number_of_piles"],
                diameter_m=p["diameter_m"], 
                length_m=p["embedded_length_m"],
                cu_pa=p["soil_cu_pa"], 
                gamma=p["soil_gamma"], 
                eps50=p["soil_eps50"],
                sy_steel_pa=p["steel_sy_pa"],
                global_safety_factor=2.0, 
                deflection_limit_mm=5.0,
                failure_criterion="von Mises"
            )
            
            f_appr = res_fem['overall_approval']
            print(f"  [BNWF METHOD] Satisfied: {f_appr}")
            print(f"    - Max Deflection: {res_fem['max_deflection_mm']:.2f} mm")
            print(f"    - Structural SF:  {res_fem['real_structural_sf']:.2f}")
            print(f"    - Pullout SF:     {res_fem['real_pullout_sf']:.2f}")
            
        except fcore.FoundationAnalysisError as e:
            res_fem = {"overall_approval": False, "max_deflection_mm": float('inf'), "real_structural_sf": 0, "real_pullout_sf": 0}
            print(f"  [BNWF METHOD] FAILED TO CONVERGE")
            print(f"    - Reason: Physical Instability / Singular Matrix")
            print(f"    - Details: {str(e)}")
            
        print("="*60)
        
        # --- GENERATE HTML REPORT ---
        print("  Generating HTML Report...")
        
        # 3. Layout Diagram
        fig_layout = plt.figure(figsize=(6, 6))
        p_row = [p["number_of_piles"] // p["n_rows"] + (1 if x < p["number_of_piles"] % p["n_rows"] else 0) for x in range(p["n_rows"])]
        start_y = -((p["n_rows"] - 1) * p["spacing_m"]) / 2
        for r_idx, count in enumerate(p_row):
            y = start_y + r_idx * p["spacing_m"]
            start_x = -((count - 1) * p["spacing_m"]) / 2
            plt.plot([start_x, start_x + (count-1)*p["spacing_m"]], [y, y], color='gray', linestyle='--', zorder=1)
            for j in range(count):
                x = start_x + j * p["spacing_m"]
                plt.gca().add_patch(plt.Circle((x, y), p["diameter_m"]/2, color='#0052cc', ec='black', zorder=2))
        
        if start_y - p["spacing_m"] < 0:
            plt.arrow(0, start_y - p["spacing_m"]*1.5, 0, p["spacing_m"], head_width=p["spacing_m"]*0.2, head_length=p["spacing_m"]*0.2, fc='red', ec='red')
        plt.axis('equal')
        plt.title('Pile Layout Map')
        plt.xlabel('X (m)'); plt.ylabel('Y (m)')
        plt.grid(True, linestyle=':', alpha=0.6)
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        plt.close(fig_layout)
        b64_layout = base64.b64encode(buf.getvalue()).decode('utf-8')
        
        # 4. Stress Profile
        try:
            stress_data = fcore.compute_pile_stresses(
                applied_force_n=p["applied_force_n"], load_application_height_m=p["eccentricity_m"],
                num_rows=p["n_rows"], spacing_between_rows_m=p["spacing_m"], total_piles=p["number_of_piles"],
                diameter_m=p["diameter_m"], length_m=p["embedded_length_m"],
                cu_pa=p["soil_cu_pa"], gamma=p["soil_gamma"], eps50=p["soil_eps50"],
                global_safety_factor=2.0, failure_criterion="von Mises"
            )
            
            # Simple custom plot for script
            Z = stress_data["Z"]; eq_stress = stress_data["equivalent_critical"]
            fig_stress, ax = plt.subplots(figsize=(5, 6))
            ax.plot(eq_stress, Z, 'purple', linewidth=2, label="Equivalent Stress")
            sy_mpa = p["steel_sy_pa"]/1e6
            ax.axvline(sy_mpa, color='red', linestyle='--', label='Yielding (Sy)')
            if np.max(eq_stress) > sy_mpa:
                ax.fill_betweenx(Z, sy_mpa, eq_stress, where=(eq_stress > sy_mpa), color='red', alpha=0.3)
            ax.invert_yaxis()
            ax.set_xlabel('Stress (MPa)')
            ax.set_ylabel('Depth (m)')
            ax.set_title('von Mises Equivalent Stress')
            ax.grid(True, linestyle=':', alpha=0.6)
            ax.legend()
            
            buf = io.BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight')
            plt.close(fig_stress)
            b64_stress = base64.b64encode(buf.getvalue()).decode('utf-8')
        except:
            b64_stress = ""

        # Build HTML
        html = f"""
        <html><head><style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f4f4f4; color: #333; margin: 40px; }}
            .container {{ background: white; padding: 40px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); max-width: 1000px; margin: auto; }}
            h1, h2, h3 {{ color: #00215e; }}
            h1 {{ border-bottom: 3px solid #0052cc; padding-bottom: 10px; }}
            .metric {{ display: inline-block; background: #eef2f5; padding: 10px 20px; border-radius: 6px; margin: 5px; border-left: 4px solid #0052cc; font-weight: bold; }}
            .pass {{ border-left-color: #2ca02c; color: #1e711e; }}
            .fail {{ border-left-color: #d62728; color: #9c1515; }}
            img {{ max-width: 100%; border: 1px solid #ddd; border-radius: 4px; margin-top: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }}
        </style></head><body>
        <div class="container">
            <h1>{case['name']}</h1>
            <p>Generated by <b>Foundation Analysis Toolkit (Test Runner)</b></p>
            
            <h2>1. Method 1: Limit Equilibrium (Broms)</h2>
            <p>Status: <span class="metric {'pass' if b_appr else 'fail'}">{'Satisfied' if b_appr else 'Failed checks'}</span></p>
            <ul>
                <li>Geotechnical Safety Factor: {res_broms.get('soil_sf', 0):.2f}</li>
                <li>Structural Safety Factor: {res_broms.get('steel_sf', 0):.2f}</li>
            </ul>
            
            <h2>2. Method 2: 1D Beam-on-Nonlinear-Winkler-Foundation</h2>
            <p>Status: <span class="metric {'pass' if res_fem.get('overall_approval') else 'fail'}">{'Satisfied' if res_fem.get('overall_approval') else 'Failed checks'}</span></p>
            <ul>
                <li>Max Deflection: {res_fem.get('max_deflection_mm', 0):.2f} mm</li>
                <li>Structural Safety Factor: {res_fem.get('real_structural_sf', 0):.2f}</li>
                <li>Pullout Safety Factor: {res_fem.get('real_pullout_sf', 0):.2f}</li>
            </ul>
            
            <h2>3. Layout Diagram</h2>
            <img src="data:image/png;base64,{b64_layout}" alt="Layout Map">
            
            <h2>4. Stress Profile</h2>
            {f'<img src="data:image/png;base64,{b64_stress}" alt="Stress Profile">' if b64_stress else '<p>Failed to compute stresses (structural instability).</p>'}
        </div>
        </body></html>
        """
        
        report_path = os.path.join(os.path.dirname(__file__), f"Report_Case_{i+1}.html")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"  Saved report to {report_path}\n")

if __name__ == "__main__":
    run_all_cases()
