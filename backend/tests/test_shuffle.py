import pytest

from backend.services.shuffle import LETTERS, display_to_original_letter, shuffled_letter_order

FULL_QUESTION = {
    "choice_a": "A text", "choice_b": "B text", "choice_c": "C text",
    "choice_d": "D text", "choice_e": None, "choice_f": None,
}

PARTIAL_QUESTION = {
    "choice_a": "A text", "choice_b": "B text", "choice_c": None,
    "choice_d": None, "choice_e": None, "choice_f": None,
}


def test_shuffled_order_is_permutation_of_available_letters():
    order = shuffled_letter_order(FULL_QUESTION, "session-1", 1)
    assert sorted(order) == ["a", "b", "c", "d"]


def test_shuffled_order_excludes_empty_choices():
    order = shuffled_letter_order(PARTIAL_QUESTION, "session-1", 1)
    assert sorted(order) == ["a", "b"]


def test_shuffled_order_deterministic_for_same_session_and_question():
    order1 = shuffled_letter_order(FULL_QUESTION, "session-1", 5)
    order2 = shuffled_letter_order(FULL_QUESTION, "session-1", 5)
    assert order1 == order2


def test_shuffled_order_varies_across_sessions():
    orders = {tuple(shuffled_letter_order(FULL_QUESTION, f"session-{i}", 1)) for i in range(30)}
    # With 4 choices there are 24 possible permutations -- 30 different
    # sessions should not all collapse onto the same one.
    assert len(orders) > 1


def test_shuffled_order_varies_across_questions_in_same_session():
    orders = {tuple(shuffled_letter_order(FULL_QUESTION, "session-1", n)) for n in range(30)}
    assert len(orders) > 1


def test_display_to_original_letter_round_trips():
    order = shuffled_letter_order(FULL_QUESTION, "session-42", 3)
    for display_letter, original_letter in zip(LETTERS, order):
        assert display_to_original_letter(FULL_QUESTION, "session-42", 3, display_letter) == original_letter


def test_display_to_original_letter_rejects_letter_beyond_available_choices():
    with pytest.raises(ValueError):
        display_to_original_letter(PARTIAL_QUESTION, "session-1", 1, "c")


def test_display_to_original_letter_rejects_unknown_letter():
    with pytest.raises(ValueError):
        display_to_original_letter(FULL_QUESTION, "session-1", 1, "z")
