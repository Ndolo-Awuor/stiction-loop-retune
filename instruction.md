# Retune an oscillating loop

## Context

A process loop cycles under its current controller. Six hours of closed-loop historian data are available. The loop was in automatic, operators changed setpoints and unmeasured disturbances acted.

## Inputs

The log - `/app/data/historian.csv`

The column definitions, the existing controller settings, the exact controller block the new settings load into, and the units and allowed ranges - `/app/data/README.txt`

## Deliverable

`/app/controller.json` - a JSON object with numeric Kp, Ti, Td, db:

```
{"Kp": ..., "Ti": ..., "Td": ..., "db": ...}
```

## What is graded

The settings are simulated on the actual process, not scored against the log. Tests are setpoint-hold and load-disturbance at several operating points, with modest gain and dead-time changes and sensor noise and disturbances you haven't seen. Checked: no sustained oscillation, load-disturbance recovery, steady-state offset, and controller-output movement.

You have 14400 seconds to complete this task. Do not cheat by using online solutions or hints specific to this task.
