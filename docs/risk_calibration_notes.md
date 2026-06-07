# Risk calibration notes

Current calibration window: June 2024.

The current rule-based signal is conservative.

June 2024 behavior:

- rows: 720
- mean risk score: 8.24
- median risk score: 0.00
- max risk score: 85.00
- high-risk rows, score >= 60: 7
- extreme rows: 1

Read:

The signal is not firing everywhere. That is good. It means the first rule layer is not noisy by default.

But the low high-risk count also means the model may miss medium-stress periods. Before changing thresholds, we need to inspect the top risk hours and compare them against market intuition.

Do not tune the model yet based only on one month.

Next useful checks:

1. Look at the top 30 risk hours.
2. Check whether those hours make sense in terms of residual load, renewable share and ramps.
3. Add price data before making any claim about market stress or trading usefulness.
4. Keep the current score >= 60 threshold for now.
5. Re-run the same behavior review on at least three more months.

Current decision:

Keep the rules unchanged.

Reason:

The model is conservative, explainable, and not obviously over-triggering. The next improvement should come from more data, not from premature threshold tuning.
