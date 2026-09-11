"""Production selection is an atomic pointer to an immutable, audited candidate."""
import hashlib
import json
import math
from pathlib import Path

from filelock import FileLock

from vesper.calendar import utcnow
from vesper.modeling import Ensemble

REQUIRED_AUDITS = {"point_in_time_identity", "terminal_outcomes", "corporate_actions", "feature_cutoffs",
                   "live_replay_parity", "execution_cost_parity", "historical_availability", "sector_provenance"}


def promotion_failures(metadata, audit):
    failures = []
    if audit.get("dataset_sha256") != metadata.get("dataset_sha256") or not metadata.get("dataset_sha256"):
        failures.append("AUDIT_DATASET_MISMATCH")
    for check in sorted(REQUIRED_AUDITS):
        item = audit.get("checks", {}).get(check, {})
        if item.get("status") != "PASS" or not item.get("evidence"):
            failures.append("AUDIT_"+check.upper())
    if metadata.get("forecast_basis") != "GROSS_RETURN_MINUS_EXECUTION_COST":
        failures.append("EXECUTION_COST_CONTRACT")
    if not {"positive", "outperform", "top_decile", "top_one"} <= set(metadata.get("calibration", {})):
        failures.append("CALIBRATION_INCOMPLETE")
    for name in ("positive", "outperform", "top_decile", "top_one"):
        try:
            values = metadata["calibration"][name]
            valid = all(math.isfinite(float(values[key])) for key in ("slope", "intercept"))
        except (KeyError, TypeError, ValueError):
            valid = False
        if not valid:
            failures.append("CALIBRATION_INVALID_"+name.upper())
    metrics = metadata.get("locked_test", {})
    for key, predicate in {
        "sessions": lambda x: x >= 63,
        "excess_vs_spy": lambda x: x > 0,
        "rank_ic": lambda x: x > 0,
        "max_drawdown": lambda x: x > -.2,
        "brier": lambda x: 0 <= x < .25,
    }.items():
        try:
            valid = math.isfinite(float(metrics[key])) and predicate(float(metrics[key]))
        except (KeyError, TypeError, ValueError):
            valid = False
        if not valid:
            failures.append("LOCKED_TEST_"+key.upper())
    try:
        values = [*metrics["mean_ci95_block"], *metrics["excess_ci95_block"], metrics["mean"], metrics["momentum_mean"]]
        if not (all(math.isfinite(float(value)) for value in values)
                and metrics["mean_ci95_block"][0] > 0 and metrics["excess_ci95_block"][0] > 0
                and metrics["mean"] >= metrics["momentum_mean"]):
            failures.append("INSUFFICIENT_BASELINE_OR_CONFIDENCE_EVIDENCE")
    except (KeyError, TypeError, IndexError):
        failures.append("MISSING_BASELINE_OR_CONFIDENCE_EVIDENCE")
    return failures


def candidate_path(root, model_id):
    if not model_id or Path(model_id).name != model_id or model_id in {".", ".."} or ":" in model_id:
        raise ValueError("Invalid model ID")
    return Path(root) / model_id


def promote(root, model_id, audit_path):
    root = Path(root)
    path = candidate_path(root, model_id)
    candidate = Ensemble.load(path)
    if candidate.metadata.get("model_id") != model_id:
        raise ValueError("Candidate model ID does not match directory")
    audit = json.loads(Path(audit_path).read_text(encoding="utf-8"))
    failures = promotion_failures(candidate.metadata, audit)
    if failures:
        raise ValueError("Promotion rejected: "+", ".join(failures))
    manifest = path / "manifest.json"
    receipt = {"model_id": model_id, "manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
               "promoted_at": utcnow().isoformat(), "audit": audit}
    with FileLock(root / "promotion.lock"):
        temporary = root / "production.json.tmp"
        temporary.write_text(json.dumps(receipt, indent=2, allow_nan=False), encoding="utf-8")
        temporary.replace(root / "production.json")
    return receipt


def load_production(root):
    root = Path(root)
    receipt = json.loads((root / "production.json").read_text(encoding="utf-8"))
    path = candidate_path(root, receipt["model_id"])
    if hashlib.sha256((path / "manifest.json").read_bytes()).hexdigest() != receipt["manifest_sha256"]:
        raise ValueError("Promoted manifest changed")
    model = Ensemble.load(path)
    failures = promotion_failures(model.metadata, receipt["audit"])
    if failures:
        raise ValueError("Production evidence no longer valid: "+", ".join(failures))
    model.metadata["status"] = "PRODUCTION"
    return model
