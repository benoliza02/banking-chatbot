"""Very small keyword retriever (BM25-style scoring), so the project has no heavy dependencies."""
import math
import re
from pathlib import Path

KB_DIR = Path(__file__).parent / "knowledge_base"
STOPWORDS = set("a an the is are be to of in on for and or my your i you can do does how what when which it if with by at from this that".split())


def tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in STOPWORDS]


class Retriever:
    def __init__(self, kb_dir: Path = KB_DIR):
        self.docs = {p.stem: p.read_text(encoding="utf-8") for p in sorted(kb_dir.glob("*.md"))}
        self.tokens = {k: tokenize(v) for k, v in self.docs.items()}
        n = len(self.docs)
        df: dict[str, int] = {}
        for toks in self.tokens.values():
            for t in set(toks):
                df[t] = df.get(t, 0) + 1
        self.idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}
        self.avg_len = sum(len(t) for t in self.tokens.values()) / max(n, 1)

    def search(self, query: str, k: int = 2, min_score: float = 0.5) -> list[tuple[str, str, float]]:
        q = tokenize(query)
        scored = []
        for name, toks in self.tokens.items():
            score = 0.0
            for term in q:
                tf = toks.count(term)
                if tf:
                    score += self.idf.get(term, 0) * (tf * 2.2) / (tf + 1.2 * (0.25 + 0.75 * len(toks) / self.avg_len))
            if score >= min_score:
                scored.append((name, self.docs[name], round(score, 3)))
        return sorted(scored, key=lambda x: -x[2])[:k]
