from app.services.vocabulary_service import meaning_key, normalize_lemma


def test_lemma_is_lower_case_with_single_spaces() -> None:
    assert normalize_lemma("  Look   After ") == "look after"


def test_meaning_key_ignores_case_spacing_and_punctuation() -> None:
    assert meaning_key("  Đặt (phòng)! ") == meaning_key("đặt phòng")


def test_meaning_key_keeps_vietnamese_accents() -> None:
    assert meaning_key("đặt") != meaning_key("dat")


def test_meaning_key_treats_composed_and_decomposed_accents_alike() -> None:
    composed = "sách"
    decomposed = "sách"  # "a" + combining acute accent

    assert composed != decomposed
    assert meaning_key(composed) == meaning_key(decomposed)
