Loop historian and controller definition
=======================================

File: /app/data/historian.csv   (6 hours, one row per second)

  time_s   seconds from start of the record
  SP       controller setpoint, % of transmitter span
  PV       measured process variable, % of span (as logged: includes sensor noise)
  OP       controller output, % of valve command (0-100)

The loop was in automatic for the whole record. Operators changed the setpoint several times.
Unmeasured disturbances acted on the process during the record. No valve position feedback
or other instrumentation is available; PV, OP and SP are everything the historian holds.

Process action: a higher OP raises PV (direct-acting process, reverse-acting controller).

Existing controller (the one that produced this log)
----------------------------------------------------
Kp = 1.204, Ti = 17.149 s, Td = 0, db = 0

Controller law (sample time Ts = 1 s; this is the block the new settings will be loaded into)
---------------------------------------------------------------------------------------------
  e     = SP - PV_measured
  e_db  = e - clip(e, -db, +db)            error dead-band; db = 0 disables it
  P     = Kp * e_db
  I    += Kp * Ts / Ti * e_db + (u - u_raw)   integral with back-calculation anti-windup
  Dterm = -Kp * Td * dPVf/dt               derivative on measurement, PVf = PV_measured passed
                                           through a first-order filter with time constant Td/8
  u_raw = P + I + Dterm
  u     = clip(u_raw, 0, 100)              controller output, % OP

Kp is dimensionless (% OP per % PV). Ti and Td are in seconds. db is in % of span.
When Td = 0 there is no derivative action.

Settings limits accepted by the block: 0 < Kp <= 10, 5 <= Ti <= 2000, 0 <= Td <= 60, 0 <= db <= 10.
