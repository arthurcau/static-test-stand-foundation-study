"""
Toolkit and GUI application for Deep Foundation Analysis.
Author: Arthur E. Cau @ Unicamp - 2026

Integrates the logical core, handles I/O, plotting, and exposes a Cross-Platform GUI.
"""

import csv
import sys
import os
import base64
from io import BytesIO
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import matplotlib.patches as mpatches
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import concurrent.futures

import foundation_core as fcore

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')

def load_materials(filename: str = os.path.join(DATA_DIR, 'materials.csv')) -> dict:
    materials = {}
    try:
        with open(filename, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                materials[row['key']] = {
                    "Sy": float(row['yield_strength_mpa']),
                    "desc": row['description']
                }
    except FileNotFoundError:
        print(f"Warning: {filename} not found.")
    return materials

def load_soils(filename: str = os.path.join(DATA_DIR, 'soils.csv')) -> dict:
    soils = {}
    try:
        with open(filename, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                soils[row['key']] = {
                    "Cu": float(row['undrained_shear_strength_kpa']),
                    "desc": row['description'],
                    "gamma": float(row['unit_weight_n_m3']),
                    "eps50": float(row['eps50'])
                }
    except FileNotFoundError:
        print(f"Warning: {filename} not found.")
    return soils

MATERIALS = load_materials()
SOILS = load_soils()

def plot_pile_stresses(data: dict, mat_desc: str, sy_mpa: float, criterion: str = "von Mises", show_plot: bool = True):
    Z = data["Z"]
    sigma_a = data["sigma_a"]
    sigma_f = data["sigma_f"]
    tau_max = data["tau_max"]
    eq_stress = data["equivalent_critical"]

    fig, (ax1, ax4) = plt.subplots(1, 2, figsize=(14, 7), sharey=True)
    fig.suptitle(f"Pile Stress Profiles ({mat_desc} - Sy = {sy_mpa} MPa)\nFactored Design Force = {data['design_force_n']/1000:.1f} kN", fontweight='bold')

    ax1.plot(sigma_f, Z, label=r'Bending ($\sigma_f$)', color='blue', linewidth=2)
    ax1.plot(sigma_a, Z, label=r'Axial ($\sigma_a$)', color='green', linestyle='--', linewidth=2)
    ax1.plot(tau_max, Z, label=r'Shear ($\tau_{max}$)', color='purple', linestyle='-.', linewidth=2)
    ax1.set_ylabel('Depth (m)')
    ax1.set_xlabel('Stress (MPa)')
    ax1.set_title('Stress Components')
    ax1.invert_yaxis()
    ax1.grid(True, linestyle='--', alpha=0.6)
    ax1.legend()

    ax4.plot(eq_stress, Z, 'purple', linewidth=2)
    ax4.axvline(sy_mpa, color='red', linestyle='--', label='Yielding (Sy)')
    if np.max(eq_stress) > sy_mpa:
        ax4.fill_betweenx(Z, sy_mpa, eq_stress, where=(eq_stress > sy_mpa), color='red', alpha=0.3)
    ax4.set_xlabel('Stress (MPa)')
    ax4.set_title(f'Equivalent Stress\n({criterion})')
    ax4.grid(True, linestyle=':', alpha=0.6)
    ax4.legend()
    
    plt.tight_layout()
    if show_plot:
        plt.show()
    return fig

class FoundationApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Foundation Analysis Toolkit")
        self.geometry("950x700")
        self.configure(padx=20, pady=20, bg="#ffffff")
        self.cancel_requested = False
        
        style = ttk.Style(self)
        if 'clam' in style.theme_names():
            style.theme_use('clam')
        
        style.configure('TFrame', background='#ffffff')
        style.configure('TLabel', background='#ffffff', font=('Segoe UI', 10))
        style.configure('TLabelframe', background='#ffffff')
        style.configure('TLabelframe.Label', background='#ffffff', font=('Segoe UI', 11, 'bold'), foreground='#333333')
        style.configure('TButton', font=('Segoe UI', 10, 'bold'), padding=6, background='#0052cc', foreground='white', borderwidth=0)
        style.map('TButton', background=[('active', '#0043a6')])
        
        style.configure('Danger.TButton', background='#cc0000', foreground='white')
        style.map('Danger.TButton', background=[('active', '#a60000')])
        
        style.configure('Success.TButton', background='#2ca02c', foreground='white')
        style.map('Success.TButton', background=[('active', '#228322')])
        
        style.configure('TProgressbar', background='#0052cc', troughcolor='#e0e0e0', borderwidth=0)

        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True)

        left_pane = ttk.Frame(main_frame)
        left_pane.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        right_pane = ttk.LabelFrame(main_frame, text="Pile Layout Visualization", padding=10)
        right_pane.pack(side=tk.RIGHT, fill=tk.Y, padx=(15, 0))

        self.canvas = tk.Canvas(right_pane, width=280, bg="#f9f9f9", highlightthickness=1, highlightbackground="#cccccc")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        frame_inputs = ttk.LabelFrame(left_pane, text="Input Parameters", padding=15)
        frame_inputs.pack(fill=tk.X, pady=(0, 15))

        # Force
        ttk.Label(frame_inputs, text="Applied Force (N):").grid(row=0, column=0, sticky=tk.W, pady=8)
        self.ent_force = ttk.Entry(frame_inputs, width=15, font=('Segoe UI', 10))
        self.ent_force.insert(0, "3000")
        self.ent_force.grid(row=0, column=1, padx=10, pady=8)

        # Height
        ttk.Label(frame_inputs, text="Load Height (m):").grid(row=1, column=0, sticky=tk.W, pady=8)
        self.ent_height = ttk.Entry(frame_inputs, width=15, font=('Segoe UI', 10))
        self.ent_height.insert(0, "0.05")
        self.ent_height.grid(row=1, column=1, padx=10, pady=8)

        # Soil
        ttk.Label(frame_inputs, text="Soil Type:").grid(row=0, column=2, sticky=tk.W, padx=(20, 0), pady=8)
        soil_descs = [s['desc'] for s in SOILS.values()]
        self.cbo_soil = ttk.Combobox(frame_inputs, values=soil_descs, state="readonly", width=22, font=('Segoe UI', 10))
        if soil_descs: self.cbo_soil.current(0)
        self.cbo_soil.grid(row=0, column=3, padx=10, pady=8)

        # Material
        ttk.Label(frame_inputs, text="Material Type:").grid(row=1, column=2, sticky=tk.W, padx=(20, 0), pady=8)
        mat_descs = [m['desc'] for m in MATERIALS.values()]
        self.cbo_material = ttk.Combobox(frame_inputs, values=mat_descs, state="readonly", width=22, font=('Segoe UI', 10))
        if mat_descs: self.cbo_material.current(0)
        self.cbo_material.grid(row=1, column=3, padx=10, pady=8)

        # Geometry
        ttk.Label(frame_inputs, text="Pile Diameter (m):").grid(row=2, column=0, sticky=tk.W, pady=8)
        self.ent_dia = ttk.Entry(frame_inputs, width=15, font=('Segoe UI', 10))
        self.ent_dia.insert(0, "0.010")
        self.ent_dia.grid(row=2, column=1, padx=10, pady=8)

        ttk.Label(frame_inputs, text="Pile Length (m):").grid(row=2, column=2, sticky=tk.W, padx=(20, 0), pady=8)
        self.ent_len = ttk.Entry(frame_inputs, width=15, font=('Segoe UI', 10))
        self.ent_len.insert(0, "0.50")
        self.ent_len.grid(row=2, column=3, padx=10, pady=8)

        # Group Layout
        ttk.Label(frame_inputs, text="Total Piles:").grid(row=3, column=0, sticky=tk.W, pady=8)
        self.ent_piles = ttk.Entry(frame_inputs, width=15, font=('Segoe UI', 10))
        self.ent_piles.insert(0, "8")
        self.ent_piles.grid(row=3, column=1, padx=10, pady=8)

        ttk.Label(frame_inputs, text="Number of Rows:").grid(row=3, column=2, sticky=tk.W, padx=(20, 0), pady=8)
        self.ent_rows = ttk.Entry(frame_inputs, width=15, font=('Segoe UI', 10))
        self.ent_rows.insert(0, "4")
        self.ent_rows.grid(row=3, column=3, padx=10, pady=8)

        ttk.Label(frame_inputs, text="Row Spacing (m):").grid(row=4, column=0, sticky=tk.W, pady=8)
        self.ent_spacing = ttk.Entry(frame_inputs, width=15, font=('Segoe UI', 10))
        self.ent_spacing.insert(0, "0.3")
        self.ent_spacing.grid(row=4, column=1, padx=10, pady=8)

        ttk.Label(frame_inputs, text="Target Safety Factor:").grid(row=4, column=2, sticky=tk.W, padx=(20, 0), pady=8)
        self.ent_sf = ttk.Entry(frame_inputs, width=15, font=('Segoe UI', 10))
        self.ent_sf.insert(0, "2.0")
        self.ent_sf.grid(row=4, column=3, padx=10, pady=8)

        ttk.Label(frame_inputs, text="Failure Criterion:").grid(row=5, column=0, sticky=tk.W, pady=8)
        self.cbo_criterion = ttk.Combobox(frame_inputs, values=["von Mises", "Tresca"], state="readonly", width=13, font=('Segoe UI', 10))
        self.cbo_criterion.current(0)
        self.cbo_criterion.grid(row=5, column=1, padx=10, pady=8)

        for entry in [self.ent_piles, self.ent_rows, self.ent_spacing, self.ent_dia, self.ent_sf]:
            entry.bind("<KeyRelease>", self.update_canvas)

        frame_btns = ttk.Frame(left_pane)
        frame_btns.pack(fill=tk.X, pady=(0, 15))

        ttk.Button(frame_btns, text="Evaluate (Broms)", command=self.run_eval_broms).pack(side=tk.LEFT, padx=3)
        ttk.Button(frame_btns, text="Evaluate (FEM/BNWF)", command=self.run_eval_fem).pack(side=tk.LEFT, padx=3)
        ttk.Button(frame_btns, text="Plot Stresses", command=self.run_plot).pack(side=tk.LEFT, padx=3)
        ttk.Button(frame_btns, text="Plot Design Map", command=self.run_length_diameter_map).pack(side=tk.LEFT, padx=3)
        ttk.Button(frame_btns, text="Save Report", style='Success.TButton', command=self.run_save_report).pack(side=tk.LEFT, padx=3)
        
        ttk.Button(frame_btns, text="Cancel", style='Danger.TButton', command=self.do_cancel).pack(side=tk.RIGHT, padx=3)

        self.progress = ttk.Progressbar(left_pane, orient=tk.HORIZONTAL, mode='determinate')
        self.progress.pack(fill=tk.X, pady=(0, 10))

        self.txt_console = tk.Text(left_pane, height=12, state=tk.DISABLED, bg="#1e1e1e", fg="#00ff00", font=("Consolas", 10), bd=0, padx=10, pady=10)
        self.txt_console.pack(fill=tk.BOTH, expand=True)

        self.after(200, self.update_canvas)

    def get_and_validate_inputs(self):
        try:
            f = float(self.ent_force.get())
            h = float(self.ent_height.get())
            d = float(self.ent_dia.get())
            l = float(self.ent_len.get())
            tot_piles = int(self.ent_piles.get())
            n_rows = int(self.ent_rows.get())
            spacing = float(self.ent_spacing.get())
            
            sf = float(self.ent_sf.get())
            criterion = self.cbo_criterion.get()
            
            if f <= 0: raise ValueError("Applied Force must be > 0.")
            if h <= 0: raise ValueError("Load Height must be > 0.")
            if d <= 0: raise ValueError("Pile Diameter must be > 0.")
            if l <= 0: raise ValueError("Pile Length must be > 0.")
            if tot_piles <= 0: raise ValueError("Total Piles must be > 0.")
            if n_rows <= 0: raise ValueError("Number of Rows must be > 0.")
            if spacing <= 0: raise ValueError("Row Spacing must be > 0.")
            if sf < 1.0: raise ValueError("Target Safety Factor must be >= 1.0.")
            
            if tot_piles % n_rows != 0:
                raise ValueError("Total number of piles must be divisible by the number of rows.")
                
            soil_desc = self.cbo_soil.get()
            mat_desc = self.cbo_material.get()
            if not soil_desc: raise ValueError("Soil type must be selected.")
            if not mat_desc: raise ValueError("Material type must be selected.")
            
            soil_id = next((k for k, v in SOILS.items() if v['desc'] == soil_desc), None)
            mat_id = next((k for k, v in MATERIALS.items() if v['desc'] == mat_desc), None)
            
            if not soil_id or not mat_id:
                raise ValueError("Invalid material or soil selection.")
                
            return f, h, d, l, tot_piles, n_rows, spacing, SOILS[soil_id], MATERIALS[mat_id], sf, criterion
        except ValueError as e:
            if "could not convert string to float" in str(e) or "invalid literal for int" in str(e):
                raise ValueError("Please enter valid numerical values.")
            raise e

    def update_canvas(self, event=None):
        try:
            tot_piles = int(self.ent_piles.get())
            n_rows = int(self.ent_rows.get())
            spacing = float(self.ent_spacing.get())
            d = float(self.ent_dia.get())
            if tot_piles <= 0 or n_rows <= 0 or spacing <= 0 or d <= 0: return
        except ValueError:
            return

        self.canvas.delete("all")
        self.update_idletasks()
        w = int(self.canvas.winfo_width())
        h = int(self.canvas.winfo_height())
        if w <= 1 or h <= 1:
            w, h = 280, 400

        piles_per_row = [tot_piles // n_rows + (1 if x < tot_piles % n_rows else 0) for x in range(n_rows)]
        max_piles = max(piles_per_row) if piles_per_row else 1
        
        real_width = (max_piles - 1) * spacing
        real_height = (n_rows - 1) * spacing
        pad = max(d * 3, spacing * 0.8)
        
        scale_x = w / (real_width + pad * 2) if (real_width + pad * 2) > 0 else 1.0
        scale_y = h / (real_height + pad * 2) if (real_height + pad * 2) > 0 else 1.0
        scale = min(scale_x, scale_y)
        
        cx, cy = w / 2, h / 2
        start_y = cy - (real_height / 2) * scale
        
        for i, count in enumerate(piles_per_row):
            y = start_y + i * spacing * scale
            start_x = cx - ((count - 1) * spacing / 2) * scale
            
            if count > 1:
                self.canvas.create_line(start_x, y, start_x + (count - 1) * spacing * scale, y, fill="#cccccc", dash=(4, 4))
                
            for j in range(count):
                x = start_x + j * spacing * scale
                r = max(4.0, (d / 2) * scale)
                self.canvas.create_oval(x-r, y-r, x+r, y+r, fill="#0052cc", outline="#00215e", width=2)
                
        arrow_y = start_y - pad * scale * 0.5
        self.canvas.create_line(cx, arrow_y - 30, cx, arrow_y, arrow=tk.LAST, fill="#cc0000", width=3)
        self.canvas.create_text(cx, arrow_y - 40, text="Applied Force", fill="#cc0000", font=("Segoe UI", 9, "bold"))
        
    def do_cancel(self):
        self.cancel_requested = True

    def log(self, message: str):
        self.txt_console.config(state=tk.NORMAL)
        self.txt_console.insert(tk.END, message + "\n")
        self.txt_console.see(tk.END)
        self.txt_console.config(state=tk.DISABLED)

    def fig_to_base64(self, fig):
        buf = BytesIO()
        fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        img_str = base64.b64encode(buf.read()).decode('utf-8')
        plt.close(fig)
        return img_str

    def run_eval_broms(self):
        try:
            self.cancel_requested = False
            self.progress['value'] = 0
            self.update()
            
            f, h, d, l, tot_piles, n_rows, spacing, soil, mat, sf, criterion = self.get_and_validate_inputs()

            self.log(f"\n--- Evaluating BROMS for {f} N ---")
            self.log("[METHOD]: Analytical Limit Equilibrium (Broms, 1964).")
            self.log(f"[LIMITATIONS]: SF={sf}, Criterion={criterion}")
            self.log("-" * 40)

            res = fcore.evaluate_capacity_broms(
                applied_force_n=f, eccentricity_m=h, passive_zone_factor=1.5,
                number_of_piles=tot_piles, diameter_m=d, embedded_length_m=l,
                soil_cu_pa=soil["Cu"]*1000, steel_sy_pa=mat["Sy"]*1e6
            )

            if not res.get("approved") and "reason" in res:
                self.log(f"Status: Failed - {res['reason']}")
            else:
                approved = res.get('soil_sf', 0) >= sf and res.get('steel_sf', 0) >= sf
                if approved:
                    self.log(f"Status: The configuration satisfies the preliminary factored checks (SF >= {sf}).")
                else:
                    self.log(f"Status: The configuration did not satisfy the factored checks (SF < {sf}).")
                self.log(f"Estimated ultimate lateral soil capacity: {res['soil_resistance_n']:.1f} N/pile")
                self.log(f"Estimated ultimate structural capacity: {res['structural_resistance_n']:.1f} N/pile")
                self.log(f"Geotechnical Safety Factor: {res['soil_sf']:.2f}")
                self.log(f"Structural Safety Factor: {res['steel_sf']:.2f}")
            self.log("=" * 40)
            
            self.progress['value'] = 100
            self.update()

        except Exception as e:
            messagebox.showerror("Invalid Input", str(e))

    def run_eval_fem(self):
        try:
            self.cancel_requested = False
            self.progress['value'] = 0
            self.update()
            
            f, h, d, l, tot_piles, n_rows, spacing, soil, mat, sf, criterion = self.get_and_validate_inputs()

            self.log(f"\n--- Evaluating FEM/BNWF for {f} N ---")
            self.log("[METHOD]: Finite Element Method (1D Beam on Elastic Foundation).")
            self.log("-" * 40)

            res = fcore.evaluate_frame_capacity(
                applied_force_n=f, load_application_height_m=h,
                num_rows=n_rows, spacing_between_rows_m=spacing, total_piles=tot_piles,
                diameter_m=d, length_m=l,
                cu_pa=soil["Cu"]*1000, gamma=soil["gamma"], eps50=soil["eps50"],
                sy_steel_pa=mat["Sy"]*1e6,
                global_safety_factor=sf,
                failure_criterion=criterion
            )

            if res['overall_approval']:
                self.log(f"Status: The configuration satisfies the preliminary nonlinear checks (SF >= {sf}).")
            else:
                if res['real_structural_sf'] < sf:
                    self.log("Status: Failed - Estimated combined stresses exceed the allowable structural limit.")
                elif res['real_pullout_sf'] < sf:
                    self.log("Status: Failed - Insufficient pullout capacity.")
                else:
                    self.log("Status: Failed - Non-convergent or excessive deflection.")

            self.log(f"Estimated service deflection: {res['max_deflection_mm']:.2f} mm")
            self.log(f"Structural Safety Factor: {res['real_structural_sf']:.2f}")
            self.log(f"Pullout Safety Factor: {res['real_pullout_sf']:.2f}")
            self.log("=" * 40)

            self.progress['value'] = 100
            self.update()

        except fcore.FoundationAnalysisError as e:
            self.show_diagnostic(str(e))
        except Exception as e:
            messagebox.showerror("Invalid Input", str(e))

    def run_plot(self):
        try:
            self.cancel_requested = False
            self.progress['value'] = 0
            self.update()

            f, h, d, l, tot_piles, n_rows, spacing, soil, mat, sf, criterion = self.get_and_validate_inputs()

            stress_data = fcore.compute_pile_stresses(
                applied_force_n=f, load_application_height_m=h,
                num_rows=n_rows, spacing_between_rows_m=spacing, total_piles=tot_piles,
                diameter_m=d, length_m=l,
                cu_pa=soil["Cu"]*1000, gamma=soil["gamma"], eps50=soil["eps50"],
                global_safety_factor=sf, failure_criterion=criterion
            )

            plot_pile_stresses(stress_data, mat["desc"], mat["Sy"], criterion)
            self.log("Plot generated successfully.")
            
            self.progress['value'] = 100
            self.update()
        except fcore.FoundationAnalysisError as e:
            self.show_diagnostic(str(e))
        except Exception as e:
            messagebox.showerror("Invalid Input", str(e))

    def run_length_diameter_map(self, show_plot=True, force_progress_start=0, force_progress_end=100):
        try:
            self.cancel_requested = False
            if show_plot:
                self.progress['value'] = 0
                self.update()

            f, h, current_d, max_l, tot_piles, n_rows, spacing, soil, mat, sf, criterion = self.get_and_validate_inputs()
            max_l = max_l * 1.5
            if max_l < 0.5: max_l = 1.0
            
            res_L, res_D = 20, 20
            L_vals = np.linspace(0.2, max_l, res_L)
            D_vals = np.linspace(max(0.005, current_d * 0.2), max(0.1, current_d * 2.5), res_D)
            L_grid, D_grid = np.meshgrid(L_vals, D_vals)
            Z = np.zeros_like(L_grid, dtype=float)

            if show_plot:
                self.log(f"\nRunning design-space sweep: embedment length vs pile diameter, {res_L}x{res_D} grid...")
            self.update()

            args_list = []
            for i in range(res_D):
                for j in range(res_L):
                    L = L_grid[i, j]
                    D = D_grid[i, j]
                    args_list.append((i, j, f, h, n_rows, spacing, tot_piles, D, L, soil["Cu"]*1000, soil["gamma"], soil["eps50"], mat["Sy"]*1e6, sf, criterion))

            def eval_point(args):
                i, j, F, h, n_rows, spacing, tot_piles, D, L, cu_pa, gamma, eps50, sy_steel_pa, sf, criterion = args
                try:
                    res = fcore.evaluate_frame_capacity(
                        applied_force_n=F, load_application_height_m=h,
                        num_rows=n_rows, spacing_between_rows_m=spacing, total_piles=tot_piles,
                        diameter_m=D, length_m=L,
                        cu_pa=cu_pa, gamma=gamma, eps50=eps50,
                        sy_steel_pa=sy_steel_pa, global_safety_factor=1.0, deflection_limit_mm=5.0
                    )
                    min_sf = min(res['real_structural_sf'], res['real_pullout_sf'])
                    if res['max_deflection_mm'] > 5.0 or min_sf < 1.0: return (i, j, 0.0)
                    elif min_sf < 1.5: return (i, j, 1.0)
                    elif min_sf < sf: return (i, j, 2.0)
                    else: return (i, j, 3.0)
                except:
                    return (i, j, 0.0)

            total_steps = len(args_list)
            step = 0
            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = [executor.submit(eval_point, arg) for arg in args_list]
                
                while futures:
                    if self.cancel_requested:
                        for f in futures: f.cancel()
                        self.log("[X] Operation cancelled by user.")
                        self.progress['value'] = 0
                        self.update()
                        return None
                    
                    done, futures = concurrent.futures.wait(futures, timeout=0.1, return_when=concurrent.futures.FIRST_COMPLETED)
                    
                    for future in done:
                        i, j, val = future.result()
                        Z[i, j] = val
                        step += 1
                        
                    if done:
                        prog_range = force_progress_end - force_progress_start
                        self.progress['value'] = force_progress_start + (step / total_steps) * prog_range
                    self.update()
            
            cmap = ListedColormap(['#d62728', '#ff7f0e', '#1f77b4', '#2ca02c'])
            labels = ['Failure', 'Marginal', 'Below SF', 'Approved']
            
            fig = plt.figure(figsize=(10, 6))
            plt.contourf(L_grid, D_grid * 1000, Z, levels=[-0.5, 0.5, 1.5, 2.5, 3.5], cmap=cmap, alpha=0.85)
            
            patches = [mpatches.Patch(color=cmap.colors[k], label=labels[k]) for k in range(4)]
            plt.legend(handles=patches, loc='upper left')
            plt.title(f"Design Map: Rod Length vs Diameter\nApplied Force: {f/1000:.1f} kN", fontweight='bold')
            plt.xlabel("Rod Embedded Length (m)")
            plt.ylabel("Rod Diameter (mm)")
            plt.grid(True, linestyle='--', alpha=0.4, color='black')
            
            plt.scatter([l], [current_d * 1000], color='white', edgecolor='black', s=100, zorder=5)
            
            plt.tight_layout()
            if show_plot:
                plt.show()
                self.log("Design Map generated successfully.")
                self.progress['value'] = 100
                self.update()
                
            return fig
        except Exception as e:
            messagebox.showerror("Invalid Input", str(e))
            return None

    def run_save_report(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".html",
            filetypes=[("HTML Report", "*.html")],
            title="Save Full Engineering Report"
        )
        if not filepath: return
        
        try:
            self.cancel_requested = False
            self.progress['value'] = 0
            self.update()
            
            f, h, d, l, tot_piles, n_rows, spacing, soil, mat, sf, criterion = self.get_and_validate_inputs()

            self.log("\n--- GENERATING FULL REPORT ---")
            
            # 1. BROMS
            res_broms = fcore.evaluate_capacity_broms(
                applied_force_n=f, eccentricity_m=h, passive_zone_factor=1.5,
                number_of_piles=tot_piles, diameter_m=d, embedded_length_m=l,
                soil_cu_pa=soil["Cu"]*1000, steel_sy_pa=mat["Sy"]*1e6
            )
            
            # 2. FEM
            res_fem = fcore.evaluate_frame_capacity(
                applied_force_n=f, load_application_height_m=h,
                num_rows=n_rows, spacing_between_rows_m=spacing, total_piles=tot_piles,
                diameter_m=d, length_m=l,
                cu_pa=soil["Cu"]*1000, gamma=soil["gamma"], eps50=soil["eps50"],
                sy_steel_pa=mat["Sy"]*1e6,
                global_safety_factor=sf, failure_criterion=criterion
            )
            
            # 3. Layout Diagram via Matplotlib
            fig_layout = plt.figure(figsize=(6, 6))
            piles_per_row = [tot_piles // n_rows + (1 if x < tot_piles % n_rows else 0) for x in range(n_rows)]
            start_y = -((n_rows - 1) * spacing) / 2
            for i, count in enumerate(piles_per_row):
                y = start_y + i * spacing
                start_x = -((count - 1) * spacing) / 2
                plt.plot([start_x, start_x + (count-1)*spacing], [y, y], color='gray', linestyle='--', zorder=1)
                for j in range(count):
                    x = start_x + j * spacing
                    plt.gca().add_patch(plt.Circle((x, y), d/2, color='#0052cc', ec='black', zorder=2))
            
            if start_y - spacing < 0:
                plt.arrow(0, start_y - spacing*1.5, 0, spacing, head_width=spacing*0.2, head_length=spacing*0.2, fc='red', ec='red')
            plt.axis('equal')
            plt.title('Pile Layout Map')
            plt.xlabel('X (m)'); plt.ylabel('Y (m)')
            plt.grid(True, linestyle=':', alpha=0.6)
            b64_layout = self.fig_to_base64(fig_layout)
            
            self.progress['value'] = 20; self.update()
            if self.cancel_requested: return
            
            # 4. Stress Plot
            stress_data = fcore.compute_pile_stresses(
                applied_force_n=f, load_application_height_m=h,
                num_rows=n_rows, spacing_between_rows_m=spacing, total_piles=tot_piles,
                diameter_m=d, length_m=l,
                cu_pa=soil["Cu"]*1000, gamma=soil["gamma"], eps50=soil["eps50"],
                global_safety_factor=sf, failure_criterion=criterion
            )
            fig_stress = plot_pile_stresses(stress_data, mat["desc"], mat["Sy"], criterion, show_plot=False)
            b64_stress = self.fig_to_base64(fig_stress)
            
            self.progress['value'] = 40; self.update()
            if self.cancel_requested: return
            
            # 5. L-D Map
            fig_ld = self.run_length_diameter_map(show_plot=False, force_progress_start=40, force_progress_end=90)
            if not fig_ld: return
            b64_ld = self.fig_to_base64(fig_ld)
            
            self.progress['value'] = 95; self.update()
            
            # Build HTML
            broms_appr = res_broms.get('approved', res_broms.get('soil_sf', 0)>=sf and res_broms.get('steel_sf',0)>=sf)
            
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
                .footer {{ margin-top: 40px; text-align: center; color: #888; font-size: 0.9em; }}
                .tag {{ color: #0052cc; font-weight: bold; }}
            </style></head><body>
            <div class="container">
                <h1>Deep Foundation Engineering Report</h1>
                <p>Generated by <b>Foundation Analysis Toolkit</b></p>
                
                <h2>1. Design Parameters</h2>
                <div class="metric">Applied Force: {f/1000:.2f} kN</div>
                <div class="metric">Load Height: {h:.2f} m</div>
                <div class="metric">Pile Diameter: {d:.3f} m</div>
                <div class="metric">Embedded Length: {l:.2f} m</div>
                <div class="metric">Layout: {tot_piles} piles in {n_rows} rows (spacing: {spacing:.2f} m)</div>
                <div class="metric">Soil: {soil['desc']} (Cu={soil['Cu']} kPa)</div>
                <div class="metric">Material: {mat['desc']} (Sy={mat['Sy']} MPa)</div>
                <div class="metric">Target Safety Factor: {sf:.2f}</div>
                <div class="metric">Failure Criterion: {criterion}</div>
                
                <h2>2. Pile Group Layout</h2>
                <img src="data:image/png;base64,{b64_layout}" alt="Layout Map">
                
                <h2>3. Method 1: Analytical Limit Equilibrium (Broms, 1964)</h2>
                <p>Status: <span class="metric {'pass' if broms_appr else 'fail'}">
                    {'Satisfied' if broms_appr else 'Failed checks'}
                </span></p>
                <ul>
                    <li>Geotechnical Safety Factor: {res_broms.get('soil_sf', 0):.2f}</li>
                    <li>Structural Safety Factor: {res_broms.get('steel_sf', 0):.2f}</li>
                    <li>Ultimate Soil Capacity (per pile): {res_broms.get('soil_resistance_n', 0)/1000:.1f} kN</li>
                    <li>Ultimate Struct Capacity (per pile): {res_broms.get('structural_resistance_n', 0)/1000:.1f} kN</li>
                </ul>
                
                <h2>4. Method 2: Simplified 1D Beam-on-Nonlinear-Winkler-Foundation</h2>
                <p>Status: <span class="metric {'pass' if res_fem['overall_approval'] else 'fail'}">
                    {'Satisfied' if res_fem['overall_approval'] else 'Failed checks'}
                </span></p>
                <ul>
                    <li>Max Deflection: {res_fem['max_deflection_mm']:.2f} mm</li>
                    <li>Structural Safety Factor: {res_fem['real_structural_sf']:.2f}</li>
                    <li>Pullout Safety Factor: {res_fem['real_pullout_sf']:.2f}</li>
                </ul>
                <img src="data:image/png;base64,{b64_stress}" alt="Stress Profile">
                
                <h2>5. Length vs Diameter Operability Map</h2>
                <img src="data:image/png;base64,{b64_ld}" alt="L-D Map">
                
                <div class="footer">
                    <span class="tag">Author: Arthur E. Cau @ Unicamp - 2026</span><br>
                    Developed via Agentic AI Framework
                </div>
            </div>
            </body></html>
            """
            with open(filepath, 'w', encoding='utf-8') as file:
                file.write(html)
                
            self.progress['value'] = 100; self.update()
            self.log(f"\n[OK] REPORT SAVED SUCCESSFULLY to {filepath}")
            messagebox.showinfo("Success", f"Full report saved to:\n{filepath}")
            
        except fcore.FoundationAnalysisError as e:
            self.show_diagnostic(str(e))
        except Exception as e:
            messagebox.showerror("Invalid Input", str(e))

    def show_diagnostic(self, error_msg: str):
        diag = tk.Toplevel(self)
        diag.title("Analysis Diagnostic")
        diag.geometry("500x350")
        diag.configure(padx=20, pady=20, bg="#ffffff")
        
        ttk.Label(diag, text="Analysis Failed: Physical/Numerical Instability", font=("Segoe UI", 12, "bold"), foreground="#cc0000", background="#ffffff").pack(pady=(0, 10))
        
        txt = tk.Text(diag, height=10, bg="#fff0f0", font=("Consolas", 10), wrap=tk.WORD, bd=0, padx=10, pady=10)
        txt.pack(fill=tk.BOTH, expand=True)
        txt.insert(tk.END, f"System Error:\n{error_msg}\n\n")
        txt.insert(tk.END, "Diagnostic:\n")
        txt.insert(tk.END, "The applied load forces the pile to deflect excessively. As deflection increases, the non-linear soil springs yield and lose their stiffness. Without lateral support, the matrix becomes singular.\n\n")
        txt.insert(tk.END, "Suggested Solutions:\n")
        txt.insert(tk.END, "1. Increase the Pile Diameter.\n")
        txt.insert(tk.END, "2. Increase the Pile Length.\n")
        txt.insert(tk.END, "3. Reduce the Applied Force.\n")
        txt.config(state=tk.DISABLED)

        ttk.Button(diag, text="Understood", command=diag.destroy).pack(pady=(10, 0))

if __name__ == "__main__":
    app = FoundationApp()
    app.mainloop()
