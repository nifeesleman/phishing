from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from sklearn.utils import resample

from ml.url_features import FEATURE_NAMES, build_feature_dataframe, normalize_url

try:
    from xgboost import XGBClassifier
except ImportError:  # pragma: no cover - optional dependency
    XGBClassifier = None


SAFE_LABELS = {"0", "safe", "legit", "benign", "clean", "normal"}
PHISHING_LABELS = {"1", "phishing", "scam", "malicious", "fraud", "suspicious"}
LEGACY_FEATURE_NAMES = [
    "UsingIP",
    "LongURL",
    "ShortURL",
    "Symbol",
    "Redirecting",
    "PrefixSuffix",
    "SubDomains",
    "HTTPS",
    "DomainRegLen",
    "Favicon",
    "NonStdPort",
    "HTTPSDomainURL",
    "RequestURL",
    "AnchorURL",
    "LinksInScriptTags",
    "ServerFormHandler",
    "InfoEmail",
    "AbnormalURL",
    "WebsiteForwarding",
    "StatusBarCust",
    "DisableRightClick",
    "UsingPopupWindow",
    "IframeRedirection",
    "AgeofDomain",
    "DNSRecording",
    "WebsiteTraffic",
    "PageRank",
    "GoogleIndex",
    "LinksPointingToPage",
    "StatsReport",
]


@dataclass(frozen=True)
class TrainingArtifacts:
    output_path: Path
    best_model_name: str
    best_metrics: dict[str, Any]
    all_metrics: dict[str, dict[str, Any]]
    rows_seen: int
    rows_used: int
    class_balance: dict[int, int]


@dataclass(frozen=True)
class PreparedTrainingSet:
    features: pd.DataFrame
    labels: pd.Series
    feature_names: list[str]
    feature_mode: str
    rows_used: int


def train_and_export_model(dataset_path: str | Path, output_path: str | Path) -> TrainingArtifacts:
    raw_dataset = pd.read_csv(dataset_path)
    prepared_training_set = _prepare_training_set(raw_dataset)
    if prepared_training_set.features.empty:
        raise ValueError("Dataset has no valid rows after cleaning")

    features = prepared_training_set.features
    labels = prepared_training_set.labels.astype(int)
    x_train, x_test, y_train, y_test = train_test_split(
        features,
        labels,
        test_size=0.2,
        random_state=42,
        stratify=labels,
    )
    balanced_train = _balance_training_split(x_train, y_train)

    candidates = _build_model_candidates(y_train)
    all_metrics: dict[str, dict[str, Any]] = {}
    best_name: str | None = None
    best_score: tuple[float, float, float, float] | None = None

    for model_name, estimator in candidates.items():
        fitted_model = clone(estimator)
        fitted_model.fit(balanced_train[0], balanced_train[1])
        predictions = fitted_model.predict(x_test)
        metrics = {
            "accuracy": round(float(accuracy_score(y_test, predictions)), 4),
            "precision": round(float(precision_score(y_test, predictions, zero_division=0)), 4),
            "recall": round(float(recall_score(y_test, predictions, zero_division=0)), 4),
            "f1_score": round(float(f1_score(y_test, predictions, zero_division=0)), 4),
            "confusion_matrix": confusion_matrix(y_test, predictions).tolist(),
        }
        all_metrics[model_name] = metrics
        candidate_score = (
            metrics["f1_score"],
            metrics["recall"],
            metrics["precision"],
            metrics["accuracy"],
        )
        if best_score is None or candidate_score > best_score:
            best_name = model_name
            best_score = candidate_score

    if best_name is None:
        raise ValueError("No candidate models were available for training")

    best_estimator = clone(candidates[best_name])
    full_features, full_labels = _balance_training_split(features, labels)
    best_estimator.fit(full_features, full_labels)

    artifact = {
        "artifact_type": "phishing_model_bundle",
        "pipeline_version": 1,
        "model_name": best_name,
        "model": best_estimator,
        "feature_names": prepared_training_set.feature_names,
        "feature_mode": prepared_training_set.feature_mode,
        "metrics": all_metrics[best_name],
        "all_metrics": all_metrics,
        "label_mapping": {"safe": 0, "phishing": 1},
    }
    output = Path(output_path)
    joblib.dump(artifact, output)

    return TrainingArtifacts(
        output_path=output,
        best_model_name=best_name,
        best_metrics=all_metrics[best_name],
        all_metrics=all_metrics,
        rows_seen=len(raw_dataset),
        rows_used=prepared_training_set.rows_used,
        class_balance=labels.value_counts().sort_index().to_dict(),
    )


def _prepare_training_set(dataset: pd.DataFrame) -> PreparedTrainingSet:
    try:
        return _prepare_url_dataset(dataset)
    except ValueError:
        return _prepare_structured_feature_dataset(dataset)


def _prepare_url_dataset(dataset: pd.DataFrame) -> PreparedTrainingSet:
    url_column = _detect_url_column(dataset)
    label_column = _detect_label_column(dataset)

    cleaned = dataset[[url_column, label_column]].copy()
    cleaned.columns = ["url", "raw_label"]
    cleaned = cleaned.dropna(subset=["url", "raw_label"])
    cleaned["url"] = cleaned["url"].astype(str).str.strip()
    cleaned["raw_label"] = cleaned["raw_label"].astype(str).str.strip().str.lower()
    cleaned["label"] = cleaned["raw_label"].map(_map_label)
    cleaned = cleaned.dropna(subset=["label"])
    cleaned = cleaned.drop_duplicates(subset=["url"])
    cleaned["normalized_url"] = cleaned["url"].map(_safe_normalize_url)
    cleaned = cleaned.dropna(subset=["normalized_url"])
    cleaned = cleaned.drop_duplicates(subset=["normalized_url"])
    cleaned = cleaned.reset_index(drop=True)
    return PreparedTrainingSet(
        features=build_feature_dataframe(cleaned["normalized_url"]),
        labels=cleaned["label"].astype(int),
        feature_names=FEATURE_NAMES,
        feature_mode="url_features_v1",
        rows_used=len(cleaned),
    )


def _prepare_structured_feature_dataset(dataset: pd.DataFrame) -> PreparedTrainingSet:
    label_column = _detect_label_column(dataset)
    feature_columns = [column for column in dataset.columns if column not in {label_column, "Index", "index"}]
    normalized_lookup = {column.lower(): column for column in feature_columns}
    if not all(name.lower() in normalized_lookup for name in (feature.lower() for feature in LEGACY_FEATURE_NAMES)):
        raise ValueError("Structured dataset is missing one or more expected feature columns")

    ordered_feature_columns = [normalized_lookup[name.lower()] for name in LEGACY_FEATURE_NAMES]
    cleaned = dataset[ordered_feature_columns + [label_column]].copy().dropna()
    raw_label_values = pd.to_numeric(cleaned[label_column], errors="coerce").dropna()
    uses_negative_phishing_labels = bool((raw_label_values == -1).any())
    cleaned["label"] = cleaned[label_column].map(
        lambda value: _map_structured_label(value, uses_negative_phishing_labels)
    )
    cleaned = cleaned.dropna(subset=["label"])
    features = cleaned[ordered_feature_columns].apply(pd.to_numeric, errors="coerce").dropna()
    labels = cleaned.loc[features.index, "label"].astype(int)
    return PreparedTrainingSet(
        features=features.reset_index(drop=True),
        labels=labels.reset_index(drop=True),
        feature_names=ordered_feature_columns,
        feature_mode="legacy_feature_extraction",
        rows_used=len(features),
    )


def _detect_url_column(dataset: pd.DataFrame) -> str:
    candidates = ["url", "urls", "link", "uri", "domain"]
    lowered = {column.lower(): column for column in dataset.columns}
    for candidate in candidates:
        if candidate in lowered:
            return lowered[candidate]
    raise ValueError("Dataset must include a URL column")


def _detect_label_column(dataset: pd.DataFrame) -> str:
    candidates = ["label", "labels", "class", "target", "result", "status"]
    lowered = {column.lower(): column for column in dataset.columns}
    for candidate in candidates:
        if candidate in lowered:
            return lowered[candidate]
    raise ValueError("Dataset must include a label column")


def _map_label(raw_label: str) -> int | None:
    if raw_label in SAFE_LABELS:
        return 0
    if raw_label in PHISHING_LABELS:
        return 1
    return None


def _map_structured_label(raw_label: Any, uses_negative_phishing_labels: bool) -> int | None:
    try:
        numeric = int(raw_label)
    except (TypeError, ValueError):
        return _map_label(str(raw_label).strip().lower())
    if uses_negative_phishing_labels:
        if numeric == -1:
            return 1
        if numeric == 1:
            return 0
        return None
    if numeric == 0:
        return 0
    if numeric == 1:
        return 1
    return None


def _safe_normalize_url(raw_url: str) -> str | None:
    try:
        return normalize_url(raw_url)
    except ValueError:
        return None


def _balance_training_split(features: pd.DataFrame, labels: pd.Series) -> tuple[pd.DataFrame, pd.Series]:
    joined = features.copy()
    joined["label"] = labels.values
    class_counts = joined["label"].value_counts()
    if len(class_counts) < 2:
        raise ValueError("Training data must contain both safe and phishing labels")

    majority_label = class_counts.idxmax()
    minority_label = class_counts.idxmin()
    majority_rows = joined[joined["label"] == majority_label]
    minority_rows = joined[joined["label"] == minority_label]

    if class_counts.max() <= class_counts.min() * 1.5:
        return joined.drop(columns=["label"]), joined["label"]

    resampled_minority = resample(
        minority_rows,
        replace=True,
        n_samples=len(majority_rows),
        random_state=42,
    )
    balanced = pd.concat([majority_rows, resampled_minority], ignore_index=True).sample(
        frac=1.0,
        random_state=42,
    )
    return balanced.drop(columns=["label"]), balanced["label"]


def _build_model_candidates(labels: pd.Series) -> dict[str, Any]:
    candidates: dict[str, Any] = {
        "logistic_regression": Pipeline(
            [
                ("scale", StandardScaler()),
                (
                    "model",
                    LogisticRegression(
                        max_iter=2000,
                        class_weight="balanced",
                        solver="liblinear",
                        random_state=42,
                    ),
                ),
            ]
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=300,
            class_weight="balanced",
            random_state=42,
        ),
        "gradient_boosting": GradientBoostingClassifier(random_state=42),
    }
    if XGBClassifier is not None:
        positives = max(int((labels == 1).sum()), 1)
        negatives = max(int((labels == 0).sum()), 1)
        candidates["xgboost"] = XGBClassifier(
            n_estimators=300,
            learning_rate=0.05,
            max_depth=6,
            subsample=0.9,
            colsample_bytree=0.9,
            reg_lambda=1.0,
            eval_metric="logloss",
            random_state=42,
            scale_pos_weight=round(negatives / positives, 4),
        )
    return candidates
