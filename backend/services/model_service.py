from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any
import warnings

import joblib
import numpy as np
import pandas as pd
from joblib.numpy_pickle import NumpyUnpickler
from sklearn.exceptions import InconsistentVersionWarning
from sklearn.tree import _tree

from ml.url_features import FEATURE_NAMES, extract_features
from utils.errors import ConfigurationError
from utils.url_processing import PreparedUrl

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


class _LegacyTreePlaceholder:
    def __init__(self, *args) -> None:
        self.args = args
        self.state = None

    def __setstate__(self, state) -> None:
        self.state = state


class _LegacyLossPlaceholder:
    def __init__(self, *args) -> None:
        self.args = args
        self.state = None

    def __setstate__(self, state) -> None:
        self.state = state


class _LegacyTreeUnpickler(NumpyUnpickler):
    def find_class(self, module, name):
        if module == "sklearn.tree._tree" and name == "Tree":
            return _LegacyTreePlaceholder
        if module == "sklearn.ensemble._gb_losses":
            return _LegacyLossPlaceholder
        return super().find_class(module, name)


@dataclass(frozen=True)
class ModelPrediction:
    storage_result: str
    api_result: str
    confidence: float
    model_name: str
    model_version: str
    heuristics: dict


class PhishingModelService:
    _FEATURE_EXTRACTION_FEATURE_COUNT = 30
    _LOW_SIGNAL_PHISHING_CONFIDENCE_THRESHOLD = 0.75

    def __init__(self, config) -> None:
        self._config = config
        self._load_lock = Lock()
        self._model: Any | None = None
        self._artifact_bundle: dict[str, Any] | None = None
        self._vectorizer: Any | None = None
        self._input_mode: str | None = None
        # Pre-sort once so _match_trusted_domain never re-sorts on every call
        self._sorted_trusted_domains: list[str] = sorted(
            config.get("TRUSTED_DOMAINS", []), key=len, reverse=True
        )

    def predict(self, prepared_url: PreparedUrl) -> ModelPrediction:
        self._ensure_loaded()
        features = self._transform(prepared_url)
        prediction = self._model.predict(features)[0]
        phishing_label = self._resolve_phishing_label()
        phishing_probability = self._extract_probability(features)
        if phishing_probability is None:
            confidence = 0.5
        elif prediction == phishing_label:
            confidence = round(phishing_probability, 4)
        else:
            confidence = round(1 - phishing_probability, 4)
        is_phishing = prediction == phishing_label
        result = self._apply_trusted_domain_override(
            ModelPrediction(
                storage_result="phishing" if is_phishing else "legitimate",
                api_result="phishing" if is_phishing else "legit",
                confidence=confidence,
                model_name=type(self._model).__name__,
                model_version=self._config["MODEL_VERSION"],
                heuristics=self._build_prediction_heuristics(prepared_url),
            ),
            getattr(prepared_url, "hostname", ""),
        )
        result = self._apply_low_signal_phishing_override(result)
        return self._apply_brand_impersonation_override(result)

    def _apply_trusted_domain_override(
        self,
        prediction: ModelPrediction,
        hostname: str,
    ) -> ModelPrediction:
        trusted_domain = self._match_trusted_domain(hostname)
        educational_domain = self._match_educational_domain(hostname)
        if prediction.api_result != "phishing":
            return prediction

        if trusted_domain:
            updated_heuristics = dict(prediction.heuristics)
            updated_heuristics["trusted_domain_override"] = trusted_domain
            return ModelPrediction(
                storage_result="legitimate",
                api_result="legit",
                confidence=0.99,
                model_name=prediction.model_name,
                model_version=prediction.model_version,
                heuristics=updated_heuristics,
            )

        if educational_domain:
            updated_heuristics = dict(prediction.heuristics)
            updated_heuristics["educational_domain_override"] = educational_domain
            return ModelPrediction(
                storage_result="legitimate",
                api_result="legit",
                confidence=0.98,
                model_name=prediction.model_name,
                model_version=prediction.model_version,
                heuristics=updated_heuristics,
            )

        return prediction

    def _build_prediction_heuristics(self, prepared_url: PreparedUrl) -> dict:
        hostname = getattr(prepared_url, "hostname", "")
        trusted_domain = self._match_trusted_domain(hostname) if hostname else None
        educational_domain = self._match_educational_domain(hostname) if hostname else None
        url_features = extract_features(prepared_url.normalized_url)
        return {
            **prepared_url.heuristics,
            "url_length": int(url_features.get("url_length", 0)),
            "uses_ip_address": bool(url_features.get("uses_ip_address", 0)),
            "has_suspicious_tld": bool(url_features.get("has_suspicious_tld", 0)),
            "abnormal_domain_structure": bool(url_features.get("abnormal_domain_structure", 0)),
            "contains_encoded_chars": bool(url_features.get("contains_encoded_chars", 0)),
            "contains_hex_pattern": bool(url_features.get("contains_hex_pattern", 0)),
            "trusted_domain": trusted_domain,
            "educational_domain": educational_domain,
        }

    def _apply_low_signal_phishing_override(self, prediction: ModelPrediction) -> ModelPrediction:
        if prediction.api_result != "phishing":
            return prediction

        heuristics = prediction.heuristics
        if heuristics.get("trusted_domain"):
            return prediction
        if prediction.confidence >= self._LOW_SIGNAL_PHISHING_CONFIDENCE_THRESHOLD:
            return prediction
        if heuristics.get("matched_brands") or heuristics.get("suspicious_terms"):
            return prediction
        if heuristics.get("uses_ip_address") or heuristics.get("has_suspicious_tld"):
            return prediction
        if heuristics.get("abnormal_domain_structure"):
            return prediction
        if heuristics.get("contains_encoded_chars") or heuristics.get("contains_hex_pattern"):
            return prediction
        if not heuristics.get("uses_https"):
            return prediction
        if int(heuristics.get("subdomain_depth", 0)) > 1:
            return prediction
        if int(heuristics.get("path_depth", 0)) > 1:
            return prediction
        if int(heuristics.get("url_length", 0)) > 96:
            return prediction

        updated_heuristics = dict(heuristics)
        updated_heuristics["low_signal_override"] = {
            "confidence_threshold": self._LOW_SIGNAL_PHISHING_CONFIDENCE_THRESHOLD,
            "reason": "phishing prediction had low confidence and no phishing indicators",
        }
        return ModelPrediction(
            storage_result="legitimate",
            api_result="legit",
            confidence=max(0.75, round(1 - prediction.confidence, 4)),
            model_name=prediction.model_name,
            model_version=prediction.model_version,
            heuristics=updated_heuristics,
        )

    def _apply_brand_impersonation_override(self, prediction: ModelPrediction) -> ModelPrediction:
        if prediction.api_result != "legit":
            return prediction

        if prediction.heuristics.get("trusted_domain"):
            return prediction

        matched_brands = prediction.heuristics.get("matched_brands") or []
        suspicious_terms = prediction.heuristics.get("suspicious_terms") or []
        if not matched_brands or not suspicious_terms:
            return prediction

        updated_heuristics = dict(prediction.heuristics)
        updated_heuristics["brand_impersonation_override"] = {
            "matched_brands": matched_brands,
            "suspicious_terms": suspicious_terms,
        }
        return ModelPrediction(
            storage_result="phishing",
            api_result="phishing",
            confidence=max(prediction.confidence, 0.97),
            model_name=prediction.model_name,
            model_version=prediction.model_version,
            heuristics=updated_heuristics,
        )

    def _match_trusted_domain(self, hostname: str) -> str | None:
        for trusted_domain in self._sorted_trusted_domains:
            if hostname == trusted_domain or hostname.endswith(f".{trusted_domain}"):
                return trusted_domain
        return None

    @staticmethod
    def _match_educational_domain(hostname: str) -> str | None:
        labels = [label for label in hostname.lower().split(".") if label]
        if len(labels) < 2:
            return None
        if labels[-1] == "edu":
            return "edu"
        if len(labels) >= 3 and labels[-2] == "edu" and labels[-1].isalpha() and 2 <= len(labels[-1]) <= 3:
            return ".".join(labels[-2:])
        return None

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return

        with self._load_lock:
            if self._model is not None:
                return
            try:
                loaded_model = self._load_model(self._config["MODEL_PATH"])
                if isinstance(loaded_model, dict) and loaded_model.get("artifact_type") == "phishing_model_bundle":
                    self._artifact_bundle = loaded_model
                    self._model = loaded_model.get("model")
                else:
                    self._artifact_bundle = None
                    self._model = loaded_model
                self._vectorizer = self._load_vectorizer(self._config["VECTORIZER_PATH"])
                self._input_mode = self._determine_input_mode()
            except FileNotFoundError as exc:
                raise ConfigurationError("Model artifacts are missing from the configured paths") from exc
            except Exception as exc:
                raise ConfigurationError(f"Unable to load model artifacts: {exc}") from exc

    def _transform(self, prepared_url: PreparedUrl):
        if self._input_mode == "vectorizer":
            return self._transform_text_inputs([prepared_url.combined_text])
        if self._input_mode == "url_feature_bundle":
            return self._transform_bundle_features(prepared_url)
        if self._input_mode == "feature_extraction":
            return self._extract_url_features(prepared_url)
        raise ConfigurationError("Model input mode is not configured")

    def _transform_text_inputs(self, text_inputs: list[str]):
        if self._vectorizer is None:
            raise ConfigurationError("Vectorizer-backed model is not configured correctly")
        transformed = self._vectorizer.transform(text_inputs)
        return transformed.toarray() if hasattr(transformed, "toarray") else transformed

    def _extract_url_features(self, prepared_url: PreparedUrl):
        try:
            from feature import FeatureExtraction
        except ImportError as exc:
            raise ConfigurationError(f"Feature extraction dependencies are unavailable: {exc}") from exc

        feature_values = np.asarray(FeatureExtraction(prepared_url.normalized_url).getFeaturesList(), dtype=float)
        expected_feature_count = int(getattr(self._model, "n_features_in_", feature_values.shape[-1]))
        if feature_values.ndim != 1 or len(feature_values) != expected_feature_count:
            raise ConfigurationError(
                f"Feature extraction produced {len(feature_values)} values but the model expects {expected_feature_count}"
            )
        return feature_values.reshape(1, -1)

    def _extract_probability(self, features) -> float | None:
        if not hasattr(self._model, "predict_proba"):
            return None
        probabilities = np.asarray(self._model.predict_proba(features)[0], dtype=float)
        probability_sum = probabilities.sum()
        if probability_sum > 0:
            probabilities = probabilities / probability_sum
        classes = np.asarray(getattr(self._model, "classes_", []))
        phishing_label = self._resolve_phishing_label()
        if phishing_label in classes:
            phishing_index = int(np.where(classes == phishing_label)[0][0])
            return float(probabilities[phishing_index])
        return float(max(probabilities))

    def _load_model(self, model_path: str):
        try:
            return self._load_joblib_artifact(model_path)
        except Exception as exc:
            if not self._requires_legacy_compatibility(exc):
                raise
            return self._load_legacy_model(model_path)

    def _load_vectorizer(self, vectorizer_path: str):
        if self._artifact_bundle is not None:
            return None
        path = Path(vectorizer_path)
        if not path.exists():
            return None

        vectorizer = self._load_joblib_artifact(path)
        if self._vectorizer_feature_count(vectorizer) == getattr(self._model, "n_features_in_", None):
            return vectorizer
        return None

    def _determine_input_mode(self) -> str:
        if self._artifact_bundle is not None:
            return "url_feature_bundle"
        if self._vectorizer is not None:
            return "vectorizer"
        if getattr(self._model, "n_features_in_", None) == self._FEATURE_EXTRACTION_FEATURE_COUNT:
            return "feature_extraction"
        raise ConfigurationError("Model artifacts are incompatible with the configured input pipeline")

    def _transform_bundle_features(self, prepared_url: PreparedUrl):
        if self._artifact_bundle is None:
            raise ConfigurationError("Bundle-backed model is not configured correctly")
        feature_names = self._artifact_bundle.get("feature_names") or FEATURE_NAMES
        feature_mode = self._artifact_bundle.get("feature_mode", "url_features_v1")
        if feature_mode == "legacy_feature_extraction":
            legacy_values = self._extract_url_features(prepared_url).reshape(-1)
            feature_values = {
                name: float(legacy_values[index]) for index, name in enumerate(LEGACY_FEATURE_NAMES)
            }
        else:
            feature_values = extract_features(prepared_url.normalized_url)
        return pd.DataFrame(
            [{name: float(feature_values.get(name, 0.0)) for name in feature_names}],
            columns=feature_names,
        )

    def _load_legacy_model(self, model_path: str):
        try:
            with open(model_path, "rb") as handle:
                with warnings.catch_warnings():
                    warnings.filterwarnings("ignore", category=InconsistentVersionWarning)
                    model = _LegacyTreeUnpickler(
                        model_path,
                        handle,
                        ensure_native_byte_order=False,
                    ).load()
            self._restore_legacy_sklearn_state(model)
            return model
        except Exception as exc:
            raise ConfigurationError(f"Unable to rebuild legacy model artifact: {exc}") from exc

    def _restore_legacy_sklearn_state(self, artifact: Any, seen: set[int] | None = None) -> None:
        if seen is None:
            seen = set()

        artifact_id = id(artifact)
        if artifact_id in seen:
            return
        seen.add(artifact_id)

        if hasattr(artifact, "tree_") and isinstance(getattr(artifact, "tree_"), _LegacyTreePlaceholder):
            self._restore_tree(artifact)
        if hasattr(artifact, "_loss") and isinstance(getattr(artifact, "_loss"), _LegacyLossPlaceholder):
            if hasattr(artifact, "_get_loss"):
                artifact._loss = artifact._get_loss(sample_weight=None)
            else:
                raise ConfigurationError("Legacy gradient boosting loss state could not be rebuilt")

        if isinstance(artifact, np.ndarray):
            if artifact.dtype == object:
                for item in artifact.flat:
                    self._restore_legacy_sklearn_state(item, seen)
            return
        if isinstance(artifact, dict):
            for item in artifact.values():
                self._restore_legacy_sklearn_state(item, seen)
            return
        if isinstance(artifact, (list, tuple, set)):
            for item in artifact:
                self._restore_legacy_sklearn_state(item, seen)
            return
        if hasattr(artifact, "__dict__"):
            for item in artifact.__dict__.values():
                self._restore_legacy_sklearn_state(item, seen)

    def _restore_tree(self, estimator: Any) -> None:
        placeholder = getattr(estimator, "tree_", None)
        if not isinstance(placeholder, _LegacyTreePlaceholder) or placeholder.state is None:
            raise ConfigurationError("Legacy model tree state could not be recovered")

        tree_state = dict(placeholder.state)
        nodes = tree_state["nodes"]
        if "missing_go_to_left" not in nodes.dtype.names:
            tree_state["nodes"] = self._upgrade_legacy_nodes(nodes)

        restored_tree = _tree.Tree(
            estimator.n_features_in_,
            self._tree_n_classes(estimator),
            estimator.n_outputs_,
        )
        restored_tree.__setstate__(tree_state)
        estimator.tree_ = restored_tree
        if not hasattr(estimator, "monotonic_cst"):
            estimator.monotonic_cst = None

    def _resolve_phishing_label(self):
        classes = np.asarray(getattr(self._model, "classes_", []))
        if classes.size == 0:
            return 1

        class_values = set(classes.tolist())
        if class_values == {-1, 1}:
            return -1
        if 1 in class_values:
            return 1
        return classes[0].item() if hasattr(classes[0], "item") else classes[0]

    @staticmethod
    def _vectorizer_feature_count(vectorizer: Any) -> int | None:
        if hasattr(vectorizer, "get_feature_names_out"):
            return len(vectorizer.get_feature_names_out())
        vocabulary = getattr(vectorizer, "vocabulary_", None)
        if isinstance(vocabulary, dict):
            return len(vocabulary)
        return None

    @staticmethod
    def _load_joblib_artifact(path: str | Path):
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=InconsistentVersionWarning)
            return joblib.load(path)

    @staticmethod
    def _requires_legacy_compatibility(exc: Exception) -> bool:
        message = str(exc)
        return "sklearn.ensemble._gb_losses" in message or "node array from the pickle has an incompatible dtype" in message

    @staticmethod
    def _tree_n_classes(estimator: Any):
        if hasattr(estimator, "n_classes_"):
            n_classes = getattr(estimator, "n_classes_")
            if np.isscalar(n_classes):
                return np.array([int(n_classes)], dtype=np.intp)
            return np.asarray(n_classes, dtype=np.intp)
        return np.ones(getattr(estimator, "n_outputs_", 1), dtype=np.intp)

    @staticmethod
    def _upgrade_legacy_nodes(nodes):
        upgraded_dtype = np.dtype(
            {
                "names": list(nodes.dtype.names) + ["missing_go_to_left"],
                "formats": [nodes.dtype.fields[name][0] for name in nodes.dtype.names] + ["u1"],
                "offsets": [nodes.dtype.fields[name][1] for name in nodes.dtype.names] + [nodes.dtype.itemsize],
                "itemsize": nodes.dtype.itemsize + 8,
            }
        )
        upgraded_nodes = np.empty(nodes.shape, dtype=upgraded_dtype)
        for name in nodes.dtype.names:
            upgraded_nodes[name] = nodes[name]
        upgraded_nodes["missing_go_to_left"] = 0
        return upgraded_nodes
