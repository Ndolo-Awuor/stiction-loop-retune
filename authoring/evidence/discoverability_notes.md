# Discoverability of the sticking valve (shipped instance, seed 30)

Method: authoring/provenance/discoverability_check.py, run on environment/data/historian.csv, no plant knowledge used.
Result: PV follows small OP moves weakly and large ones strongly; the response levels off near 2.5 %OP.

| |dOP| (%OP) | mean dPV/dOP |
|---|---|
| < 0.5 | 0.06 |
| 1.0-1.5 | 0.21 |
| 2.0-2.5 | 0.30 |
| 2.5-3.0 | 0.32 |
| 4-6 | 0.35 |
| 6-12 | 0.39 |

The knee coincides with the true stick band (S = 2.57 %OP, tests/hidden_plant.json). A soft signature, not a crisp dead zone.

Difficulty probe, first submission of this bundle: 0 of 8 solved (pass band 0-6). One inspected trajectory diagnosed the cycling as
over-aggressive tuning (Ti 17 s versus a 67 s process time constant), tested only on smooth simulated plants, and submitted
Kp 1.1, Ti 65, Td 0, db 0.1. Scored with tests/grading.py: oscillation 0.92 (gate 0.25), travel 808 (gate 107) -> reward 0.
The same Kp and Ti with db 1.7 gives oscillation 0.08.
