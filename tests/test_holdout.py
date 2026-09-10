import pytest

from vesper.holdout import claim_holdout


def test_changed_dataset_cannot_reuse_overlapping_locked_dates(tmp_path):
    claim_holdout(tmp_path, "2025-01-01", "2025-03-31", "first", "candidate1")
    with pytest.raises(ValueError, match="already"):
        claim_holdout(tmp_path, "2025-03-01", "2025-06-30", "changed", "candidate2")
    assert claim_holdout(tmp_path, "2025-04-01", "2025-06-30", "new", "candidate3").exists()
