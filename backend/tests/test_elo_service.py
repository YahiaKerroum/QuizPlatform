import pytest

from backend.services import elo_service


def test_expected_score_is_half_for_equal_ratings():
    assert elo_service.expected_score(1200, 1200) == pytest.approx(0.5)


def test_expected_score_favors_higher_rated_student():
    assert elo_service.expected_score(1600, 1200) > 0.5
    assert elo_service.expected_score(800, 1200) < 0.5


def test_correct_answer_raises_student_and_lowers_item_rating():
    new_student, new_item = elo_service.update_ratings(1200, 1200, correct=True)
    assert new_student > 1200
    assert new_item < 1200


def test_incorrect_answer_lowers_student_and_raises_item_rating():
    new_student, new_item = elo_service.update_ratings(1200, 1200, correct=False)
    assert new_student < 1200
    assert new_item > 1200


def test_beating_a_much_harder_item_moves_ratings_more_than_an_easy_one():
    _, easy_item_delta = elo_service.update_ratings(1200, 800, correct=True)
    _, hard_item_delta = elo_service.update_ratings(1200, 1600, correct=True)
    # Correctly answering a harder-than-you item is more surprising, so it
    # should move the item's rating down by more.
    assert (1600 - hard_item_delta) > (800 - easy_item_delta)


def test_update_is_zero_sum_in_k_weighted_surprise():
    student, item = 1300.0, 1100.0
    new_student, new_item = elo_service.update_ratings(student, item, correct=True)
    student_delta = new_student - student
    item_delta = new_item - item
    # Same underlying surprise term, scaled by each side's own K factor.
    assert student_delta / elo_service.K_STUDENT == pytest.approx(-(item_delta / elo_service.K_ITEM))


def test_repeated_correct_answers_converge_student_rating_upward():
    rating, item_rating = 1200.0, 1200.0
    for _ in range(20):
        rating, item_rating = elo_service.update_ratings(rating, item_rating, correct=True)
    assert rating > 1200.0
    assert item_rating < 1200.0
