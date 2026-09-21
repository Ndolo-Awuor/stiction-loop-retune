# Retune an oscillating loop

# Context

A process loop cycles under its current controller. Six hours of closed-loop historian data are available. The loop was in automatic, operators changed setpoints and unmeasured disturbances acted.

# Inputs

The log - /app/data/historian.csv
The column Definitions, the existing controller settings, the exact controller block the new settings load into, and the units and allowed ranges - /app/data/README.txt

# Deliverable

/app/controller.json - a JSON object with numeric Kp, Ti, Td, db, with the example block in the code fence. ```
{"Kp": ..., "Ti": ..., "Td": ..., "db": ...}

```
# What is Graded

The simulation done on the settings is based on the actual process, and the score is not determined from the logs. The tests are initiated at different operating points and include the setpoint-hold and load-disturbance. The variables tracked include the modest gain and dead-time changes and noise on the sensor and disturbances that could have been missed. Notably, the key elements are the nonexistence of sustained oscillations, the load-disturbance recovery, and the offset based on the steady-state and the movement from the controller-output.

You have 14400 seconds to complete this task. Do not cheat by using online solutions or hints specific to this task.
```
