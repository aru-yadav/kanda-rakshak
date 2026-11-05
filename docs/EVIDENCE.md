# Evidence register — every number a juror sees must be here

| Claim | Where used | Source | Date | Link / file |
|---|---|---|---|---|
| 40–60 % loss in natural chawl over 120 days; 15 % with controlled storage | deck s1,s2; video 0:00 | Pasha Patel, Chairman, Maharashtra State Agricultural Price Commission | 10 Aug 2025 | Deccan Herald |
| Maharashtra = 40–45 % of India's onion; stores 40–50 lakh t rabi onion | deck s2 | same | 10 Aug 2025 | Deccan Herald |
| Govt buffer recovery 49 % (2022), 54 % (2023), 63 % (2024), 72 % (2026) | deck s2 | Consumer Affairs Secretary, PTI | 28 Aug 2026 | Deccan Chronicle |
| 40,623 applications for 75 storage structures (Aurangabad) | deck s2 | Deccan Herald | 23 Feb 2021 | Deccan Herald |
| ₹800–1,200/q farm-gate vs ≥ ₹2,500/q cost | deck s2 | news reports | Aug 2025 | add link |
| IIT Bombay team won national Grand Onion Challenge with storage retrofit | jury Q&A | IIT Bombay ACR | Dec 2023 | acr.iitbombay.org |
| Our fresh vs rot result | deck s4, video | our log | TBD | docs/evidence/*.csv |
| Our offline fan proof | video | our recording | TBD | Drive link |

## v2 field kit and business model (added Nov 2026)

Status column: **verified** = we read the primary source; **to verify** = secondary source only, check before quoting to a juror. Lab studies are lab results, not field results: never present them as proof that our kit works in a chawl.

| Claim | Where used | Source | Type | Status |
|---|---|---|---|---|
| Fan-ventilated store at NHRDF Sinnar: 14.52 % loss vs 33.40 % in conventional storage over 6 months | deck, BUSINESS.md, jury Q&A | NHRDF study, *Vegetable Science* 47(2), 2020 | Field trial (NHRDF, not ours) | to verify (add DOI / PDF) |
| Gas-sensor array can separate sour-skin-infected from healthy onions | jury Q&A (why gas sensing) | University of Georgia, *Sensors*, 2015 | Lab | to verify (add DOI) |
| GC-IMS volatile profiles distinguish rotting from healthy stored onions | jury Q&A (sulphur confirms rot) | University of Warwick, *J. Agric. Food Chem.*, 2024 | Lab | to verify (add DOI) |
| Bulk onion storage airflow 1–2 m³/min per m³ of onions | HARDWARE.md field kit fan sizing | UC Davis Postharvest / Oregon State University Extension storage guides | Extension guideline | to verify (add links) |
| MIDH 2025-26 onion storage structure subsidy | BUSINESS.md (MIDH retrofit component) | Agrowon, Apr 2025 | News | **to verify against the Govt GR** before quoting amounts |
| Godaam Sense reported at ₹10,000 per device covering ~5–10 t (may include service); sensing only | JURY_PREP §12, deck | Kisan of India; Krishi Jagran | News | to verify (add links + dates). No hard per-tonne comparison |
| Pilot budget ₹9.74 lakh (quoted ₹9.7 L) for 40 kit + 20 control chawls | JURY_PREP §16, deck slide 4 | our pilot budget; breakdown in HARDWARE.md Part B | Our estimate | itemised |
| PoC bench kit ₹11,500; field kit ≈ ₹17,000 for 25 t (≈ ₹700/t); 5 t ≈ ₹9–10k, 100 t ≈ ₹45–65k | README, HARDWARE.md, JURY_PREP, deck | our estimate, approximate retail prices Nov 2026 | Our estimate | line-item BOM in HARDWARE.md Part B (≈₹17,400; BME688 + mux not yet itemised) |
| Onion price ₹15/kg used in the ₹75,000 savings example | JURY_PREP §11 | assumption | Assumption | replace with a dated Agmarknet modal price |

## Pitch deck numbers (deck as presented 30 Oct 2026; deck not edited)

| Claim | Where used | Source / derivation | Type | Status |
|---|---|---|---|---|
| Lasalgaon (Vinchur) onion modal ₹4,000/q, arrival date 29-10-2026 | deck slide 3 (used as an **illustrative advisory example**) | data.gov.in Agmarknet, fetched by our own price service | API response | real; illustrative use |
| ₹40/kg | deck | = ₹4,000/q above | Derived | real price, converted |
| Kit ≈ 7 % of a 25 t chawl's cost norm (deck: "6–8 %") | deck slide 5, BUSINESS.md, JURY_PREP §11 | 25 t × ₹10,000/t MIDH cost norm = ₹2.5 L; ₹17,000 / ₹2.5 L ≈ 6.8 %. Ratio is kit vs **chawl cost**, not vs subsidy | Derived | MIDH norm as reported by Agrowon, Apr 2025; verify against GR |
| "1-season payback" | deck slides 1, 3 | ₹75,000 target saving (JURY_PREP §11) vs ₹17,000 kit | Target | **target payback < 1 season**, not a result |
| ₹1,500 crore | deck slide 2 (footnoted) | 40 lakh t × 25-point loss reduction × ₹15/kg | Our estimate | estimate |
| 12× | deck | 5 t × ₹40,000/t ÷ ₹17,000 ≈ 11.8 | Our estimate | estimate |
| ≈ ₹12,000 per kit at scale | deck | bulk PCB + parts pricing | Our estimate | estimate |
