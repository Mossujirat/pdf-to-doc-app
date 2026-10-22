"""The search of a log for anything of a document: what the privacy tests look for."""

from collections.abc import Sequence


def leaked(lines: Sequence[str], log: str) -> list[str]:
    """Every run of 8 characters of the document's text `lines`, without a space, that the log holds."""
    fragments = {line[start : start + 8] for line in lines for start in range(len(line) - 7)}
    return sorted(fragment for fragment in fragments if " " not in fragment and fragment in log)
