# Production operations

No production model or validated live data is supplied with this engineering build.

## Credentials and acquisition

Use Massive as the primary provider and put its key in `.env` locally. Stock real-time consolidated data and quotes, historical minute data and the Benzinga earnings endpoint require the corresponding account access. An authenticated socket is not proof of full coverage. No subscription is automatically purchased.

Historical downloads retain retrieval provenance. Supply audited sector/split/all-event context and terminal outcomes. Do not declare historical revisions point-in-time merely by changing their timestamps. Do not replace missing outcomes with zero returns.

## Model release

Training writes a candidate and reserves its locked evaluation dates once. Promotion command:

```powershell
python -m vesper promote --model-id <candidate-id> --audit <audit.json>
```

The audit JSON needs the candidate's exact `dataset_sha256` and `checks` entries for `point_in_time_identity`, `terminal_outcomes`, `corporate_actions`, `feature_cutoffs`, `live_replay_parity`, `execution_cost_parity`, `historical_availability`, and `sector_provenance`. Each entry needs `status: PASS` and a nonempty `evidence` description identifying the actual audited source/report. These are provenance attestations, not automatically established facts; they must not be fabricated. Numerical gates alone do not establish profitability.

Promotion requires at least 63 locked sessions, positive SPY excess and rank IC, drawdown better than -20%, Brier below .25, positive lower block-bootstrap bounds for returns and SPY excess, and performance at least as high as the momentum baseline. Four required probability calibrations must have finite parameters. These engineering thresholds are explicit policy choices, not proven optimal thresholds.

An atomic `models/production.json` pointer records the candidate manifest hash and audit. The original candidate is unchanged. Restart VESPER to load a new selected model. Editing a selected manifest or model invalidates fingerprint checks.

## Acceptance

Start the application, then run `VALIDATE_LIVE.ps1` during the real signal session. The validator observes the local runtime, model, current data, multiple ranking snapshots, and the persisted decision. A valid NO TRADE is acceptable; missing/stale candidate inputs are SYSTEM INVALID. A closed session or missing evidence cannot pass. A pass is current-session evidence and expires from the dashboard when current readiness fails.

## Pauses and recovery

```powershell
python -m vesper pause --reason "Investigating data quality"
python -m vesper resume --reason "Recorded investigation and corrective action"
```

Pauses persist across restarts. Resume records the review and acknowledges completed outcomes through that session; a new outcome can trigger another automatic pause. Monitoring stays active. Never resume merely to force a BUY.

Signals and outcomes are immutable. Unknown Telegram delivery is deliberately not retried: check the destination before taking any manual action. Raw recordings expire after the configured retention period; export long-term replay evidence beforehand. SQLite is canonical for regenerating result files.

Position monitoring surfaces available quotes and observed warnings, including outside regular hours when the feed supplies them. Absence of a warning is not complete all-catalyst coverage. MFE/MAE are regular-session minute-bar bounds around a benchmark, not an actual execution path. Loss attribution is numerical component decomposition, not a verified causal explanation.
