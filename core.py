from __future__ import annotations

import json
import math
import os
import re
import time
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import date
from typing import Any, Iterable
from urllib.parse import quote

import requests


OPENALEX_API = "https://api.openalex.org"
TOKEN_RE = re.compile(r"[a-z0-9]+")
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "how", "in", "is", "it", "of", "on", "or", "that", "the", "their",
    "this", "to", "using", "was", "were", "what", "which", "with",
}


@dataclass
class Paper:
    openalex_id: str
    title: str
    year: int | None
    authors: list[str]
    doi: str | None
    pmid: str | None
    cited_by_count: int
    work_type: str
    abstract: str
    referenced_works: list[str]
    source_url: str


def _tokens(text: str) -> set[str]:
    return {t for t in TOKEN_RE.findall(text.lower()) if len(t) > 2 and t not in STOPWORDS}


def _abstract_from_inverted_index(index: dict[str, list[int]] | None) -> str:
    if not index:
        return ""
    positioned = [(position, word) for word, positions in index.items() for position in positions]
    return " ".join(word for _, word in sorted(positioned))


def evidence_quote_is_exact(quote_text: str, abstract: str) -> bool:
    """Return true only when a non-empty model quote occurs verbatim in the abstract."""
    cleaned = quote_text.strip().strip('"“”')
    return bool(cleaned and abstract and cleaned.casefold() in abstract.casefold())


def _paper(work: dict[str, Any]) -> Paper:
    ids = work.get("ids") or {}
    primary = work.get("primary_location") or {}
    return Paper(
        openalex_id=work.get("id", ""),
        title=work.get("display_name") or "Untitled",
        year=work.get("publication_year"),
        authors=[
            a.get("author", {}).get("display_name", "")
            for a in (work.get("authorships") or [])[:8]
            if a.get("author", {}).get("display_name")
        ],
        doi=ids.get("doi"),
        pmid=ids.get("pmid"),
        cited_by_count=int(work.get("cited_by_count") or 0),
        work_type=work.get("type") or "unknown",
        abstract=_abstract_from_inverted_index(work.get("abstract_inverted_index")),
        referenced_works=work.get("referenced_works") or [],
        source_url=(primary.get("landing_page_url") or ids.get("doi") or work.get("id") or ""),
    )


class OpenAlexClient:
    def __init__(self, mailto: str | None = None, timeout: int = 25):
        self.timeout = timeout
        self._last_request_at = 0.0
        self.params = {"mailto": mailto} if mailto else {}
        if os.getenv("OPENALEX_API_KEY"):
            self.params["api_key"] = os.environ["OPENALEX_API_KEY"]
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "TrialSignal-Research/0.1"})

    def _get(self, path: str, **params: Any) -> dict[str, Any]:
        response = None
        for attempt in range(4):
            # Keep sequential requests below the anonymous per-second ceiling.
            elapsed = time.monotonic() - self._last_request_at
            if elapsed < 0.15:
                time.sleep(0.15 - elapsed)
            response = self.session.get(
                f"{OPENALEX_API}{path}",
                params={**self.params, **params},
                timeout=self.timeout,
            )
            self._last_request_at = time.monotonic()
            if response.status_code not in {429, 500, 502, 503, 504}:
                response.raise_for_status()
                return response.json()
            if attempt < 3:
                retry_after = response.headers.get("Retry-After", "")
                try:
                    wait_seconds = float(retry_after)
                except ValueError:
                    wait_seconds = 0.75 * (2 ** attempt)
                time.sleep(min(4.0, max(0.5, wait_seconds)))
        assert response is not None
        response.raise_for_status()
        return response.json()

    def resolve(self, value: str) -> Paper:
        raw = value.strip()
        if not raw:
            raise ValueError("Empty seed")
        if "openalex.org/W" in raw or re.fullmatch(r"W\d+", raw, re.I):
            identifier = raw.rsplit("/", 1)[-1]
            return _paper(self._get(f"/works/{identifier}"))
        doi_match = re.search(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", raw, re.I)
        if doi_match:
            return _paper(self._get(f"/works/https://doi.org/{quote(doi_match.group(0), safe='/')}"))
        pmid_match = re.search(r"(?:pubmed/|pmid:?\s*)(\d{5,10})", raw, re.I)
        if not pmid_match and re.fullmatch(r"\d{5,10}", raw):
            pmid_match = re.match(r"(\d{5,10})", raw)
        if pmid_match:
            data = self._get("/works", filter=f"pmid:{pmid_match.group(1)}", per_page=1)
            if data.get("results"):
                return _paper(data["results"][0])
        data = self._get("/works", search=raw, per_page=1)
        if not data.get("results"):
            raise ValueError(f"No OpenAlex match for seed: {raw}")
        return _paper(data["results"][0])

    def works_by_ids(self, ids: Iterable[str], limit: int = 100) -> list[Paper]:
        short_ids = [x.rsplit("/", 1)[-1] for x in ids if x]
        papers: list[Paper] = []
        for start in range(0, min(len(short_ids), limit), 50):
            batch = short_ids[start : start + 50]
            data = self._get("/works", filter=f"openalex_id:{'|'.join(batch)}", per_page=50)
            papers.extend(_paper(w) for w in data.get("results", []))
        return papers

    def citing(self, openalex_id: str, limit: int = 40) -> list[Paper]:
        short_id = openalex_id.rsplit("/", 1)[-1]
        data = self._get(
            "/works",
            filter=f"cites:{short_id},has_abstract:true",
            sort="cited_by_count:desc",
            per_page=min(limit, 100),
        )
        return [_paper(w) for w in data.get("results", [])]

    def search(self, question: str, limit: int = 40) -> list[Paper]:
        # OpenAlex treats ? and * as wildcard operators in stemmed search.
        safe_question = question.replace("?", " ").replace("*", " ").strip()
        data = self._get(
            "/works",
            search=safe_question,
            filter="has_abstract:true",
            per_page=min(limit, 100),
        )
        return [_paper(w) for w in data.get("results", [])]


def rank_candidates(
    question: str,
    seeds: list[Paper],
    candidates: Iterable[Paper],
    paths: dict[str, set[str]],
    shared_reference_count: Counter[str],
) -> list[dict[str, Any]]:
    """Score candidate papers with inspectable, non-LLM signals."""
    seed_text = " ".join(f"{s.title} {s.abstract}" for s in seeds)
    q_tokens, seed_tokens = _tokens(question), _tokens(seed_text)
    current_year = date.today().year
    scored: list[dict[str, Any]] = []
    for paper in candidates:
        text_tokens = _tokens(f"{paper.title} {paper.abstract}")
        q_overlap = len(text_tokens & q_tokens) / max(1, len(q_tokens))
        seed_overlap = len(text_tokens & seed_tokens) / max(1, min(80, len(seed_tokens)))
        seed_connections = len(paths[paper.openalex_id])
        shared_count = shared_reference_count[paper.openalex_id]
        if shared_count:
            seed_connections += shared_count
            paths[paper.openalex_id].add(f"Referenced by {shared_count} seed paper(s)")
        citation_signal = min(1.0, math.log1p(paper.cited_by_count) / math.log(1001))
        recency = max(0.0, 1.0 - max(0, current_year - (paper.year or 1990)) / 20)
        score = 100 * (
            0.40 * q_overlap
            + 0.25 * min(1.0, seed_connections / max(2, len(seeds)))
            + 0.20 * seed_overlap
            + 0.10 * citation_signal
            + 0.05 * recency
        )
        scored.append({
            **asdict(paper),
            "score": round(score, 1),
            "signals": {
                "question_match": round(q_overlap, 3),
                "seed_connections": seed_connections,
                "seed_similarity": round(seed_overlap, 3),
                "citation_signal": round(citation_signal, 3),
                "recency": round(recency, 3),
            },
            "discovery_paths": sorted(paths[paper.openalex_id])[:6],
        })
    scored.sort(key=lambda row: row["score"], reverse=True)
    return scored


def discover(question: str, seed_values: list[str], max_candidates: int = 120) -> tuple[list[Paper], list[dict[str, Any]]]:
    client = OpenAlexClient(os.getenv("OPENALEX_MAILTO"))
    resolved = [client.resolve(value) for value in seed_values if value.strip()]
    seeds = list({seed.openalex_id: seed for seed in resolved}.values())
    if not seeds:
        raise ValueError("Add at least one seed paper.")

    seed_ids = {s.openalex_id for s in seeds}
    candidate_map: dict[str, Paper] = {}
    paths: dict[str, set[str]] = defaultdict(set)
    shared_reference_count: Counter[str] = Counter()

    all_references: list[str] = []
    retrieval_errors: list[Exception] = []
    for seed in seeds:
        for ref in seed.referenced_works:
            if ref not in seed_ids:
                all_references.append(ref)
                shared_reference_count[ref] += 1
                paths[ref].add(f"Referenced by {seed.title[:60]}")
        try:
            citing_papers = client.citing(seed.openalex_id, limit=30)
        except requests.RequestException as exc:
            retrieval_errors.append(exc)
            citing_papers = []
        for paper in citing_papers:
            if paper.openalex_id not in seed_ids:
                candidate_map[paper.openalex_id] = paper
                paths[paper.openalex_id].add(f"Cites {seed.title[:60]}")

    frequent_refs = [paper_id for paper_id, _ in shared_reference_count.most_common(80)]
    try:
        reference_papers = client.works_by_ids(frequent_refs, limit=80)
    except requests.RequestException as exc:
        retrieval_errors.append(exc)
        reference_papers = []
    for paper in reference_papers:
        candidate_map[paper.openalex_id] = paper

    try:
        question_papers = client.search(question, limit=40)
    except requests.RequestException as exc:
        retrieval_errors.append(exc)
        question_papers = []
    for paper in question_papers:
        if paper.openalex_id not in seed_ids:
            candidate_map[paper.openalex_id] = paper
            paths[paper.openalex_id].add("Question search match")

    publication_types = {"article", "review", "preprint"}
    eligible = [paper for paper in candidate_map.values() if paper.work_type in publication_types]
    if not eligible and retrieval_errors:
        raise retrieval_errors[0]
    scored = rank_candidates(question, seeds, eligible, paths, shared_reference_count)
    return seeds, scored[:max_candidates]


def enrich_with_tavily(question: str, paper: dict[str, Any]) -> list[dict[str, str]]:
    key = os.getenv("TAVILY_API_KEY")
    if not key:
        return []
    from tavily import TavilyClient

    query = f'"{paper["title"]}" {question}'
    response = TavilyClient(api_key=key).search(
        query=query,
        search_depth="advanced",
        max_results=3,
        include_domains=["pubmed.ncbi.nlm.nih.gov", "doi.org", "nature.com", "science.org", "cell.com"],
    )
    return [
        {"title": r.get("title", ""), "url": r.get("url", ""), "content": r.get("content", "")[:1200]}
        for r in response.get("results", [])
    ]


def explain_with_nemotron(question: str, paper: dict[str, Any], web_sources: list[dict[str, str]]) -> dict[str, Any]:
    key = os.getenv("NEBIUS_API_KEY")
    if not key:
        return {
            "relevance": "Add NEBIUS_API_KEY for a model-generated explanation.",
            "evidence_quote": "",
            "uncertainty": "Nemotron explanation unavailable; deterministic ranking remains usable.",
            "web_context": "",
            "evidence_validated": False,
        }
    from openai import OpenAI

    abstract = paper.get("abstract", "")
    payload = {
        "research_question": question,
        "candidate": {k: paper.get(k) for k in ("title", "year", "authors", "doi", "pmid", "abstract")},
        "retrieval_signals": paper.get("signals"),
        "discovery_paths": paper.get("discovery_paths"),
        "web_sources": web_sources,
    }
    client = OpenAI(
        base_url=os.getenv("NEBIUS_BASE_URL", "https://api.tokenfactory.nebius.com/v1/"),
        api_key=key,
        timeout=60,
    )
    response = client.chat.completions.create(
        model=os.getenv("NEBIUS_MODEL", "nvidia/Nemotron-3_5-Lightning"),
        temperature=0.1,
        max_tokens=700,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "You assess research-paper relevance. Use only supplied data. Return JSON with keys "
                    "relevance, evidence_quote, uncertainty, web_context. evidence_quote must be a short exact "
                    "substring of the supplied abstract. Do not infer study outcomes beyond the abstract. If evidence "
                    "is insufficient, say so. Web context is supplementary and must not replace paper evidence."
                ),
            },
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
    )
    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.I)
    result = json.loads(raw)
    quote_text = str(result.get("evidence_quote", "")).strip().strip('"')
    valid = evidence_quote_is_exact(quote_text, abstract)
    if not valid:
        result["evidence_quote"] = ""
        result["uncertainty"] = (str(result.get("uncertainty", "")) + " Evidence quote was removed because it could not be verified.").strip()
    result["evidence_validated"] = valid
    return result
