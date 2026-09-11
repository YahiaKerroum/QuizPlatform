"""Elo ratings for students (per module) and items.

A student and an item both start at DEFAULT_RATING and are treated as two
players in a game the student "wins" by answering correctly. Standard
symmetric Elo update, O(1) per answer, no retraining, no cold start beyond
the shared starting rating -- exactly the KT baseline the doc's own
prioritisation calls the best accuracy-per-line-of-code in the whole
proposal.
"""

DEFAULT_RATING = 1200.0
K_STUDENT = 32.0
K_ITEM = 16.0


def expected_score(student_rating: float, item_rating: float) -> float:
    """P(student answers this item correctly), by the logistic Elo curve."""
    return 1.0 / (1.0 + 10 ** ((item_rating - student_rating) / 400.0))


def update_ratings(student_rating: float, item_rating: float, correct: bool) -> tuple[float, float]:
    """Return (new_student_rating, new_item_rating) after one answer.

    The student and item move by their own K-factor in opposite directions:
    a correct answer against a high-rated (hard) item raises the student's
    rating more than the same answer against an easy item, and lowers the
    item's rating -- the item turned out easier than its rating implied.
    """
    actual_student = 1.0 if correct else 0.0
    expected_student = expected_score(student_rating, item_rating)

    new_student = student_rating + K_STUDENT * (actual_student - expected_student)
    new_item = item_rating + K_ITEM * (expected_student - actual_student)
    return new_student, new_item
