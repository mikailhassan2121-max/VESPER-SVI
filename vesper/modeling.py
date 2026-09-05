"""Chronological candidate training. Locked test data never selects model weights."""
import hashlib
import json
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from vesper.calendar import utcnow
from vesper.features import FEATURES


def purged_folds(frame, min_train=252, validation_sessions=63, embargo_sessions=1):
    days = sorted(frame.session.unique())
    for start in range(min_train + embargo_sessions, len(days), validation_sessions):
        validation_days = days[start:start + validation_sessions]
        if len(validation_days) < validation_sessions:
            break
        validation = frame[frame.session.isin(validation_days)]
        boundary = validation.cutoff.min()
        training = frame[(frame.session.isin(days[:start - embargo_sessions])) &
                         (frame.label_end < boundary)]
        if training.session.nunique() >= min_train:
            yield training, validation


def validate_dataset(frame):
    required = set(FEATURES) | {"ticker", "session", "cutoff", "feature_available_at", "label_end",
                               "entry_time", "target_return", "target_gap", "target_intraday", "spy_return",
                               "sector_return", "cost", "pit_universe", "source"}
    missing = required - set(frame)
    if missing:
        raise ValueError(f"Missing dataset fields: {sorted(missing)}")
    if frame.duplicated(["session", "ticker"]).any():
        raise ValueError("Duplicate session/ticker rows")
    for col in ("cutoff", "feature_available_at", "entry_time", "label_end"):
        frame[col] = pd.to_datetime(frame[col], utc=True)
    if (frame.feature_available_at > frame.cutoff).any() or (frame.entry_time <= frame.cutoff).any():
        raise ValueError("Feature cutoff/entry leakage")
    if (frame.label_end <= frame.entry_time).any():
        raise ValueError("Invalid holding horizon")
    if not frame.pit_universe.eq(True).all():
        raise ValueError("Point-in-time universe required")
    if not frame.source.eq("massive").all():
        raise ValueError("Unsupported or synthetic dataset provenance")
    labels = ["target_return", "target_gap", "target_intraday", "spy_return", "sector_return", "cost"]
    if not np.isfinite(frame[labels].to_numpy()).all() or (frame.cost < 0).any():
        raise ValueError("Invalid labels or costs; unresolved delistings must be reconciled")
    if (frame.groupby("session").size() < 100).any():
        raise ValueError("Cross-sectional training requires at least 100 securities per session")
    return frame.sort_values(["session", "ticker"]).reset_index(drop=True)


class Ensemble:
    def __init__(self, models, weight=.5, metadata=None):
        self.models, self.weight, self.metadata = models, weight, metadata or {}

    @classmethod
    def fit(cls, frame):
        frame = frame.sort_values(["session", "ticker"])
        x = frame[FEATURES]
        params = dict(n_estimators=100, num_leaves=15, learning_rate=.04, min_child_samples=100,
                      verbosity=-1, n_jobs=2, random_state=17)
        models = {}
        for name, target in (("total", "target_return"), ("gap", "target_gap"),
                             ("intraday", "target_intraday"), ("excess", "excess")):
            y = frame.target_return - frame.spy_return if target == "excess" else frame[target]
            models[name] = lgb.LGBMRegressor(objective="huber", **params).fit(x, y).booster_
        ranks = frame.groupby("session").target_return.rank(pct=True)
        targets = {"positive": frame.target_return > 0, "outperform": frame.target_return > frame.spy_return,
                   "top_decile": ranks >= .9, "top_five": ranks >= .95, "top_one": ranks >= .99,
                   "gap_positive": frame.target_gap > 0, "intraday_positive": frame.target_intraday > 0}
        for name, y in targets.items():
            if y.nunique() != 2:
                raise ValueError(f"Insufficient classes for {name}")
            models[name] = lgb.LGBMClassifier(**params).fit(x, y.astype(int)).booster_
        for q in (.05, .25, .5, .75, .95):
            models[f"q{q}"] = lgb.LGBMRegressor(objective="quantile", alpha=q, **params).fit(x, frame.target_return).booster_
        relevance = np.minimum((ranks * 10).astype(int), 9)
        models["rank"] = lgb.LGBMRanker(objective="lambdarank", **params).fit(
            x, relevance, group=frame.groupby("session", sort=True).size().to_list()).booster_
        return cls(models)

    def predict(self, frame):
        x = frame[FEATURES]
        out = frame.copy()
        values = {name: model.predict(x) for name, model in self.models.items()}
        decomposed = (1 + values["gap"]) * (1 + values["intraday"]) - 1
        out["expected_return"] = self.weight * values["total"] + (1 - self.weight) * decomposed
        out["expected_excess"] = values["excess"]
        out["expected_gap"], out["expected_intraday"] = values["gap"], values["intraday"]
        out["disagreement"] = np.abs(values["total"] - decomposed)
        quantiles = np.sort(np.column_stack([values[f"q{q}"] for q in (.05, .25, .5, .75, .95)]), axis=1)
        for i, name in enumerate(("q05", "q25", "q50", "q75", "q95")):
            out[name] = quantiles[:, i]
        for name in ("positive", "outperform", "top_decile", "top_five", "top_one"):
            out[f"p_{name}"] = values[name]
        out["ranking_prediction"] = values["rank"]
        out["uncertainty"] = out.q95 - out.q05 + out.disagreement
        return out

    def save(self, directory):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=False)
        hashes = {}
        for name, model in self.models.items():
            path = directory / f"{name}.txt"
            model.save_model(str(path))
            hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest = self.metadata | {"features": FEATURES, "weight": self.weight, "hashes": hashes}
        (directory / "manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False), encoding="utf-8")

    @classmethod
    def load(cls, directory, production=False):
        directory = Path(directory)
        metadata = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
        if metadata["features"] != FEATURES:
            raise ValueError("Feature schema mismatch")
        if production and metadata.get("status") != "PRODUCTION":
            raise ValueError("Model has not passed production promotion")
        models = {}
        for name, expected in metadata["hashes"].items():
            path = directory / f"{name}.txt"
            if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                raise ValueError("Model fingerprint mismatch")
            models[name] = lgb.Booster(model_file=str(path))
        return cls(models, metadata["weight"], metadata)


def metrics(predictions):
    frame = predictions.copy()
    frame["utility"] = frame.expected_excess - frame.cost - frame.uncertainty * .1
    selected = frame.sort_values("utility", ascending=False).groupby("session").head(1).sort_values("session")
    returns = selected.target_return - selected.cost
    wealth = (1 + returns).cumprod()
    peak = wealth.cummax().clip(lower=1)
    correlations = [spearmanr(g.ranking_prediction, g.target_return).statistic
                    for _, g in frame.groupby("session") if g.ranking_prediction.nunique() > 1]
    top5 = frame.sort_values("utility", ascending=False).groupby("session").head(5)
    return {"sessions": len(selected), "mean": float(returns.mean()), "median": float(returns.median()),
            "positive_rate": float((returns > 0).mean()),
            "excess_vs_spy": float((returns - selected.spy_return).mean()),
            "max_drawdown": float((wealth / peak - 1).min()),
            "rank_ic": float(np.mean(correlations)) if correlations else 0,
            "top5_mean": float((top5.target_return - top5.cost).mean()),
            "brier": float(((frame.p_positive - (frame.target_return > 0)) ** 2).mean()),
            "mean_ci95_normal": [float(returns.mean() - 1.96 * returns.std() / np.sqrt(len(returns))),
                                 float(returns.mean() + 1.96 * returns.std() / np.sqrt(len(returns)))],
            "spy_mean": float(selected.spy_return.mean()),
            "momentum_mean": float(frame.sort_values("return_30m", ascending=False).groupby("session").head(1).target_return.mean()),
            "universe_mean": float(frame.groupby("session").target_return.mean().mean())}


def train(dataset_path, model_dir, locked_start):
    frame = validate_dataset(pd.read_parquet(dataset_path))
    locked = frame[frame.session >= locked_start]
    development = frame[(frame.session < locked_start) & (frame.label_end < locked.cutoff.min())]
    if locked.session.nunique() < 63:
        raise ValueError("Reserve at least 63 locked test sessions")
    predictions = []
    for training, validation in purged_folds(development):
        predictions.append(Ensemble.fit(training).predict(validation))
    if not predictions:
        raise ValueError("Insufficient history for 252 training + embargo + 63 validation sessions")
    oof = pd.concat(predictions)
    direct = oof.expected_return * 2 - ((1 + oof.expected_gap) * (1 + oof.expected_intraday) - 1)
    gap = (1 + oof.expected_gap) * (1 + oof.expected_intraday) - 1
    errors = [np.mean((direct - oof.target_return) ** 2), np.mean((gap - oof.target_return) ** 2)]
    weight = float((1 / max(errors[0], 1e-12)) / sum(1 / max(e, 1e-12) for e in errors))
    candidate = Ensemble.fit(development)
    candidate.weight = weight
    model_id = "candidate-" + utcnow().strftime("%Y%m%dT%H%M%S%f")
    candidate.metadata = {"model_id": model_id, "status": "CANDIDATE", "trained_at": utcnow().isoformat(),
                          "dataset_sha256": hashlib.sha256(Path(dataset_path).read_bytes()).hexdigest(),
                          "training_start": str(development.session.min()), "training_end": str(development.session.max()),
                          "locked_start": locked_start, "walkforward": metrics(oof),
                          "locked_test": metrics(candidate.predict(locked)),
                          "limitations": ["Probability calibration requires independent evaluation",
                                           "Promotion requires independently audited provenance and live parity"]}
    candidate.save(Path(model_dir) / model_id)
    report = "# VESPER model validation\n\nCandidate only; no profitability claim.\n\n```json\n"
    report += json.dumps(candidate.metadata, indent=2) + "\n```\n"
    Path("MODEL_VALIDATION_REPORT.md").write_text(report, encoding="utf-8")
    return candidate.metadata
