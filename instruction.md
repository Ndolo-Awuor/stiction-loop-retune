<!--
DRAFT OF THE FACTS ONLY. Rewrite this in your own words before submission (the platform screens
instruction.md for AI-generated text). Keep every fact below accurate (paths, file format, units, the
list of graded qualities, the closing sentence). Do NOT add hints about how to solve it, and do not
say what causes the problem. Delete this comment block before submitting.
-->

# Retune an oscillating loop

A process loop in our plant has been cycling and the operators want it fixed. The historian export for six
hours of normal operation is at `/app/data/historian.csv`; `/app/data/README.txt` describes the columns,
the settings of the controller that produced the log, and the exact controller block the new settings will
be loaded into. The loop was in automatic throughout, setpoint changes were made by the operators, and
unmeasured disturbances acted on the process. Nothing else about the loop is available.

Write the new controller settings to `/app/controller.json` as one JSON object with numeric fields:

```
{"Kp": ..., "Ti": ..., "Td": ..., "db": ...}
```

Units and allowed ranges are in the README. The settings are graded on the actual process, not on the log:
they are run through simulated setpoint-hold and load-disturbance tests at several operating points and
for modest changes in process gain and dead time, with sensor noise and disturbances you have not seen.
What is checked is whether the loop stays free of sustained oscillation, rejects a load disturbance well,
holds a small steady-state offset, and keeps the controller output from moving more than the job needs.

You have 14400 seconds to complete this task. Do not cheat by using online solutions or hints specific to this task.
