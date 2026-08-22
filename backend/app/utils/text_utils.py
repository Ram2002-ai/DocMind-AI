"""Text utilities"""


def count_words(text: str) -> int:
    """Count words in text"""
    return len(text.split())


def count_characters(text: str, include_spaces: bool = True) -> int:
    """Count characters in text"""
    if include_spaces:
        return len(text)
    return len(text.replace(" ", ""))


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to maximum length"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def extract_first_lines(text: str, num_lines: int = 5) -> str:
    """Extract first N lines from text"""
    lines = text.split('\n')
    return '\n'.join(lines[:num_lines])
