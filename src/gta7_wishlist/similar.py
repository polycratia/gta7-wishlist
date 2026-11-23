"""Similarity between proposals, so two people filing the same wish can be caught."""

from __future__ import annotations

import re
from collections.abc import Iterable

from gta7_wishlist.model import Proposal

SHINGLE_SIZE = 2
TITLE_WEIGHT = 2
DEFAULT_THRESHOLD = 0.45

STOP_WORDS = frozenset(
    """
    a about after again all also an and any are as at be been before being but
    by can could did do does done down each for from had has have he her his i
    if in into is it its just may me more most must my no not of on only or
    other our out over own she should so some such than that the their them
    then there these they this those to too under up us very was we were what
    when which while who will with would you your
    """.split()
)

_WORD = re.compile(r"[a-z0-9]+")
_PLURAL_ES = ("sses", "shes", "ches", "xes", "zes", "ses")


def similarity(a: Proposal, b: Proposal) -> float:
    """Score two proposals in 0..1, with the title counted twice."""
    title = _jaccard(shingles(a.title), shingles(b.title))
    body = _jaccard(shingles(_body(a)), shingles(_body(b)))
    return (TITLE_WEIGHT * title + body) / (TITLE_WEIGHT + 1)


def find_duplicates(
    proposals: Iterable[Proposal], threshold: float = DEFAULT_THRESHOLD
) -> list[tuple[Proposal, Proposal, float]]:
    """Return every pair at or above the threshold, best score first."""
    items = list(proposals)
    pairs: list[tuple[Proposal, Proposal, float]] = []

    for index, left in enumerate(items):
        for right in items[index + 1 :]:
            if declared_different(left, right):
                continue
            score = similarity(left, right)
            if score >= threshold:
                first, second = sorted((left, right), key=lambda item: _text(item.id))
                pairs.append((first, second, score))

    pairs.sort(key=lambda pair: (-pair[2], _text(pair[0].id), _text(pair[1].id)))
    return pairs


def declared_different(a: Proposal, b: Proposal) -> bool:
    """True when either proposal lists the other in not_duplicate_of."""
    return _text(b.id) in a.not_duplicate_of or _text(a.id) in b.not_duplicate_of


def shingles(text: object) -> frozenset[tuple[str, ...]]:
    words = _words(text)
    if len(words) < SHINGLE_SIZE:
        return frozenset((word,) for word in words)
    return frozenset(
        tuple(words[start : start + SHINGLE_SIZE])
        for start in range(len(words) - SHINGLE_SIZE + 1)
    )


def _body(proposal: Proposal) -> str:
    return f"{_text(proposal.problem)} {_text(proposal.proposal)}"


def _text(value: object) -> str:
    return value if isinstance(value, str) else ""


def _words(text: object) -> list[str]:
    return [
        _stem(word)
        for word in _WORD.findall(_text(text).lower())
        if word not in STOP_WORDS
    ]


def _stem(word: str) -> str:
    """Strip -s, -es, -ed and -ing; crude on purpose, it only has to pair wordings."""
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    if word.endswith(_PLURAL_ES) and len(word) > 4:
        return word[:-2]
    if word.endswith("s") and not word.endswith("ss") and len(word) > 3:
        return word[:-1]
    if word.endswith("ing") and len(word) > 5:
        return word[:-3]
    if word.endswith("ed") and len(word) > 4:
        return word[:-2]
    return word


def _jaccard(
    left: frozenset[tuple[str, ...]], right: frozenset[tuple[str, ...]]
) -> float:
    union = left | right
    if not union:
        return 0.0
    return len(left & right) / len(union)
