# Open items (need a human / primary source)

Added during implementation (on top of the PRD's Section 14 list):

1. **Detector formula symbols (FR-PHY-03).** Implemented as
   `0.5 · A · yield · ε · [1 − d/√(r² + m·d + d²)] · exp(−μ_air·d)` with
   *d* = source–detector distance, *r* = detector radius, *m* = Wright et al.
   fit term (default 0 = exact disk solid angle). The paper could not be
   reached from the build environment — check the symbol meanings and the fitted
   *m* against Wright et al. (2021), Eq. for the Gazebo radiation sensor.
2. **NIST XCOM values** in `physics_constants.yaml` marked VERIFY (air at
   1.25 MeV; concrete and iron at 0.662 and 1.25 MeV) were taken from memory of
   the XCOM tables and interpolated log-log. Re-query XCOM and replace.
3. **Detector parameters** (radius 5 mm, intrinsic efficiency 1 %) are a
   design choice for a low-sensitivity probe; replace with the datasheet of the
   detector the semester-2 robots will carry.
4. **Model-error field (D6)** σ = 0.3, correlation length 3 m. Find a
   literature value for analytic-vs-measured discrepancy near shielded sources
   (e.g. buildup-factor studies, or Son et al. 2025 residuals) and cite it.
5. **AC-3 re-check.** Budgets were calibrated with dose-unaware baselines
   (Co-60, 0.3 Gy → 30 % violation for "approach"). AC-3 is defined on trained
   MAPPO: run `scripts/calibrate.py --policies checkpoint:<mappo final.pt>` at
   week 5 and lower the budget if MAPPO violates < 30 %.
6. **FR-ALG-06.** The λ update reproduces the projected-gradient rule of
   PKU Safe-Policy-Optimization as documented; diff against their
   `mappolag` source once network access is available.
7. Shielding **build-up factors** are ignored (narrow-beam attenuation): dose
   behind thick obstacles is underestimated. Acceptable for semester 1; check
   with OpenMC in semester 2 (FR-PHY-09).
