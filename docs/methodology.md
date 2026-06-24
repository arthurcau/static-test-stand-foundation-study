# Toolkit Methodology and User Guide

This document outlines the workflow and theoretical modules implemented in the Foundation Analysis Toolkit. The toolkit is designed for engineers, students, and researchers evaluating preliminary foundation responses under lateral and axial loading.

## 1. Input Parameters
The calculation engine requires the definition of structural geometry, material properties, and geotechnical profiles. These are entered via the left-hand panel:

- **Applied Force (N):** The horizontal lateral load applied to the foundation.
- **Load Height (m):** The vertical distance from the ground surface to the point of load application.
- **Soil Type:** Cohesive soil profiles (e.g., configurations of Red Oxisol), defined by undrained shear strength ($C_u$), unit weight ($\gamma$), and $\varepsilon_{50}$.
- **Material Type:** Structural material yielding limits (e.g., 250 MPa for structural steel).
- **Geometry & Layout:** Single pile dimensions (Diameter and Embedment Length) and the group configuration (Total Piles, Number of Rows, Row Spacing).

*Note: The right-hand panel visualizes the plan-view of the pile group configuration based on the inputted spacing and rows.*

## 2. Evaluation Methods

### Evaluate (Broms)
Executes a limit equilibrium analysis based on Broms (1964). 
It evaluates the ultimate geotechnical capacity assuming full mobilization of passive soil wedges, and the ultimate structural capacity assuming rigid-plastic hinges. It does not calculate service deflections.

### Evaluate (FEM/BNWF)
Executes a 1D Beam-on-Nonlinear-Winkler-Foundation model.
The pile is modeled as an elastic beam discretized into finite elements, supported by nonlinear $p-y$ soil springs (Matlock, 1970). This method evaluates progressive soil yielding and provides serviceability metrics, such as the maximum horizontal deflection (mm).

## 3. Post-Processing Tools

### Plot Stresses
Solves the BNWF model and plots the resulting vertical distributions of bending, axial, and shear stresses. It overlays the combined equivalent stress against the von Mises yield criterion of the selected material.

### Plot Design Map
Performs a nonlinear parameter sweep across varying pile lengths and diameters for the defined load. It generates a 2D contour map classifying the design space into regions based on the governing failure criterion:
- **Red:** Failed (SF < 1.0 or deflection > 5.0 mm, or non-convergent cases).
- **Orange:** Marginal (1.0 $\le$ SF < 1.5).
- **Blue:** Sub-optimal (1.5 $\le$ SF < 2.0).
- **Green:** Satisfied (SF $\ge$ 2.0 and deflection $\le$ 5.0 mm).

### Save Report
Aggregates the inputs, both analytical (Broms) and numerical (BNWF) evaluations, the layout diagram, the stress profile, and the design map into a single self-contained HTML report.

## 4. Handling Numerical Non-Convergence
If the BNWF solver encounters a singular matrix or fails to converge, it is typically symptomatic of physical instability (e.g., the applied load far exceeds the ultimate soil resistance, causing infinite displacement). In these scenarios, the program logs the configuration as "Failed - Non-convergent or excessive deflection" and halts the solver to prevent unbounded iterations. To resolve this, increase the pile dimensions or reduce the applied load.
