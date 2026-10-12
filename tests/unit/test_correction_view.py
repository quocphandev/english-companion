from app.schemas.conversation import CorrectionOut, Segment
from app.services.correction_view import build_correction_view


def correction(
    span: str, fix: str, category: str = "grammar", explanation: str = "Giải thích."
) -> CorrectionOut:
    return CorrectionOut(
        category=category,
        original_span=span,
        corrected_text=fix,
        explanation_vi=explanation,
    )


def joined(segments: list[Segment] | None) -> str:
    assert segments is not None
    return "".join(segment.text for segment in segments)


def changed(segments: list[Segment] | None) -> list[str]:
    assert segments is not None
    return [segment.text for segment in segments if segment.changed]


def test_no_corrections_means_no_card() -> None:
    assert build_correction_view("I went to work.", []) is None


def test_single_error_marks_original_and_corrected_sentence() -> None:
    view = build_correction_view(
        "Yesterday I go to work.", [correction("I go", "I went")]
    )

    assert view is not None
    assert joined(view.original) == "Yesterday I go to work."
    assert changed(view.original) == ["I go"]
    assert joined(view.corrected) == "Yesterday I went to work."
    assert changed(view.corrected) == ["I went"]
    assert len(view.errors) == 1
    assert view.suggestions == []


def test_span_matches_whole_words_only() -> None:
    view = build_correction_view("I am going to go home.", [correction("go", "walk")])

    assert view is not None
    assert joined(view.corrected) == "I am going to walk home."


def test_span_with_different_case_is_still_found() -> None:
    view = build_correction_view(
        "yesterday i go to work.", [correction("I go", "I went")]
    )

    assert view is not None
    # The original keeps the learner's own letters.
    assert changed(view.original) == ["i go"]
    assert joined(view.corrected) == "yesterday I went to work."


def test_span_not_in_the_sentence_is_listed_but_not_applied() -> None:
    view = build_correction_view("I go to work.", [correction("He go", "He goes")])

    assert view is not None
    assert view.corrected is None
    assert changed(view.original) == []
    assert len(view.errors) == 1


def test_several_errors_are_applied_in_sentence_order() -> None:
    corrections = [
        correction("an", "a", category="word_choice"),
        correction("I go", "I went"),
    ]

    view = build_correction_view("Yesterday I go to an shop.", corrections)

    assert view is not None
    assert joined(view.corrected) == "Yesterday I went to a shop."
    assert changed(view.corrected) == ["I went", "a"]


def test_same_span_twice_uses_two_different_places() -> None:
    corrections = [correction("I go", "I went"), correction("I go", "I went")]

    view = build_correction_view("I go home and I go out.", corrections)

    assert view is not None
    assert joined(view.corrected) == "I went home and I went out."


def test_overlapping_span_is_listed_but_not_applied() -> None:
    corrections = [correction("I go to", "I went to"), correction("go", "went")]

    view = build_correction_view("Yesterday I go to work.", corrections)

    assert view is not None
    assert joined(view.corrected) == "Yesterday I went to work."
    assert len(view.errors) == 2


def test_naturalness_tips_are_kept_apart_and_not_applied() -> None:
    corrections = [
        correction("I go", "I went"),
        correction("very like", "really like", category="naturalness"),
    ]

    view = build_correction_view("Yesterday I go out. I very like it.", corrections)

    assert view is not None
    assert [c.category for c in view.errors] == ["grammar"]
    assert [c.category for c in view.suggestions] == ["naturalness"]
    assert joined(view.corrected) == "Yesterday I went out. I very like it."


def test_only_style_tips_gives_no_corrected_sentence() -> None:
    view = build_correction_view(
        "I like it very much.",
        [correction("like it very much", "really love it", category="naturalness")],
    )

    assert view is not None
    assert view.errors == []
    assert view.corrected is None
    assert len(view.suggestions) == 1


def test_span_ending_with_punctuation_is_found() -> None:
    view = build_correction_view(
        "I live in hanoi.", [correction("hanoi.", "Hanoi.", "spelling")]
    )

    assert view is not None
    assert joined(view.corrected) == "I live in Hanoi."


def test_blank_span_is_ignored() -> None:
    view = build_correction_view("Hello.", [correction("   ", "Hi")])

    assert view is not None
    assert view.corrected is None
