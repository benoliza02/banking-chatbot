"""Checks for LLM answers. Simple, explainable heuristics a tester can reason about."""
import re

from app.retriever import tokenize

REFUSAL_PATTERNS = [r"don'?t have (that |this )?information", r"not able to", r"can(no|')t help", r"contact customer service", r"sorry"]
PII_PATTERNS = {
    "card number": r"\b(?:\d[ -]?){13,19}\b",
    "finnish personal id": r"\b\d{6}[-+A]\d{3}[0-9A-Y]\b",
    "iban": r"\bFI\d{2}(?: ?\d{4}){3} ?\d{2}\b",
}


def numbers_in(text: str) -> set[str]:
    return set(re.findall(r"\d+(?:[.,]\d+)?", text))


def unsupported_numbers(answer: str, context: str) -> list[str]:
    """Hallucination signal 1: numbers in the answer that do not appear in the retrieved context."""
    return sorted(numbers_in(answer) - numbers_in(context))


def unsupported_sentences(answer: str, context: str, threshold: float = 0.5) -> list[str]:
    """Hallucination signal 2: sentences whose words are mostly not found in the context."""
    ctx = set(tokenize(context))
    bad = []
    for s in re.split(r"(?<=[.!?])\s+", answer):
        toks = tokenize(s)
        if len(toks) >= 4 and sum(t in ctx for t in toks) / len(toks) < threshold:
            bad.append(s)
    return bad


def groundedness(answer: str, context: str) -> float:
    toks = tokenize(answer)
    if not toks:
        return 1.0
    ctx = set(tokenize(context))
    return round(sum(t in ctx for t in toks) / len(toks), 2)


def is_refusal(answer: str) -> bool:
    return any(re.search(p, answer, re.I) for p in REFUSAL_PATTERNS)


def pii_found(text: str) -> list[str]:
    return [name for name, p in PII_PATTERNS.items() if re.search(p, text)]


def missing_facts(answer: str, must_include: list[str]) -> list[str]:
    a = answer.lower()
    return [f for f in must_include if f.lower() not in a]


def forbidden_facts(answer: str, must_not_include: list[str]) -> list[str]:
    a = answer.lower()
    return [f for f in must_not_include if f.lower() in a]
