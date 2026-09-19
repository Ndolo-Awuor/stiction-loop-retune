# Feasibility prototype results (synthetic sticky-valve loop)

Plant: two-lag + 7 s dead time, equal-percentage valve characteristic (local gain 0.96-1.45 across SP 35-65),
two-parameter stick-slip valve model, sensor noise 0.1 %PV, unmeasured load step. 3 hidden scenarios x 2 noise seeds,
3000 s runs. Gates evaluated on worst case: p2p of 15 s moving average of PV over last 1500 s (limit cycle),
IAE over 300-1800 s, mean steady-state error over last 1000 s.

## Findings
1. PI-only (Kp, Ti) cannot satisfy no-limit-cycle + disturbance bound at S = 2 % stiction:
   0-1 of 100 grid cells pass. At S = 3 % the pass cells are isolated "lucky stuck" points (noise-sensitive) -> unusable gate.
   At S = 1 % the textbook IMC rule fails only marginally (p2p 1.66 vs gate 1.5) -> inside method noise.
2. Lazy strategies at S = 2 % (dead-band 0): existing (1.6, 20) p2p 6.9; textbook IMC (1.4, 51) p2p 3.0;
   blanket detune (0.2, 200) IAE 4003 (> 2500-3000 bound). All fail.
3. Adding an error dead-band lever: pass cells per 100 (Kp,Ti) cells, gate p2p<=1.5, IAE<=2500, ssErr<=3:
   db 0 -> 0, 0.5 -> 8, 1.0 -> 51, 1.5 -> 65, 2.0 -> 65, 3.0 -> 4, 4.0 -> 0.
   Window in db is roughly 0.5-1.0 x (stick band in PV units); mis-sizing in either direction fails.
   Textbook tuning + db 1-2 passes (p2p 0.0, IAE ~1400-1600); textbook + db 3 fails.

## Implications for the design
- Controller deliverable needs an anti-stiction lever (error dead-band) or no expert answer exists.
- Stiction size must not be a "guessable round number": window in db scales with S x local gain, so the agent
  has to quantify the stick band from the historian data.
- Gates must be evaluated over multiple noise seeds per scenario (single-seed p2p is noise-sensitive).
- Still to calibrate: gate thresholds against two independent solvers on >= 30 regenerated plants.
