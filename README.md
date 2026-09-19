# stiction-loop-retune

Retune an oscillating process loop from six hours of closed-loop historian data. The settings are graded
by simulating them on the hidden true process (a synthetic, disclosed plant) under held-out setpoint and
load-disturbance tests. The data are **synthetic**, from a seeded generator (`authoring/provenance/`).

## Difficulty

The loop was logged under an aggressive PI controller and cycles continuously. The log does not say why.
The process has two lags and dead time, a gain that changes with operating point, sensor noise, unmeasured
load disturbances, and a sticking valve (stick-slip stiction). The controller block offers Kp, Ti, Td and an
error dead-band.

Plausible wrong routes, and what they produce on the shipped instance (gates in Verification):

* **Textbook tuning from a first-order-plus-dead-time fit (IMC/lambda), no dead-band.** Reads the cycle as
  under-damped tuning and tunes for speed. The stick-slip cycle persists in 96 % of held-out runs and the
  valve moves about 12x more than the gate allows.
* **Blanket detuning.** Slow enough to stop chasing, but the cycle persists (100 % of runs) and
  disturbance rejection is poor (IAE 4721 against a gate of 4298).
* **Textbook tuning plus a guessed round-number dead-band.** Dead-band 1 to 2.5 leaves a cycle or a chattering
  valve; dead-band 3 to 5 stops the cycle but leaves an offset and a slow recovery. All fail on the shipped
  instance. Across the 32 calibration plants a fixed guess passes 0/32 (db 1, 1.5), 3/32 (db 2), 6/32 (db 2.5),
  13/32 (db 3), 17/32 (db 4), 15/32 (db 5).
* **A dead-band sized from only one of the two things that set it.** The window depends on both the stick
  band and the sensor noise level, and the two matter differently on different plants. Sizing from the noise
  alone (3 sigma) passes 14/32 plants and fails the shipped one; sizing from the stick band alone passes 9/32
  and fails the shipped one.

The expert judgment is recognising that a stick-slip valve, not the tuning, is what limits the loop, that
PI-only settings cannot both stop the cycle and reject disturbances, and then sizing the dead-band and the
gains against the stick band, the noise, the operating-point gain change and the valve travel. Fitting a model
to closed-loop data also needs care: unmeasured disturbances and the stick-slip nonlinearity bias a naive fit.

Honest limits of the difficulty. A fixed dead-band around 4 with textbook gains passes 17 of 32 calibration
plants, so a lucky guess is not negligible in general; it fails on the shipped instance, which was chosen from
the calibration plants for that reason (see Verification). Whether the task lands in the required solve band
is measured only by the platform's difficulty probe.

## Reference solution

`solution/solve.py` (route A, identification then simulation-based design), working only from
`historian.csv` and the documented controller law:

1. Static map from mean OP versus mean PV on the long constant-setpoint plateaus (quadratic, extended
   linearly outside the observed range so it stays monotone); local gain from its slope.
2. Two lags, dead time and a stick-slip valve model fitted by simulation error over the whole record on
   high-passed residuals (which removes slow unmeasured disturbances), with the logged OP as the known input,
   using a small self-contained differential-evolution search.
3. Sensor noise level and correlation from second differences of PV.
4. A search over (Kp, Ti, db) on the fitted model, judged the way the verifier judges: several noise seeds and
   gain and delay variants, fraction of oscillating runs, IAE, offset and output travel. It picks the
   lowest-IAE tuning in the interior of the feasible region. Loop gain is kept in a conventional range
   (Kp times the local gain at most about 2.4).

Other valid strategies exist and the verifier does not require this one: any settings that pass the four gates
are accepted. `authoring/provenance/solver_b.py` is an independent route (below).

## Verification

`tests/test_retune.py` loads `/app/controller.json`, rejects a missing file, non-finite or out-of-range
values, then simulates the settings on the hidden plant and on gain- and delay-perturbed variants: 5 scenarios
(three setpoints, two perturbed plants) times 5 noise seeds the agent never saw = 25 runs, 3000 s each, with a
4 %PV load step at t = 300 s. Four gates must all hold (one pytest test each; reward is 1 only if all pass):

| gate | measures | threshold (shipped instance) | why it sits there |
|---|---|---|---|
| oscillation | fraction of the 25 runs whose PV, smoothed over 15 s, swings more than 1.5 %PV peak-to-peak in the last 1500 s | <= 0.25 | Gating the worst run was brittle (stick-slip cycling is sensitive); a fraction is stable. Lazy routes sit at 0.6 to 1.0, the reference at 0.08. |
| offset | mean absolute error in the last 1000 s, worst scenario, seed-averaged | <= 2.78 (0.9 x the stick band in PV units) | A dead-band leaves a stick-band-sized offset; the gate stops an oversized dead-band. Reference 1.00. |
| disturbance IAE | integral of absolute error 300-1800 s, worst scenario, seed-averaged | <= 4298 (0.75 x the IAE of a loop that never acts) | Physical baseline independent of any solver. Reference 1849; do-nothing scores 5730. |
| output travel | sum of absolute OP moves after t = 300 s, worst scenario, seed-averaged | <= 107 (6 x the least travel of any clearly good tuning) | Stops a chattering valve. The reference of 75 leaves a 1.4x margin. |

**Ground truth** is the simulated physics of the hidden plant, from the disclosed generator
(`authoring/provenance/make_instance.py`, seed 30). No reference answer is compared. The travel yardstick
comes from a brute-force grid over (Kp, Ti, db) on the true plant, independent of every solver
(`authoring/provenance/grid.py`); "clearly good" means oscillation <= 0.1, offset <= 0.5 x stick band and IAE
<= 0.5 x do-nothing. Simulation is fixed-step with fixed seeds and pinned numpy, so grading is deterministic.

**Calibration.** The generator was run for 32 regenerated plants (seeds 11-42: stick band 1.5-6 %OP, sensor
noise 0.3-1.8 %PV, process gain 0.9-1.8, varied lags and dead time). Results are in `authoring/evidence/`
(`cal_*.json`, `grid_*.npz`, `bvar_*.json`, `final_tables.json`) and were produced by `calibrate.py`,
`grid.py`, `bvariants.py`, `summarize3.py`.

**Disclosures.** (1) The gate parameters were chosen after seeing the calibration results, so the 32-plant
figures are not a clean hold-out. (2) The reference solver design step was revised several times on earlier
plant families (earlier results are archived in `authoring/evidence/v*`). (3) The shipped instance (seed 30)
was selected from the 32 calibration plants because both solvers pass with margin and every fixed blind
dead-band guess fails on it. (4) The reference passes 27 of 32 calibration plants, not all of them; its
misses are marginal oscillation or travel on 5 plants, and it passes the shipped instance deterministically.

## Ablation ladder

Shipped instance. Gates: oscillation <= 0.25, offset <= 2.78, IAE <= 4298, travel <= 107.

| route | oscillation | offset | IAE | travel | passes | 32-plant pass count |
|---|---|---|---|---|---|---|
| A: identification + simulation design (reference) | 0.08 | 1.00 | 1849 | 75 | yes | 27/32 |
| B: field heuristic (stick band from cycle amplitude, dead-band = max(0.4 x stick band, 3 sigma), gain x0.5, reset x2.5) | 0.08 | 0.83 | 2732 | 98 | yes | 21/32 |
| existing controller | 1.00 | 5.53 | 6111 | 1371 | no | 0/32 |
| textbook FOPDT/IMC, no dead-band | 0.96 | 0.84 | 1244 | 1313 | no | 0/32 |
| blanket detune (Kp 0.2, Ti 200) | 1.00 | 0.71 | 4721 | 156 | no | 0/32 |
| textbook + dead-band 1 | 0.64 | 0.82 | 1444 | 543 | no | 0/32 |
| textbook + dead-band 2 | 0.20 | 1.18 | 2354 | 279 | no | 3/32 |
| textbook + dead-band 3 | 0.08 | 2.36 | 3700 | 202 | no | 13/32 |
| textbook + dead-band 4 | 0.00 | 3.04 | 4856 | 96 | no | 17/32 |
| textbook + dead-band 5 | 0.00 | 4.00 | 5730 | 3 | no | 15/32 |
| textbook + dead-band from noise only (3 sigma) | 0.72 | 0.80 | 1642 | 539 | no | 14/32 |
| textbook + dead-band from stick band only (0.45 x) | 0.48 | 0.88 | 1653 | 364 | no | 9/32 |

Cheat attempts (`authoring/provenance/cheat_attempts.py`, results in `authoring/evidence/cheat_attempts_results.json`):
an inert controller (huge dead-band), tiny gain with huge reset time, maximum gain, P-only high gain, derivative
chatter, an oversized dead-band with fast tuning, and an undersized dead-band all fail the gates; zero settings
are rejected before simulation. Not done: an independent second implementation of the *verifier*, and agent
trials (the platform's difficulty probe is the first measurement of agent solve rate).
