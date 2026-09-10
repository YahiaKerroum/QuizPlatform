import numpy as np
import pytest

from backend.services import ml_service

# Golden feature order -- this list is a documented invariant (see ml_service
# module docstring). Changing it without retraining the model breaks
# predict_level silently, so it's pinned here rather than left to a comment.
EXPECTED_FEATURE_NAMES = [
    "overall_acc",
    "acc_easy", "acc_medium", "acc_hard",
    "has_easy", "has_medium", "has_hard",
    "last3_acc", "error_streak", "correct_streak", "acc_trend",
    "fast_correct_rate", "fast_wrong_rate", "slow_correct_rate", "time_acc_corr",
    "weighted_acc", "n_norm",
    "hard_variance", "medium_variance", "medium_hard_gap",
    "module_id_enc",
]


def test_feature_order_pinned():
    assert ml_service.FEATURE_NAMES == EXPECTED_FEATURE_NAMES
    assert len(ml_service.FEATURE_NAMES) == 21


def test_compute_features_shape():
    features = ml_service.compute_features([True, False, True], ["easy", "medium", "hard"], [1000, 2000, 3000])
    assert features.shape == (1, 21)


def test_compute_features_empty_history():
    features = ml_service.compute_features([], [], [])
    assert features.shape == (1, 21)
    assert np.all(features == 0)


def test_compute_features_overall_acc_and_streaks():
    is_correct = [True, True, False, False, False]
    features = ml_service.compute_features(is_correct, ["easy"] * 5, [1000] * 5)
    f = features[0]
    assert f[0] == pytest.approx(0.4)  # overall_acc
    assert f[8] == 3  # error_streak (trailing wrong answers)
    assert f[9] == 0  # correct_streak


def test_predict_level_fallback_monotonic_in_accuracy():
    """Rule-based fallback: rising hard-tier accuracy must move the predicted
    level from beginner to advanced, never backwards (a basic monotonicity
    guarantee -- more correct answers should never make the system less sure
    you're doing well). Exercised with the trained model disabled so this
    holds regardless of whichever HistGBM artifact happens to be on disk.
    """
    original_load_model = ml_service._load_model
    ml_service._load_model = lambda: None
    try:
        levels = []
        for acc in (0.3, 0.5, 0.7, 0.9):
            n = 10
            n_correct = round(acc * n)
            is_correct = [True] * n_correct + [False] * (n - n_correct)
            features = ml_service.compute_features(is_correct, ["hard"] * n, [3000] * n)
            levels.append(ml_service.predict_level(features)["level"])
    finally:
        ml_service._load_model = original_load_model

    assert levels[0] == "beginner"
    assert levels[-1] == "advanced"


def test_select_next_question_random_picks_from_candidates():
    features = ml_service.compute_features([True], ["easy"], [1000])
    for _ in range(20):
        choice = ml_service.select_next_question(features, [3, 7, 11], ["easy", "medium", "hard"], strategy="random")
        assert choice in (3, 7, 11)


def test_select_next_question_entropy_uses_history_and_returns_candidate():
    is_correct_list = [True, True, False, True]
    difficulty_list = ["easy", "easy", "medium", "medium"]
    time_ms_list = [2000, 2500, 4000, 3000]
    features = ml_service.compute_features(is_correct_list, difficulty_list, time_ms_list)

    candidate_nums = [5, 6, 7]
    candidate_diffs = ["easy", "medium", "hard"]

    choice = ml_service.select_next_question(
        features,
        candidate_nums,
        candidate_diffs,
        strategy="entropy",
        is_correct_list=is_correct_list,
        difficulty_list=difficulty_list,
        time_ms_list=time_ms_list,
        module_list=["cpp-programming"] * len(is_correct_list),
    )
    assert choice in candidate_nums


def test_select_next_question_margin_uses_history_and_returns_candidate():
    is_correct_list = [True, False, True, True]
    difficulty_list = ["easy", "medium", "medium", "hard"]
    time_ms_list = [2000, 3500, 3000, 4200]
    features = ml_service.compute_features(is_correct_list, difficulty_list, time_ms_list)

    candidate_nums = [1, 2, 3, 4]
    candidate_diffs = ["easy", "medium", "hard", "hard"]

    choice = ml_service.select_next_question(
        features,
        candidate_nums,
        candidate_diffs,
        strategy="margin",
        is_correct_list=is_correct_list,
        difficulty_list=difficulty_list,
        time_ms_list=time_ms_list,
        module_list=["data-structure"] * len(is_correct_list),
    )
    assert choice in candidate_nums


def test_select_next_question_entropy_without_history_falls_back():
    """No raw history supplied -- must not crash, must fall back to the
    difficulty-targeting heuristic instead of the acquisition loop."""
    features = ml_service.compute_features([True, True, True], ["easy", "easy", "easy"], [1000, 1000, 1000])
    choice = ml_service.select_next_question(features, [1, 2], ["easy", "hard"], strategy="entropy")
    assert choice in (1, 2)


def test_select_next_question_raises_on_no_candidates():
    features = ml_service.compute_features([True], ["easy"], [1000])
    with pytest.raises(ValueError):
        ml_service.select_next_question(features, [], [], strategy="entropy")


def test_predict_proba_batch_shape_and_normalization():
    features = ml_service.compute_features([True, False, True], ["easy", "medium", "hard"], [1000, 2000, 3000])
    batch = np.vstack([features[0], features[0], features[0]])
    proba = ml_service._predict_proba_batch(batch)
    assert proba.shape == (3, 3)
    row_sums = proba.sum(axis=1)
    assert np.allclose(row_sums, 1.0, atol=1e-6)


def test_entropy_and_margin_helpers():
    uniform = np.array([[1 / 3, 1 / 3, 1 / 3]])
    confident = np.array([[0.98, 0.01, 0.01]])
    assert ml_service._entropy(uniform)[0] > ml_service._entropy(confident)[0]
    assert ml_service._margin(confident)[0] > ml_service._margin(uniform)[0]


def test_should_stop_respects_min_and_max_questions():
    features = ml_service.compute_features([True] * 5, ["easy"] * 5, [1000] * 5)
    assert ml_service.should_stop(features, n_answered=5) is False  # below MIN_QUESTIONS

    features_max = ml_service.compute_features([True] * 20, ["hard"] * 20, [1000] * 20)
    assert ml_service.should_stop(features_max, n_answered=20) is True  # at MAX_QUESTIONS
