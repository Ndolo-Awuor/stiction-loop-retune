# Retune an oscillating loop

The process loop in the plant has been cycling, and the operators want it sorted out.

I’ve put the six-hour historian export from a period of normal operation in `/app/data/historian.csv`. The `/app/data/README.txt` has the column descriptions, the controller settings that were being used when the data was recorded, and the exact controller block where the new settings will be loaded.

The loop was in automatic the whole time. The operators made some setpoint changes, and there were also disturbances affecting the process that were not measured. Apart from the historian data and the information in the README, we don't have anything else to work with.

Use that information to come up with the new controller settings and save them in `/app/controller.json`. Keep it as one JSON object with these four numeric fields:

```arduino
{"Kp": ..., "Ti": ..., "Td": ..., "db": ...}
```

The README gives you the required units and the allowed ranges for each setting, so use those when choosing the values.

One important point is that the settings won't be judged just by how well they fit the six-hour log. They'll be run on the actual process through simulated setpoint-hold and load-disturbance tests at several operating points. The tests will also introduce modest changes in process gain and dead time, as well as sensor noise and disturbances that aren't in the data you have.

What we need from the tuning is a loop that doesn't settle into sustained cycling, recovers properly when a load disturbance hits it, keeps the steady-state offset small, and doesn't make the controller output move around more than the job requires.

You have 14400 seconds to complete this task. Do not cheat by using online solutions or hints specific to this task.
