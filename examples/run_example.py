import sys
import os

# Add src to path so we can import the core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import foundation_core as fcore

def main():
    print("Running a simple Broms Analysis...")
    res = fcore.evaluate_capacity_broms(
        applied_force_n=3000, 
        eccentricity_m=0.05, 
        passive_zone_factor=1.5,
        number_of_piles=8, 
        diameter_m=0.01, 
        embedded_length_m=0.5,
        soil_cu_pa=100000, 
        steel_sy_pa=250e6
    )
    
    print("--- RESULTS ---")
    print(f"Approved: {res.get('approved', False)}")
    print(f"Soil SF: {res.get('soil_sf', 0):.2f}")
    print(f"Steel SF: {res.get('steel_sf', 0):.2f}")

if __name__ == "__main__":
    main()
