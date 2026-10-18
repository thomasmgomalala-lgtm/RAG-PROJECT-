import math
import re
from collections import Counter

from app.services.database import connection


STOP_WORDS = {
    "a", "about", "and", "are", "as", "at", "be", "by", "did", "do", "does",
    "for", "from", "how", "in", "is", "it", "many", "of", "on", "or", "that",
    "the", "their", "to", "was", "were", "what", "when", "where", "which", "who", "with",
}


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+(?:['’-][a-z0-9]+)*", text.lower())


def _search_terms(text: str) -> list[str]:
    terms = []
    for term in tokenize(text):
        if term.endswith("'s"):
            term = term[:-2]
        if term in STOP_WORDS:
            continue
        if len(term) > 5 and term.endswith("ies"):
            term = term[:-3]
        elif len(term) > 4 and term.endswith("ed"):
            term = term[:-2]
        elif len(term) > 5 and term.endswith("ing"):
            term = term[:-3]
        elif len(term) > 4 and term.endswith("s"):
            term = term[:-1]
        terms.append(term)
    return terms


def retrieve(query: str, top_k: int = 5) -> list[dict]:
    query_terms = _search_terms(query)
    if not query_terms:
        return []

    with connection() as db:
        rows = db.execute(
            """SELECT chunks.document_id, documents.filename, chunks.page, chunks.content
               FROM chunks JOIN documents ON documents.id = chunks.document_id"""
        ).fetchall()

    if not rows:
        return []

    tokenized = [_search_terms(row["content"]) for row in rows]
    document_frequency = Counter(term for terms in tokenized for term in set(terms))
    query_counts = Counter(query_terms)
    query_phrases = [" ".join(pair) for pair in zip(query_terms, query_terms[1:])]
    scored = []
    total = len(rows)
    for row, terms in zip(rows, tokenized):
        frequencies = Counter(terms)
        score = 0.0
        for term, query_count in query_counts.items():
            if not frequencies[term]:
                continue
            inverse_frequency = math.log(1 + (total - document_frequency[term] + 0.5) / (document_frequency[term] + 0.5))
            score += inverse_frequency * (frequencies[term] * 2.2) / (frequencies[term] + 1.2) * query_count
        normalized_text = " ".join(terms)
        score += 5.0 * sum(phrase in normalized_text for phrase in query_phrases)
        if score > 0:
            scored.append((score, row))

    scored.sort(key=lambda item: item[0], reverse=True)
    maximum = scored[0][0] if scored else 1
    results = []
    seen_content = set()
    for score, row in scored:
        if row["content"] in seen_content:
            continue
        seen_content.add(row["content"])
        results.append({
            "document_id": row["document_id"],
            "filename": row["filename"],
            "page": row["page"],
            "content": row["content"],
            "score": round(score / maximum, 4),
        })
        if len(results) == top_k:
            break
    return results