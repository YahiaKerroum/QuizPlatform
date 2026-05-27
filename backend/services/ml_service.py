"""
ML service -- adaptive question selection and student level estimation.

Uses a HistGradientBoostingClassifier trained on single-module synthetic sessions
(best_model_single_module.pkl, 21 features, sessions 12-20 questions).

Feature set (21 total, must match training order exactly):
    [0]     overall_acc
    [1-3]   acc_easy, acc_medium, acc_hard
    [4-6]   has_easy, has_medium, has_hard
    [7-10]  last3_acc, error_streak, correct_streak, acc_trend
    [11-14] time-accuracy interaction: fast_correct_rate, fast_wrong_rate,
            slow_correct_rate, time_acc_corr
    [15-16] weighted_acc, n_norm
    [17-19] hard_variance, medium_variance, medium_hard_gap
    [20]    module_id_enc (categorical 0-5)

Indices [0-14] are identical to the previous 27-feature model so
select_next_question / should_stop / rule-based fallback need no index changes.
"""

import pickle
import random
import logging
import warnings
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

# -- Model loading -------------------------------------------------------------
_MODEL_PATH = Path(__file__).parent.parent.parent / "ML NOTEBOOKS" / "models" / "best_model_single_module.pkl"
_model = None


def _load_model():
    global _model
    if _model is not None:
        return _model
    if not _MODEL_PATH.exists():
        logger.warning("ML model not found at %s -- falling back to rule-based prediction.", _MODEL_PATH)
        return None
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            bundle = pickle.load(open(_MODEL_PATH, "rb"))
        _model = bundle.get("model") if isinstance(bundle, dict) else bundle
        logger.info("ML model loaded from %s", _MODEL_PATH)
    except Exception as exc:
        logger.error("Failed to load ML model: %s", exc)
    return _model


# -- Feature set constants -----------------------------------------------------
MODULES_ORDER = [
    "computer-fundamentals", "cpp-programming", "cyber-security",
    "data-structure", "operating-system", "software-engineering",
]

FEATURE_NAMES: list[str] = [
    "overall_acc",
    "acc_easy", "acc_medium", "acc_hard",
    "has_easy", "has_medium", "has_hard",
    "last3_acc", "error_streak", "correct_streak", "acc_trend",
    "fast_correct_rate", "fast_wrong_rate", "slow_correct_rate", "time_acc_corr",
    "weighted_acc", "n_norm",
    "hard_variance", "medium_variance", "medium_hard_gap",
    "module_id_enc",
]

# -- Stop criterion ------------------------------------------------------------
# Adaptive thresholds: require higher confidence for early stops because
# short sessions (n=8-11) carry more binomial noise — don't halt unless very sure.
_CONFIDENCE_BY_LENGTH = [
    (8,  0.85),   # n=8-9:  very early, need near-certainty
    (10, 0.82),   # n=10-11
    (12, 0.78),   # n=12-14
    (15, 0.75),   # n=15+:  enough data, standard threshold
]
MIN_QUESTIONS = 8
MAX_QUESTIONS = 20


def _confidence_threshold(n_answered: int) -> float:
    for min_n, threshold in reversed(_CONFIDENCE_BY_LENGTH):
        if n_answered >= min_n:
            return threshold
    return _CONFIDENCE_BY_LENGTH[0][1]


_LEVELS = ["beginner", "intermediate", "advanced"]


# =============================================================================
# PUBLIC API
# =============================================================================

def compute_features(
    is_correct_list: list[bool],
    difficulty_list: list[str | None],
    time_ms_list: list[int],
    module_list: list[str | None] | None = None,
) -> np.ndarray:
    """Return a (1, 21) feature vector matching the single-module training pipeline."""
    n = len(is_correct_list)
    if n == 0:
        return np.zeros((1, 21))

    correct = np.array(is_correct_list, dtype=float)
    diffs   = [str(d).lower().strip() if d else "" for d in difficulty_list]

    mask_easy   = np.array([d == "easy"   for d in diffs])
    mask_medium = np.array([d == "medium" for d in diffs])
    mask_hard   = np.array([d == "hard"   for d in diffs])

    acc_easy   = float(correct[mask_easy].mean())   if mask_easy.any()   else 0.0
    acc_medium = float(correct[mask_medium].mean()) if mask_medium.any() else 0.0
    acc_hard   = float(correct[mask_hard].mean())   if mask_hard.any()   else 0.0

    last3  = float(correct[-3:].mean()) if n >= 3 else float(correct.mean())
    first3 = float(correct[:3].mean())  if n >= 3 else float(correct.mean())

    err_streak = cor_streak = 0
    for v in reversed(correct):
        if v == 0: err_streak += 1
        else: break
    for v in reversed(correct):
        if v == 1: cor_streak += 1
        else: break

    # Time-accuracy interaction (self-normalized per session)
    t = np.array(time_ms_list, dtype=float) if time_ms_list else np.full(n, 5000.0)
    t_mean = float(t.mean())
    fast = t < t_mean
    fast_correct_rate = float(((fast) & (correct == 1)).mean())
    fast_wrong_rate   = float(((fast) & (correct == 0)).mean())
    slow_correct_rate = float(((~fast) & (correct == 1)).mean())
    if n >= 3 and t.std() > 0 and correct.std() > 0:
        speed   = 1.0 / (t + 1e-3)
        speed_z = (speed - speed.mean()) / (speed.std() + 1e-9)
        c_z     = (correct - correct.mean()) / (correct.std() + 1e-9)
        time_acc_corr = float(np.mean(speed_z * c_z))
    else:
        time_acc_corr = 0.0

    # Difficulty-weighted accuracy
    w_sum = float(mask_easy.sum()) + 2 * float(mask_medium.sum()) + 3 * float(mask_hard.sum())
    weighted_acc = (
        acc_easy   * float(mask_easy.sum())
        + 2 * acc_medium * float(mask_medium.sum())
        + 3 * acc_hard   * float(mask_hard.sum())
    ) / w_sum if w_sum > 0 else 0.0

    # Variance features (help discriminate intermediate class)
    hard_variance   = float(np.var(correct[mask_hard]))   if mask_hard.sum()   >= 2 else 0.0
    medium_variance = float(np.var(correct[mask_medium])) if mask_medium.sum() >= 2 else 0.0
    medium_hard_gap = acc_medium - acc_hard

    # Module identity (categorical)
    mods = [str(m).lower().strip() if m else "" for m in (module_list or [])]
    current_module = next((m for m in mods if m in MODULES_ORDER), "")
    module_id_enc  = float(MODULES_ORDER.index(current_module)) if current_module in MODULES_ORDER else 0.0

    return np.array([[
        float(correct.mean()), acc_easy, acc_medium, acc_hard,
        float(mask_easy.any()), float(mask_medium.any()), float(mask_hard.any()),
        last3, float(err_streak), float(cor_streak), last3 - first3,
        fast_correct_rate, fast_wrong_rate, slow_correct_rate, time_acc_corr,
        weighted_acc, n / 20.0,
        hard_variance, medium_variance, medium_hard_gap,
        module_id_enc,
    ]])


def predict_level(features: np.ndarray) -> dict:
    """
    Predict the student's knowledge level.

    Uses the trained HistGBM pipeline when available; falls back to a
    rule-based estimate keyed on accuracy-per-difficulty-tier otherwise.

    Returns {"level", "confidence", "probabilities"}.
    """
    model = _load_model()
    if model is not None:
        try:
            proba      = model.predict_proba(features)[0]
            classes    = list(getattr(model, "classes_", _LEVELS))
            proba_dict = {str(cls): float(p) for cls, p in zip(classes, proba)}
            level      = max(proba_dict, key=proba_dict.__getitem__)
            return {
                "level":         level,
                "confidence":    float(proba_dict[level]),
                "probabilities": proba_dict,
            }
        except Exception as exc:
            logger.error("predict_level model error: %s -- using fallback", exc)

    # Rule-based fallback
    f = features[0]
    overall_acc = float(f[0])
    acc_medium, acc_hard = float(f[2]), float(f[3])
    has_medium, has_hard = bool(f[5]), bool(f[6])

    if has_hard and acc_hard >= 0.70:
        level, raw = "advanced",     0.55 + min(acc_hard - 0.70,   0.30) / 0.30 * 0.44
    elif has_medium and acc_medium >= 0.65:
        level, raw = "intermediate", 0.55 + min(acc_medium - 0.65, 0.30) / 0.30 * 0.44
    elif has_hard and acc_hard < 0.40:
        level, raw = "beginner",     0.55 + min(0.40 - acc_hard,   0.40) / 0.40 * 0.44
    elif has_medium and acc_medium < 0.40:
        level, raw = "beginner",     0.55 + min(0.40 - acc_medium, 0.40) / 0.40 * 0.44
    elif overall_acc < 0.40:
        level, raw = "beginner",     0.55 + min(0.40 - overall_acc, 0.40) / 0.40 * 0.30
    else:
        level, raw = "intermediate", 0.50 + overall_acc * 0.12

    confidence = min(max(raw, 0.0), 0.99)
    proba_dict = {k: (1.0 - confidence) / 2 for k in _LEVELS}
    proba_dict[level] = confidence
    return {"level": level, "confidence": confidence, "probabilities": proba_dict}


def select_next_question(
    features: np.ndarray,
    candidate_question_numbers: list[int],
    candidate_difficulties: list[str | None],
    strategy: str = "uncertainty",
) -> int:
    """Pick the next question by targeting the appropriate difficulty tier."""
    if not candidate_question_numbers:
        raise ValueError("No candidate questions remaining.")

    if strategy == "random":
        return random.choice(candidate_question_numbers)

    f = features[0]
    overall_acc  = float(f[0])
    has_medium   = bool(f[5])
    has_hard     = bool(f[6])
    error_streak = int(f[8])

    _diff_val = {"easy": 0.2, "medium": 0.5, "hard": 0.8}

    if error_streak >= 3:
        target_dv = 0.2
    elif not has_medium:
        target_dv = 0.5
    elif not has_hard and overall_acc >= 0.55:
        target_dv = 0.8
    elif overall_acc >= 0.70:
        target_dv = 0.8
    elif overall_acc >= 0.50:
        target_dv = 0.5
    else:
        target_dv = 0.2

    best_idx, best_score = 0, float("-inf")
    for i, (_, diff) in enumerate(zip(candidate_question_numbers, candidate_difficulties)):
        dv = _diff_val.get(str(diff).lower().strip() if diff else "medium", 0.5)
        score = -abs(dv - target_dv)
        if score > best_score:
            best_score, best_idx = score, i

    return candidate_question_numbers[best_idx]


def should_stop(features: np.ndarray, n_answered: int) -> bool:
    """Return True when the quiz should end."""
    if n_answered < MIN_QUESTIONS:
        return False
    if n_answered >= MAX_QUESTIONS:
        return True

    has_medium = bool(features[0][5])
    has_hard   = bool(features[0][6])
    if not (has_medium or has_hard):
        return False

    prediction = predict_level(features)
    return prediction["confidence"] >= _confidence_threshold(n_answered)
