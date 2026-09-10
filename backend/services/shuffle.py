"""Deterministic per-session answer-option shuffling.

Randomises the display order of a question's choices so the correct answer
isn't always in the same slot, without touching how questions are stored.
The permutation is derived from (session_id, question_number) so it's stable
for the lifetime of a session -- the same question always displays the same
shuffled order to the same session -- but differs across sessions and breaks
the positional bias a fixed answer-key column produces.
"""

import hashlib
import random

LETTERS = ["a", "b", "c", "d", "e", "f"]


def _seed(session_id: str, question_number: int) -> int:
    digest = hashlib.sha256(f"{session_id}:{question_number}".encode()).digest()
    return int.from_bytes(digest[:8], "big")


def shuffled_letter_order(question: dict, session_id: str, question_number: int) -> list[str]:
    """Original storage letters (a-f) present on `question`, in the order they
    should be displayed. `order[i]` is the original letter shown at display
    position `i` (i.e. display letter LETTERS[i]).
    """
    available = [letter for letter in LETTERS if question.get(f"choice_{letter}")]
    order = available[:]
    random.Random(_seed(session_id, question_number)).shuffle(order)
    return order


def display_to_original_letter(
    question: dict, session_id: str, question_number: int, display_letter: str
) -> str:
    """Map a letter the student picked (as rendered) back to the original
    storage letter, using the same deterministic shuffle. Raises ValueError if
    the display letter doesn't correspond to an available choice.
    """
    order = shuffled_letter_order(question, session_id, question_number)
    try:
        index = LETTERS.index(display_letter)
    except ValueError as exc:
        raise ValueError(f"Unknown answer letter: {display_letter}") from exc
    if index >= len(order):
        raise ValueError(f"No choice at display position {display_letter} for this question.")
    return order[index]
