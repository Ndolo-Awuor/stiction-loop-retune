"""
Try to cheat our own verifier (never executed by the pipeline). Each attempt is a controller.json a lazy or
adversarial agent might submit; none should pass the shipped gates.

Usage: python cheat_attempts.py <hidden_plant.json> <gates.json>
"""
import json
import sys
import numpy as np
import grading as g

ATTEMPTS = {
    "all_zero_settings (invalid range)": None,
    "inert_controller: huge dead-band hides every error": (1.0, 100.0, 0.0, 10.0),
    "detune_to_nothing: tiny gain, huge reset time": (0.05, 2000.0, 0.0, 0.0),
    "blanket_detune": (0.2, 200.0, 0.0, 0.0),
    "max_gain_max_speed": (10.0, 5.0, 0.0, 0.0),
    "p_only_high_gain": (5.0, 2000.0, 0.0, 0.0),
    "textbook_imc_no_deadband": (1.0, 50.0, 0.0, 0.0),
    "derivative_kick_chatter": (2.0, 40.0, 60.0, 0.0),
    "oversized_deadband_with_fast_tuning": (2.0, 30.0, 0.0, 6.0),
    "undersized_deadband": (1.0, 45.0, 0.0, 0.3),
}

if __name__ == "__main__":
    plant = json.load(open(sys.argv[1]))
    gates = json.load(open(sys.argv[2]))
    out = {}
    for name, s in ATTEMPTS.items():
        if s is None:
            out[name] = {"passes": False, "reason": "Kp = 0 is rejected as out of range before any simulation"}
            continue
        kp, ti, td, db = s
        m = g.evaluate({"Kp": [kp], "Ti": [ti], "Td": [td], "db": [db]}, plant)
        res = {k: float(v[0]) for k, v in m.items()}
        res["passes"] = bool(g.passes({k: v for k, v in m.items()}, gates)[0])
        out[name] = res
        print(f"{name:52s} cyc={res['cyc']:.2f} iae={res['iae']:7.0f} ss={res['ss']:5.2f}  passes={res['passes']}")
    json.dump(out, open("../evidence/cheat_attempts_results.json", "w"), indent=2)
