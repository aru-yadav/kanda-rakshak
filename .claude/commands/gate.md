---
description: Run a phase gate (G0–G5) from docs/PLAN.md and decide GO / NO-GO
argument-hint: <G0|G1|G2|G3|G4|G5>
---

Run gate $ARGUMENTS for Kanda Rakshak.

1. Open `docs/PLAN.md`, find the exit criteria for gate $ARGUMENTS.
2. Verify each criterion with evidence: run `cd backend && pytest -q`, `cd firmware && pio run` where relevant, query `data/kanda.db`, check files exist. Do not accept "it worked earlier".
3. Invoke the `red-team` agent on the scope of this gate.
4. If anything touches hardware, invoke `hardware-safety-reviewer`.
5. Before G4 and G5, invoke `data-integrity-auditor`.
6. Output:

```
GATE $ARGUMENTS — <date IST>
[x]/[ ] each criterion — evidence
Red team verdict: ...
Decision: GO / NO-GO
If NO-GO: the 3 smallest actions to get to GO, with owner (Aryan/Sarvejeet)
```
