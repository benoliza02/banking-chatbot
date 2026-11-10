"""A small local chat window for the banking assistant, using only the Python standard library.

Run from the project folder:
    python -m app.chat_server
then open http://localhost:8000 in your browser. Stop it with Ctrl+C.

Every answer is also checked live with the same evaluators the Robot tests use,
so you can see groundedness, unsupported numbers and sensitive-data checks per message.
"""
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from app.assistant import ask
from qa import evaluators as ev

PAGE = Path(__file__).parent / "static" / "chat.html"
HOST = "127.0.0.1"
PORT = int(os.getenv("PORT", "8000"))


def answer_with_checks(question: str, hallucinate: bool = False) -> dict:
    """Ask the assistant, then run the QA checks on its answer."""
    previous = os.environ.get("FAKE_MODE")
    if hallucinate:
        os.environ["FAKE_MODE"] = "hallucinate"
    try:
        result = ask(question)
    finally:
        if previous is None:
            os.environ.pop("FAKE_MODE", None)
        else:
            os.environ["FAKE_MODE"] = previous

    answer, context = result["answer"], result["context"]
    return {
        "answer": answer,
        "sources": result["sources"],
        "backend": os.getenv("LLM_BACKEND", "fake"),
        "checks": {
            "refusal": ev.is_refusal(answer),
            "groundedness": ev.groundedness(answer, context) if context else None,
            "unsupported_numbers": ev.unsupported_numbers(answer, context),
            "sensitive_data": ev.pii_found(answer),
        },
    }


class ChatHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ("/", "/index.html"):
            self.send_error(404)
            return
        self._send(200, "text/html; charset=utf-8", PAGE.read_bytes())

    def do_POST(self):
        if self.path != "/ask":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, json.JSONDecodeError):
            self._json(400, {"error": "The request could not be read."})
            return
        question = str(data.get("question", "")).strip()[:500]
        if not question:
            self._json(400, {"error": "Type a question first."})
            return
        try:
            self._json(200, answer_with_checks(question, bool(data.get("hallucinate"))))
        except Exception as exc:  # show backend problems (e.g. missing API key) in the chat
            self._json(500, {"error": f"The assistant failed: {exc}"})

    def _json(self, status: int, payload: dict):
        self._send(status, "application/json", json.dumps(payload).encode("utf-8"))

    def _send(self, status: int, content_type: str, body: bytes):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):  # keep the terminal quiet
        pass


if __name__ == "__main__":
    server = HTTPServer((HOST, PORT), ChatHandler)
    print(f"Aurora Bank assistant is running at http://localhost:{PORT}  (backend: {os.getenv('LLM_BACKEND', 'fake')})")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
