---
description: Red team a scope, then hand findings to blue team
argument-hint: <scope e.g. firmware | backend | wiring | deck | all>
---

1. Invoke the `red-team` agent on scope: $ARGUMENTS. Save the report to `docs/reviews/<date>-redteam-$ARGUMENTS.md`.
2. Show me the CRITICAL and HIGH findings and wait for my "go".
3. On "go", invoke the `blue-team` agent with that report. Save its response next to the report.
4. Re-invoke `red-team` on the changed files only. Repeat until verdict is PASS or I stop you.
