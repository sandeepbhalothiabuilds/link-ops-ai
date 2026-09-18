# Agent autonomy policy

Read-only analysis is A0. Reversible workspace edits with validation are A1. Local
commits after gates are A2. Push and cloud deployment are A3 and require human approval.
Destructive actions are A4 and disabled by default. Exhausted retries, critical findings,
missing approvals, and integrity mismatches must safe-stop.
