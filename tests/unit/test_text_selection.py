from app.services.text_selection import sentence_bounds, word_spans, words_in


def words(text: str) -> list[str]:
    return [text[s:e] for s, e in word_spans(text)]


def test_punctuation_is_not_a_word_and_apostrophes_are_kept() -> None:
    assert words("Don't stop, I’m testing it!") == [
        "Don't",
        "stop",
        "I’m",
        "testing",
        "it",
    ]


def test_hyphenated_words_stay_together() -> None:
    assert words("A well-known bug.") == ["A", "well-known", "bug"]


def test_vietnamese_letters_are_words() -> None:
    assert words("Tôi đi làm.") == ["Tôi", "đi", "làm"]


def test_words_in_selection_counts_partial_overlap() -> None:
    text = "She looks after her sister."
    start = text.index("looks")
    end = text.index("after") + len("after")

    assert [text[s:e] for s, e in words_in(text, start, end)] == ["looks", "after"]


def test_sentence_bounds_find_the_sentence_with_the_selection() -> None:
    text = "I read a book. I want to book a room! Thanks."
    start = text.index("book a")

    s, e = sentence_bounds(text, start, start + 4)

    assert text[s:e] == "I want to book a room!"


def test_selection_across_two_sentences_keeps_both() -> None:
    text = "Hi there. How are you?"

    s, e = sentence_bounds(text, text.index("there"), text.index("How") + 3)

    assert text[s:e] == "Hi there. How are you?"


def test_offsets_are_code_points() -> None:
    text = "😀 I read a book."
    start = text.index("book")

    assert start == 11  # the emoji counts as one code point
    assert text[start : start + 4] == "book"
