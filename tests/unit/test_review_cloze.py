from app.services.review_service import BLANK, cloze_from_example, make_cloze


def test_cloze_blanks_the_selection_in_its_sentence() -> None:
    sentence = "She looks after her sister."
    start = sentence.index("looks after")

    assert (
        make_cloze(sentence, start, start + len("looks after"))
        == f"She {BLANK} her sister."
    )


def test_example_cloze_blanks_a_whole_word_ignoring_case() -> None:
    assert (
        cloze_from_example("Book a table, please.", ["book"])
        == f"{BLANK} a table, please."
    )


def test_example_cloze_does_not_blank_inside_another_word() -> None:
    assert cloze_from_example("I like bookshops.", ["book"]) is None


def test_example_cloze_tries_each_form() -> None:
    assert cloze_from_example("I booked it.", ["book", "booked"]) == f"I {BLANK} it."
