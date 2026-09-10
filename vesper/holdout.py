"""A locked date range can be evaluated only once within this model registry."""
import json
from datetime import date
from pathlib import Path

from filelock import FileLock

from vesper.calendar import utcnow


def claim_holdout(directory, start, end, fingerprint, model_id):
    start, end = date.fromisoformat(str(start)), date.fromisoformat(str(end))
    if end < start:
        raise ValueError("Invalid holdout interval")
    directory = Path(directory) / "holdouts"
    directory.mkdir(parents=True, exist_ok=True)
    with FileLock(directory / "registry.lock"):
        for path in directory.glob("*.json"):
            previous = json.loads(path.read_text(encoding="utf-8"))
            if start <= date.fromisoformat(previous["end"]) and end >= date.fromisoformat(previous["start"]):
                raise ValueError("Locked test dates already evaluated or reserved; use new unseen dates")
        path = directory / f"{start}_{end}.json"
        with path.open("x", encoding="utf-8") as handle:
            json.dump({"start": str(start), "end": str(end), "dataset_fingerprint": fingerprint,
                       "model_id": model_id, "reserved_at": utcnow().isoformat(),
                       "policy": "Reservation survives failed evaluation; no automatic reuse"}, handle, indent=2)
    return path
