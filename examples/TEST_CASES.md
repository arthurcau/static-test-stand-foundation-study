# Test Cases & Examples

This document outlines 5 educational test cases ranging from simple, safe designs to catastrophic failures. These cases demonstrate the capabilities, safety checks, and theoretical limitations of the Foundation Analysis Toolkit.

You can run all these cases programmatically by executing `python examples/run_test_cases.py`.

---

### Case 1: Baseline Safe Design (Stiff Soil, Moderate Load)
**Goal:** Demonstrate a robust layout in compacted soil where both limit equilibrium and non-linear checks easily pass.
- **Parameters:** 8 piles (4 rows, 0.3m spacing), Diameter: 50mm, Length: 1.5m.
- **Environment:** Compacted Red Oxisol ($C_u$ = 120 kPa). Load: 5 kN at 0.1m height.
- **Expected Outcome:** 
  - **Broms:** Satisfied (High Geotechnical and Structural Safety Factors).
  - **BNWF:** Satisfied (Minimal deflection < 1mm, excellent pullout margin).

### Case 2: The Serviceability Trap (Flexible Piles in Soft Soil)
**Goal:** Highlight why Broms (Limit Equilibrium) is dangerous on its own. Broms might approve the ultimate soil capacity, but the BNWF model will reject it because the piles bend excessively before reaching that ultimate state.
- **Parameters:** 4 piles (2 rows), Diameter: 15mm (Very thin), Length: 2.0m.
- **Environment:** Saturated Red Oxisol ($C_u$ = 30 kPa). Load: 2 kN at 0.1m height.
- **Expected Outcome:** 
  - **Broms:** Satisfied (Ultimate soil wedge is strong enough).
  - **BNWF:** Failed (Deflection exceeds the 5.0mm serviceability limit due to lack of stiffness).

### Case 3: Structural Failure (High Bending Moment)
**Goal:** Demonstrate a scenario where the soil provides strong resistance, but the extreme load application height causes enormous bending moments, yielding the steel.
- **Parameters:** 6 piles (3 rows), Diameter: 20mm, Length: 1.0m. Steel: A36.
- **Environment:** Compacted Red Oxisol. Load: 15 kN at 0.5m height.
- **Expected Outcome:**
  - **Broms:** Failed (Structural SF drops below 2.0).
  - **BNWF:** Failed (Maximum von Mises stresses near the pile head exceed 250 MPa yield strength).

### Case 4: Axial Pullout Failure (Insufficient Embedment)
**Goal:** Show the limit of lateral loading causing axial tension. A tall overturning moment creates massive uplift on the rear pile rows. The embedment length is too short to resist pullout friction.
- **Parameters:** 4 piles (2 rows), Diameter: 30mm, Length: 0.3m (Too short).
- **Environment:** Dry Red Oxisol ($C_u$ = 60 kPa). Load: 8 kN at 0.8m height.
- **Expected Outcome:**
  - **BNWF:** Failed (The axial pullout force exceeds the integrated side-friction resistance, leading to a Pullout SF < 2.0).

### Case 5: Catastrophic Physical Instability (Waterlogged Soil)
**Goal:** Simulate an extreme load in mud with practically zero cohesion. The piles plow through the soil without resistance. This highlights the solver's non-convergence safety net.
- **Parameters:** 8 piles (4 rows), Diameter: 20mm, Length: 1.0m.
- **Environment:** Waterlogged Red Oxisol ($C_u$ = 10 kPa). Load: 25 kN at 0.1m height.
- **Expected Outcome:**
  - **BNWF:** Failed to converge. The non-linear springs completely degrade, the structural matrix becomes singular, and the solver correctly halts with a `FoundationAnalysisError` indicating physical collapse.
