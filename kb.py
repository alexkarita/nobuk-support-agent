"""Simple keyword-based search over the knowledge_base folder."""
import re
from pathlib import Path

KB_DIR = Path(__file__).parent / "knowledge_base"

STOPWORDS = {
    "what", "how", "the", "and", "for", "can", "does", "your", "you",
    "are", "with", "this", "that", "from", "about",
}


def search_kb(query: str, top_k: int = 3) -> str:
    terms = [
        t.lower()
        for t in re.findall(r"\w+", query)
        if len(t) > 2 and t.lower() not in STOPWORDS
    ]
    if not terms:
        return "No relevant information found in the knowledge base."

    scored = []
    for path in KB_DIR.glob("**/*"):
        if path.suffix.lower() not in {".md", ".txt"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        # score per paragraph so we return the most relevant chunks
        for para in re.split(r"\n\s*\n", text):
            score = sum(para.lower().count(t) for t in terms)
            if score > 0:
                scored.append((score, path.name, para.strip()))

    scored.sort(key=lambda x: x[0], reverse=True)
    if not scored:
        return "No relevant information found in the knowledge base."
    return "\n\n---\n\n".join(f"[{name}]\n{para}" for _, name, para in scored[:top_k])