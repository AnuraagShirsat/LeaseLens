# LeaseLens evaluation results

Run on 2026-10-09 with 4 mock agreements.

| Case | Planted issues found | Quote accuracy | Citation validity | Unexpected high-risk findings | Seconds |
| --- | --- | --- | --- | --- | --- |
| case1 | ERROR | ERROR | ERROR | ERROR | 0 |
| case2 | ERROR | ERROR | ERROR | ERROR | 0 |
| case3 | ERROR | ERROR | ERROR | ERROR | 0 |
| case4 | ERROR | ERROR | ERROR | ERROR | 0 |
| **Overall** | **0/0** | **n/a (0)** | **n/a (0)** | **0** | **0 (average)** |

## Issues that were missed

- case1: deductions | Painting and repair charges may be deducted from the deposit with no amount, list or proof (Clause 5)  (analysis failed)
- case1: missing | No deposit return timeline is given (Clauses 4 and 5)  (analysis failed)
- case2: conflict | The security deposit is Rs 60,000 in the summary of key terms but Rs 80,000 in Clause 4  (analysis failed)
- case3: lock_in | Lock-in period of 8 months out of an 11-month term (Clause 6)  (analysis failed)
- case3: termination_notice | Notice period of 90 days (Clause 7)  (analysis failed)
- case3: maintenance_repairs | Maintenance and repairs clause does not say who pays or who does what (Clause 8)  (analysis failed)
- case4: missing | Annexure A (Inventory of Items) is mentioned in Clause 1 but is not attached  (analysis failed)
- case4: entry_inspection | Landlord may enter with "reasonable notice" without saying how much notice (Clause 9)  (analysis failed)

Notes: a planted issue counts as found when the AI gave a medium or high risk finding on that topic, or a gap of the same kind (conflict or missing). Quote accuracy ignores capital letters and extra spaces. Small test set: four fictional agreements.
