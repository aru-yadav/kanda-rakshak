## What
## How tested
- [ ] `cd backend && pytest -q`
- [ ] `cd firmware && pio run` (if firmware touched)
- [ ] Bench test (if hardware touched): describe
## Reviews
- [ ] red-team: PASS / PASS WITH FIXES (link report)
- [ ] hardware-safety-reviewer (if pins/power touched)
- [ ] data-integrity-auditor (if anything a juror will see)
