import re


def clean_text(text: str) -> str:
    """
    Clean extracted text by removing extra spaces,
    blank lines, and unnecessary formatting.
    """

    # Remove multiple spaces
    text = re.sub(r"[ ]+", " ", text)

    # Remove multiple blank lines
    text = re.sub(r"\n+", "\n", text)

    # Remove tabs
    text = text.replace("\t", " ")

    # Remove leading/trailing spaces
    text = text.strip()

    return text