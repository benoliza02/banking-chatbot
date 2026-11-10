"""Pluggable LLM backends. Choose with the LLM_BACKEND environment variable:
  fake       - deterministic, no API key, used in CI (default)
  anthropic  - needs ANTHROPIC_API_KEY (optional ANTHROPIC_MODEL)
  openai     - needs OPENAI_API_KEY (optional OPENAI_MODEL)
  ollama     - local model via Ollama (optional OLLAMA_MODEL, default llama3.1)
FAKE_MODE=hallucinate makes the fake backend invent facts, to show the tests catching it.
"""
import json
import os
import re
import urllib.request


def generate(system: str, user: str) -> str:
    backend = os.getenv("LLM_BACKEND", "fake").lower()
    if backend == "anthropic":
        import anthropic
        client = anthropic.Anthropic()
        msg = client.messages.create(
            model=os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5"),
            max_tokens=400, temperature=0, system=system,
            messages=[{"role": "user", "content": user}],
        )
        return msg.content[0].text.strip()
    if backend == "openai":
        from openai import OpenAI
        client = OpenAI()
        r = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), temperature=0,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        )
        return r.choices[0].message.content.strip()
    if backend == "ollama":
        body = json.dumps({"model": os.getenv("OLLAMA_MODEL", "llama3.1"), "stream": False,
                           "options": {"temperature": 0},
                           "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}).encode()
        req = urllib.request.Request("http://localhost:11434/api/chat", data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read())["message"]["content"].strip()
    return _fake(user)


def _fake(user: str) -> str:
    """Answers with the context sentences that best match the question. No invention."""
    context = user.split("CONTEXT:", 1)[1].split("QUESTION:", 1)[0] if "CONTEXT:" in user else ""
    question = user.split("QUESTION:", 1)[-1]
    if not context.strip():
        return "I'm sorry, I don't have information about that. Please contact customer service."
    # Use only the best-matching document (the first one), like a careful human agent would.
    top_doc = context.split("\n\n# ")[0]
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n", top_doc) if s.strip() and not s.startswith("#")]
    answer = " ".join(sentences[:4])
    if os.getenv("FAKE_MODE") == "hallucinate":
        answer += " As a bonus, you also get 3 percent cashback on all purchases."
    return answer
