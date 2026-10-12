"""FR01: the chatbot opens each conversation with one short question.

Built from a template (no AI call): free, instant and never fails.
"""

SIMPLE_LEVELS = ("A1", "A2")


def build_opener(topic: str, level: str) -> str:
    """A short, friendly first question about the topic, simpler for A1/A2."""
    if level in SIMPLE_LEVELS:
        return f"Hi! Let's talk about “{topic}”. What do you want to tell me first?"
    return (
        f"Hi! Today let's practise talking about “{topic}”. "
        "What's the first thing that comes to mind?"
    )
