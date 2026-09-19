"""
Sealed verifier. Loads the agent's controller settings, simulates them on the hidden true plant
(and gain/delay-perturbed variants) with noise seeds the agent never saw, and gates on:

  1. no sustained oscillation at constant setpoint     (fraction of held-out runs that limit-cycle)
  2. load-disturbance rejection                        (integrated absolute error)
  3. steady-state offset                               (mean absolute error at constant setpoint)
  4. controller-output travel                          (total |dOP| after the disturbance: valve wear)

Settings are read defensively (key case, int vs float, string numbers). Out-of-range settings, a
missing file, or non-finite values fail. Diagnostics are written to /logs/verifier/metrics.json.
"""
import json
import math
from pathlib import Path

import pytest

import grading as g

ARTIFACT = Path("/app/controller.json")
HERE = Path(__file__).parent
PLANT = json.loads((HERE / "hidden_plant.json").read_text())
GATES = json.loads((HERE / "gates.json").read_text())
LIMITS = {"kp": (0.0, 10.0), "ti": (5.0, 2000.0), "td": (0.0, 60.0), "db": (0.0, 10.0)}


def load_settings():
    assert ARTIFACT.exists(), f"missing {ARTIFACT}"
    raw = json.loads(ARTIFACT.read_text())
    assert isinstance(raw, dict), "controller.json must contain a JSON object"
    norm = {str(k).strip().lower(): v for k, v in raw.items()}
    out = {}
    for key in ("kp", "ti", "td", "db"):
        assert key in norm, f"missing setting {key}"
        val = float(norm[key])
        assert math.isfinite(val), f"{key} is not finite"
        out[key] = val
    lo, hi = LIMITS["kp"]
    assert lo < out["kp"] <= hi, "Kp out of accepted range"
    lo, hi = LIMITS["ti"]
    assert lo <= out["ti"] <= hi, "Ti out of accepted range"
    lo, hi = LIMITS["td"]
    assert lo <= out["td"] <= hi, "Td out of accepted range"
    lo, hi = LIMITS["db"]
    assert lo <= out["db"] <= hi, "db out of accepted range"
    return out


@pytest.fixture(scope="module")
def metrics():
    s = load_settings()
    ctrl = {"Kp": [s["kp"]], "Ti": [s["ti"]], "Td": [s["td"]], "db": [s["db"]]}
    m = g.evaluate(ctrl, PLANT)
    result = {k: float(v[0]) for k, v in m.items()}
    Path("/logs/verifier").mkdir(parents=True, exist_ok=True)
    (Path("/logs/verifier") / "metrics.json").write_text(
        json.dumps({"settings": s, "metrics": result, "gates": GATES}, indent=2))
    return result


def test_no_sustained_oscillation(metrics):
    assert metrics["cyc"] <= GATES["cyc"], f"sustained oscillation in {metrics['cyc']:.0%} of held-out runs (limit {GATES['cyc']:.0%})"


def test_disturbance_rejection(metrics):
    assert metrics["iae"] <= GATES["iae"], f"IAE {metrics['iae']:.0f} > {GATES['iae']}"


def test_steady_state_offset(metrics):
    assert metrics["ss"] <= GATES["ss"], f"steady-state offset {metrics['ss']:.2f} > {GATES['ss']}"


def test_controller_output_travel(metrics):
    assert metrics["trav"] <= GATES["trav"], f"OP travel {metrics['trav']:.0f} > {GATES['trav']}"
