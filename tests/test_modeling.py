import numpy as np
import pandas as pd
import pytest

from vesper.features import FEATURES
from vesper.modeling import Ensemble


def test_model_artifact_roundtrip_and_tamper_detection(tmp_path):
    # Synthetic data is exclusively a unit-test fixture, never production evidence.
    rng = np.random.default_rng(7)
    frame = pd.DataFrame(rng.normal(size=(400, len(FEATURES))), columns=FEATURES)
    frame["session"] = np.repeat(["2024-01-02", "2024-01-03"], 200)
    frame["ticker"] = [f"TEST{i:04d}" for i in range(400)]
    frame["target_return"] = frame.return_30m * .01 + rng.normal(0, .01, 400)
    frame["target_gap"] = frame.target_return * .6
    frame["target_intraday"] = frame.target_return * .4
    frame["spy_return"] = 0.0
    model = Ensemble.fit(frame)
    expected = model.predict(frame)
    directory = tmp_path / "candidate"
    model.save(directory)
    loaded = Ensemble.load(directory)
    np.testing.assert_allclose(expected.expected_return, loaded.predict(frame).expected_return)
    assert (expected.q05 <= expected.q25).all()
    assert (expected.q75 <= expected.q95).all()
    with pytest.raises(ValueError, match="promotion"):
        Ensemble.load(directory, production=True)
    path = directory / "total.txt"
    path.write_text(path.read_text() + "\nchanged\n")
    with pytest.raises(ValueError, match="fingerprint"):
        Ensemble.load(directory)
