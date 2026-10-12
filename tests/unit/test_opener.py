from app.services.opener import build_opener


def test_opener_is_one_short_question_about_the_topic() -> None:
    opener = build_opener("coffee shop", "A2")

    assert "coffee shop" in opener
    assert opener.count("?") == 1


def test_beginner_and_intermediate_openers_differ() -> None:
    assert build_opener("work", "A1") != build_opener("work", "B2")
    assert build_opener("work", "A1") == build_opener("work", "A2")
