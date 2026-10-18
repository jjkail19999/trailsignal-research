from __future__ import annotations

import csv
import io
import os

import streamlit as st
from dotenv import load_dotenv

from core import discover, enrich_with_tavily, explain_with_nemotron


load_dotenv()
st.set_page_config(page_title="TrialSignal Research", page_icon="●", layout="wide", initial_sidebar_state="collapsed")

OPENALEX_INSPIRED_CSS = """
<style>
:root {
  color-scheme: light;
  --ink: #111111;
  --muted: #616161;
  --paper: #fcfcfb;
  --surface: #ffffff;
  --line: #dededb;
  --soft: #f2f2ef;
  --signal: #235347;
  --signal-soft: #e7f2ed;
  --danger: #a33b2f;
  --radius: 13px;
}

html, body, [class*="css"], .stApp {
  font-family: Inter, -apple-system, BlinkMacSystemFont, "Helvetica Neue", Arial, sans-serif;
}
.stApp { background: var(--paper); color: var(--ink); }
[data-testid="stHeader"], [data-testid="stSidebar"], #MainMenu, footer { display: none !important; }
.stMainBlockContainer { max-width: 1240px; padding: 0 2.4rem 5rem; }

h1, h2, h3, h4 { color: var(--ink); letter-spacing: -.04em; }
h2 { font-size: 2.2rem !important; line-height: 1.05 !important; font-weight: 680 !important; }
h3 { font-size: 1.32rem !important; font-weight: 650 !important; }
p, label, [data-testid="stCaptionContainer"] { color: var(--muted); }

.ts-nav {
  min-height: 72px; display: flex; align-items: center; justify-content: space-between;
  border-bottom: 1px solid var(--line); margin: 0 -2.4rem 0; padding: 0 2.4rem;
}
.ts-nav-left, .ts-nav-right, .ts-brand { display: flex; align-items: center; }
.ts-nav-left { gap: 3rem; }.ts-nav-right { gap: 1.25rem; }
.ts-brand { gap: .68rem; color: var(--ink); font-size: 1.35rem; font-weight: 760; letter-spacing: -.045em; }
.ts-logo { position: relative; width: 25px; height: 25px; }
.ts-logo i { position: absolute; width: 10px; height: 10px; border-radius: 50%; background: var(--ink); }
.ts-logo i:nth-child(1) { left: 7px; top: 0; }.ts-logo i:nth-child(2) { left: 1px; top: 11px; }.ts-logo i:nth-child(3) { right: 1px; top: 11px; }
.ts-nav-links { display: flex; gap: 1.8rem; color: #3f3f3f; font-size: .89rem; }
.ts-nav-links a { color: #3f3f3f; text-decoration: none; }
.ts-nav-links a:first-child { color: var(--ink); font-weight: 650; }
.ts-nav-links a:hover { color: var(--signal); }
.ts-built { font-size: .77rem; color: var(--muted); }
.ts-live { display: inline-flex; align-items: center; gap: .45rem; color: var(--ink); font-size: .78rem; font-weight: 630; }
.ts-live::before { content: ""; width: 7px; height: 7px; border-radius: 50%; background: #2c8b55; }

.ts-hero { padding: clamp(4.8rem, 10vw, 8.4rem) 0 3.2rem; max-width: 930px; }
.ts-eyebrow { color: var(--signal); font-size: .77rem; font-weight: 750; letter-spacing: .11em; text-transform: uppercase; margin-bottom: 1.4rem; }
.ts-hero h1 { color: var(--ink); font-size: clamp(3.8rem, 7vw, 6.5rem); line-height: .93; font-weight: 700; letter-spacing: -.068em; margin: 0 0 1.8rem; }
.ts-hero h1 em { color: var(--signal); font-style: normal; }
.ts-hero p { max-width: 700px; font-size: clamp(1.1rem, 1.7vw, 1.35rem); line-height: 1.52; margin: 0; color: #555; }

[data-testid="stVerticalBlockBorderWrapper"] {
  background: var(--surface); border: 1px solid #242424 !important;
  border-radius: var(--radius) !important; box-shadow: none !important;
}
[data-testid="stVerticalBlockBorderWrapper"] > div { padding: .25rem .45rem; }
.ts-composer-label { color: var(--ink); font-size: .77rem; font-weight: 700; letter-spacing: .055em; text-transform: uppercase; margin: .1rem 0 .45rem; }
.ts-composer-help { color: var(--muted); font-size: .82rem; margin-bottom: .5rem; }
.stTextArea [data-baseweb="textarea"], .stTextArea [data-baseweb="base-input"] {
  background: #ffffff !important; color: #111111 !important;
}
.stTextArea textarea {
  background: #ffffff !important; border: 0 !important; border-radius: 0 !important;
  color: #111111 !important; -webkit-text-fill-color: #111111 !important; caret-color: #111111 !important;
  font-size: 1.03rem !important; line-height: 1.48 !important;
  padding: .55rem .15rem !important; box-shadow: none !important;
}
.stTextArea textarea::placeholder { color: #777777 !important; -webkit-text-fill-color: #777777 !important; opacity: 1 !important; }
.stTextArea textarea:focus { box-shadow: none !important; }
[data-testid="stExpander"] { border: 0 !important; border-top: 1px solid var(--line) !important; border-radius: 0 !important; background: transparent !important; }
[data-testid="stExpander"] summary { min-height: 44px; color: var(--ink); font-weight: 620; }
.stButton > button, .stDownloadButton > button {
  min-height: 44px; border-radius: 9px; font-weight: 650; border: 1px solid var(--ink);
  background: var(--surface); color: var(--ink); transition: background .14s ease, color .14s ease, transform .14s ease;
}
.stButton > button[kind="primary"] { background: var(--ink) !important; color: #fff !important; }
.stButton > button[kind="primary"] p, .stButton > button[kind="primary"] span { color: #fff !important; }
.stButton > button:hover, .stDownloadButton > button:hover { border-color: var(--signal); color: var(--signal); transform: translateY(-1px); }
.stButton > button[kind="primary"]:hover { background: var(--signal); color: #fff; }
.stButton > button:focus-visible, .stDownloadButton > button:focus-visible { outline: 3px solid rgba(35,83,71,.24); outline-offset: 2px; }

.ts-trust-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0; margin: 3.6rem 0 5.2rem; border-top: 1px solid var(--line); border-bottom: 1px solid var(--line); }
.ts-trust-item { padding: 1.45rem 1.5rem 1.45rem 0; }
.ts-trust-item + .ts-trust-item { border-left: 1px solid var(--line); padding-left: 1.5rem; }
.ts-trust-item strong { display: block; color: var(--ink); font-size: .9rem; margin-bottom: .28rem; }
.ts-trust-item span { display: block; color: var(--muted); font-size: .78rem; line-height: 1.4; }

.ts-section { scroll-margin-top: 24px; margin: 5.4rem 0 1.5rem; }
.ts-section h2 { margin: 0 0 .7rem; }
.ts-section > p { max-width: 760px; line-height: 1.55; margin: 0; }
.ts-method-grid { display: grid; grid-template-columns: repeat(3, 1fr); border-top: 1px solid var(--ink); border-bottom: 1px solid var(--line); }
.ts-method-card { padding: 1.5rem 1.4rem 1.55rem 0; }
.ts-method-card + .ts-method-card { border-left: 1px solid var(--line); padding-left: 1.4rem; }
.ts-step { color: var(--signal); font-size: .72rem; font-weight: 760; letter-spacing: .09em; text-transform: uppercase; }
.ts-method-card h3 { margin: .65rem 0 .55rem; font-size: 1.08rem !important; letter-spacing: -.025em; }
.ts-method-card p { margin: 0; font-size: .84rem; line-height: 1.5; }
.ts-formula { margin-top: 1.2rem; padding: .95rem 1.1rem; background: var(--soft); border-radius: 9px; color: #383838; font-size: .8rem; line-height: 1.55; }
.ts-formula strong { color: var(--ink); }
.ts-evidence-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
.ts-evidence-card { background: var(--surface); border: 1px solid var(--line); border-radius: 11px; padding: 1.2rem; }
.ts-evidence-card strong { display: block; color: var(--ink); font-size: .9rem; margin-bottom: .35rem; }
.ts-evidence-card p { margin: 0; font-size: .8rem; line-height: 1.5; }
.ts-source-chip { display: inline-block; margin-top: .7rem; padding: .28rem .52rem; border-radius: 999px; background: var(--signal-soft); color: var(--signal); font-size: .68rem; font-weight: 700; }
.ts-proof-list { border-top: 1px solid var(--line); margin-top: .7rem; }
.ts-proof-row { display: grid; grid-template-columns: 1.25fr .8fr; gap: 1rem; padding: .78rem 0; border-bottom: 1px solid var(--line); font-size: .78rem; }
.ts-proof-row span:first-child { color: var(--ink); font-weight: 630; }.ts-proof-row span:last-child { color: var(--muted); }

.ts-results-head { display: flex; justify-content: space-between; align-items: end; gap: 2rem; margin: 5.5rem 0 1.6rem; }
.ts-results-head h2 { margin: 0 0 .45rem; }.ts-results-head p { margin: 0; max-width: 700px; line-height: 1.5; }
.ts-results-tag { flex: 0 0 auto; color: var(--signal); background: var(--signal-soft); border-radius: 999px; padding: .48rem .8rem; font-size: .76rem; font-weight: 680; }

[data-testid="stMetric"] { background: transparent; border-top: 1px solid var(--ink); padding: 1rem 0 .75rem; }
[data-testid="stMetricLabel"] { color: var(--muted); font-size: .78rem; }
[data-testid="stMetricValue"] { color: var(--ink); font-weight: 680; letter-spacing: -.04em; }
[data-testid="stDataFrame"] { border: 1px solid var(--line); border-radius: 10px; overflow: hidden; }
.stNumberInput input, [data-baseweb="select"] > div { background: var(--surface) !important; color: var(--ink) !important; border-color: var(--line) !important; }

.ts-detail-kicker { color: var(--signal); font-size: .75rem; font-weight: 720; text-transform: uppercase; letter-spacing: .09em; margin-bottom: .5rem; }
.ts-footer { margin-top: 5rem; border-top: 1px solid var(--line); padding: 1.4rem 0; display: flex; justify-content: space-between; gap: 2rem; color: var(--muted); font-size: .75rem; line-height: 1.5; }
.ts-footer strong { color: var(--ink); }

[data-testid="stAlert"] { border-radius: 9px; }
@media (max-width: 780px) {
  .stMainBlockContainer { padding: 0 1.1rem 3rem; }
  .ts-nav { margin: 0 -1.1rem; padding: 0 1.1rem; }.ts-nav-links, .ts-built { display: none; }
  .ts-hero { padding-top: 4.2rem; }.ts-hero h1 { font-size: 3.7rem; }
  .ts-trust-row { grid-template-columns: 1fr; }.ts-trust-item + .ts-trust-item { border-left: 0; border-top: 1px solid var(--line); padding-left: 0; }
  .ts-method-grid, .ts-evidence-grid { grid-template-columns: 1fr; }
  .ts-method-card + .ts-method-card { border-left: 0; border-top: 1px solid var(--line); padding-left: 0; }
  .ts-results-head { display: block; }.ts-results-tag { display: inline-block; margin-top: 1rem; }
  .ts-footer { display: block; }
}
@media (prefers-reduced-motion: reduce) { *, *::before, *::after { transition: none !important; animation: none !important; scroll-behavior: auto !important; } }
</style>
"""
st.markdown(OPENALEX_INSPIRED_CSS, unsafe_allow_html=True)


@st.cache_data(ttl=3600, show_spinner=False)
def cached_discover(question: str, seeds: tuple[str, ...]):
    return discover(question, list(seeds))


@st.cache_data(ttl=3600, show_spinner=False)
def cached_evidence_check(question: str, paper: dict):
    web_sources = enrich_with_tavily(question, paper)
    explanation = explain_with_nemotron(question, paper, web_sources)
    return explanation, web_sources


def csv_export(rows):
    stream = io.StringIO()
    fields = ["rank", "score", "title", "year", "authors", "doi", "pmid", "source_url", "discovery_paths"]
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    for rank, row in enumerate(rows, 1):
        writer.writerow({
            "rank": rank, "score": row["score"], "title": row["title"], "year": row["year"],
            "authors": "; ".join(row["authors"]), "doi": row["doi"], "pmid": row["pmid"],
            "source_url": row["source_url"], "discovery_paths": "; ".join(row["discovery_paths"]),
        })
    return stream.getvalue()


def friendly_error(exc: Exception, action: str) -> str:
    detail = str(exc).lower()
    if "429" in detail or "too many requests" in detail:
        return "OpenAlex is temporarily rate-limiting discovery. TrialSignal retried automatically; wait one minute and try again. Adding a free OpenAlex API key will make the public demo more reliable."
    if "timed out" in detail or "timeout" in detail:
        return f"{action} took longer than expected. Check your connection, then try again."
    return f"{action} couldn’t finish. Try again; if the problem continues, check the service status."


st.markdown("""
<nav class="ts-nav" aria-label="Primary navigation">
  <div class="ts-nav-left">
    <div class="ts-brand"><span class="ts-logo" aria-hidden="true"><i></i><i></i><i></i></span>TrialSignal</div>
    <div class="ts-nav-links"><a href="#discover">Discover</a><a href="#method">Method</a><a href="#evidence">Evidence</a><a href="#about">About</a></div>
  </div>
  <div class="ts-nav-right"><span class="ts-built">Powered by Nebius + Tavily</span><span class="ts-live">Live demo</span></div>
</nav>
<section class="ts-hero" id="discover">
  <div class="ts-eyebrow">Research paper discovery</div>
  <h1>Find the research<br>you’re <em>missing.</em></h1>
  <p>Start with the papers you trust. TrialSignal follows their citation network, finds meaningful bridges, and shows why every new paper belongs.</p>
</section>
""", unsafe_allow_html=True)

with st.container(border=True):
    st.markdown('<div class="ts-composer-label">Research question</div><div class="ts-composer-help">Ask a focused question about the evidence you want to discover.</div>', unsafe_allow_html=True)
    question = st.text_area(
        "Research question",
        value="Which single-cell methods help characterize melanoma immune cells and treatment response?",
        height=96,
        placeholder="What are you trying to understand?",
        label_visibility="collapsed",
    )
    default_seeds = "https://doi.org/10.1126/science.aad0501\nhttps://doi.org/10.1016/j.cell.2018.10.038\nhttps://doi.org/10.1038/s41586-021-03704-y"
    with st.expander("Seed collection · add DOI, PMID, OpenAlex ID, or title", expanded=False):
        seeds_text = st.text_area(
            "Seed papers",
            value=default_seeds,
            height=132,
            placeholder="One paper per line",
            label_visibility="collapsed",
        )
    action_col, reset_col = st.columns([4, 1])
    discover_clicked = action_col.button("Discover papers", type="primary", width="stretch")
    if reset_col.button("Reset", width="stretch"):
        for key in ("question", "seeds", "candidates", "analysis", "evidence_checks_used"):
            st.session_state.pop(key, None)
        st.rerun()

st.markdown("""
<div class="ts-trust-row">
  <div class="ts-trust-item"><strong>Traceable by design</strong><span>Every recommendation includes the citation path that surfaced it.</span></div>
  <div class="ts-trust-item"><strong>Transparent ranking</strong><span>Inspectable signals rank the list before AI explains the evidence.</span></div>
  <div class="ts-trust-item"><strong>Current context</strong><span>Tavily and Nemotron enrich only the papers you choose to review.</span></div>
</div>
""", unsafe_allow_html=True)

if discover_clicked:
    if not question.strip():
        st.warning("Add a research question to begin.")
    elif not any(line.strip() for line in seeds_text.splitlines()):
        st.warning("Add at least one seed paper to begin.")
    else:
        try:
            with st.spinner("Following citations and comparing the evidence network…"):
                seed_values = tuple(line.strip() for line in seeds_text.splitlines() if line.strip())
                seeds, candidates = cached_discover(question.strip(), seed_values)
            st.session_state.update(question=question, seeds=seeds, candidates=candidates)
        except Exception as exc:
            st.error(friendly_error(exc, "Discovery"))

seeds = st.session_state.get("seeds", [])
candidates = st.session_state.get("candidates", [])

if seeds:
    if candidates:
        st.success(f"Discovery complete — {len(candidates)} candidate papers found. Results are shown below.")
    with st.expander(f"Resolved seed collection · {len(seeds)} papers"):
        for seed in seeds:
            st.markdown(f"- [{seed.title}]({seed.source_url}) · {seed.year or 'Year unavailable'}")

if candidates:
    bridge_count = sum(row["signals"]["seed_connections"] >= 2 for row in candidates)
    st.markdown("""
    <div class="ts-results-head"><div><h2>Ranked discoveries</h2><p>A review queue built from citation paths, semantic overlap, recency, and influence—not an AI-generated quality score.</p></div><span class="ts-results-tag">Evidence trail ready</span></div>
    """, unsafe_allow_html=True)
    metric_a, metric_b, metric_c = st.columns(3)
    metric_a.metric("Candidates", len(candidates))
    metric_b.metric("Multi-seed bridges", bridge_count)
    metric_c.metric("Highest review score", candidates[0]["score"] if candidates else "—")

    with st.container(border=True):
        st.markdown('<div class="ts-composer-label">Refine results</div>', unsafe_allow_html=True)
        filter_a, filter_b, filter_c = st.columns(3)
        top_n = filter_a.slider("Results to review", 5, 25, 10)
        min_year = filter_b.number_input("Published since", min_value=1900, max_value=2100, value=2015)
        bridge_only = filter_c.toggle("Multi-seed bridges only", value=False)

    filtered = [row for row in candidates if (row["year"] or 0) >= min_year and (not bridge_only or row["signals"]["seed_connections"] >= 2)]
    shown = filtered[:top_n]
    if not shown:
        st.info("No papers match these filters. Choose an earlier year or include single-seed connections.")
        st.stop()

    st.dataframe(
        [{"Score": row["score"], "Year": row["year"], "Paper": row["title"], "Seed links": row["signals"]["seed_connections"], "Citations": row["cited_by_count"]} for row in shown],
        hide_index=True,
        width="stretch",
        column_config={
            "Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%.1f"),
            "Paper": st.column_config.TextColumn("Paper", width="large"),
        },
    )
    export_col, select_col = st.columns([1, 2])
    export_col.download_button("Export CSV", data=csv_export(shown), file_name="trailsignal-ranked-papers.csv", mime="text/csv", width="stretch")
    selected_title = select_col.selectbox("Paper to inspect", [row["title"] for row in shown])
    selected = next(row for row in shown if row["title"] == selected_title)

    st.markdown('<div class="ts-results-head"><div><h2>Paper detail</h2><p>Inspect the source record, ranking signals, and discovery path before asking AI for an explanation.</p></div></div>', unsafe_allow_html=True)
    with st.container(border=True):
        detail_col, signal_col = st.columns([1.75, 1])
        with detail_col:
            st.markdown('<div class="ts-detail-kicker">Recommended paper</div>', unsafe_allow_html=True)
            st.markdown(f"### [{selected['title']}]({selected['source_url']})")
            metadata = " · ".join(item for item in [str(selected["year"]) if selected["year"] else None, ", ".join(selected["authors"][:3]) or None] if item)
            st.caption(metadata or "Publication metadata unavailable")
            st.write(selected["abstract"] or "No abstract is available from OpenAlex for this paper.")
        with signal_col:
            st.metric("Review score", selected["score"])
            st.caption("Question match"); st.progress(float(selected["signals"]["question_match"]))
            st.caption("Seed-text similarity"); st.progress(float(selected["signals"]["seed_similarity"]))
            st.caption("Citation signal"); st.progress(float(selected["signals"]["citation_signal"]))
            st.caption(f"Connected through {selected['signals']['seed_connections']} seed paths")
        st.markdown("#### Why this paper surfaced")
        for path in selected["discovery_paths"] or ["Question search match"]:
            st.markdown(f"- {path}")
        st.markdown("#### Evidence provenance")
        identifier = selected.get("doi") or selected.get("pmid") or selected.get("openalex_id")
        abstract_status = "Available for grounding" if selected.get("abstract") else "Not available"
        st.markdown(
            f"""
            <div class="ts-proof-list">
              <div class="ts-proof-row"><span>Publication identity</span><span>{identifier}</span></div>
              <div class="ts-proof-row"><span>Abstract evidence</span><span>{abstract_status}</span></div>
              <div class="ts-proof-row"><span>Ranking process</span><span>Deterministic · no LLM score</span></div>
              <div class="ts-proof-row"><span>Discovery paths retained</span><span>{len(selected['discovery_paths'])}</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        explain_clicked = st.button("Check relevance with Nemotron + Tavily", type="primary", width="stretch")

    if explain_clicked:
        checks_used = st.session_state.get("evidence_checks_used", 0)
        if checks_used >= 3:
            st.warning("This demo session has used its three evidence checks. Start a new browser session to continue.")
        else:
            try:
                st.session_state["evidence_checks_used"] = checks_used + 1
                with st.spinner("Reading the abstract and checking supplementary sources…"):
                    explanation, web_sources = cached_evidence_check(st.session_state["question"], selected)
                st.session_state["analysis"] = (selected["openalex_id"], explanation, web_sources)
            except Exception as exc:
                st.error(friendly_error(exc, "The evidence check"))

    analysis = st.session_state.get("analysis")
    if analysis and analysis[0] == selected["openalex_id"]:
        _, explanation, web_sources = analysis
        st.markdown('<div class="ts-results-head"><div><h2>Evidence check</h2><p>A model-assisted explanation grounded in the available abstract and supplementary sources.</p></div></div>', unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("#### Relevance")
            st.write(explanation.get("relevance", "No relevance explanation was returned."))
            if explanation.get("evidence_quote"):
                st.success(f'Abstract evidence: “{explanation["evidence_quote"]}”')
                st.caption("Verified: this passage is an exact substring of the retrieved abstract.")
            elif selected.get("abstract"):
                st.info("No verified quotation was returned. The explanation is shown without a supporting passage.")
            st.markdown("#### Limits and uncertainty")
            st.warning(explanation.get("uncertainty", "No uncertainty statement was returned."))
            if explanation.get("web_context"):
                st.info(explanation["web_context"])
            if web_sources:
                st.markdown("#### Supplementary sources")
                for source in web_sources:
                    st.markdown(f'- [{source["title"]}]({source["url"]})')

st.markdown("""
<section class="ts-section" id="method">
  <div class="ts-eyebrow">Method</div>
  <h2>A graph first. AI second.</h2>
  <p>The ranking is reproducible and inspectable. Language models explain selected results, but never invent the numerical score.</p>
</section>
<div class="ts-method-grid">
  <article class="ts-method-card"><span class="ts-step">01 · Retrieve</span><h3>Follow the seed network</h3><p>Resolve each seed in OpenAlex, collect papers that cite it, gather its references, and add direct question-search matches.</p></article>
  <article class="ts-method-card"><span class="ts-step">02 · Rank</span><h3>Combine visible signals</h3><p>Score every candidate using question overlap, connections to the seed collection, seed-text overlap, citation visibility, and recency.</p></article>
  <article class="ts-method-card"><span class="ts-step">03 · Verify</span><h3>Ground the explanation</h3><p>Nemotron receives only retrieved metadata and context. Any supporting quotation must exactly match the OpenAlex abstract or it is removed.</p></article>
</div>
<div class="ts-formula"><strong>Review score</strong> = 40% question match + 25% seed-network connections + 20% seed-text similarity + 10% citation signal + 5% recency. It prioritizes review; it does not measure scientific quality.</div>

<section class="ts-section" id="evidence">
  <div class="ts-eyebrow">Evidence standard</div>
  <h2>Every claim keeps its receipt.</h2>
  <p>TrialSignal separates publication evidence from supplementary web context, and shows uncertainty rather than filling gaps.</p>
</section>
<div class="ts-evidence-grid">
  <article class="ts-evidence-card"><strong>Publication record</strong><p>Title, authors, year, identifiers, abstract, citations, and reference links come from the OpenAlex scholarly graph.</p><span class="ts-source-chip">Primary discovery source</span></article>
  <article class="ts-evidence-card"><strong>Discovery trail</strong><p>Each recommendation preserves the specific seed citation, shared reference, or question-search route that surfaced it.</p><span class="ts-source-chip">Deterministic provenance</span></article>
  <article class="ts-evidence-card"><strong>Model explanation</strong><p>Nemotron explains relevance from the supplied record. A quoted passage is displayed only after exact-string validation.</p><span class="ts-source-chip">Grounded interpretation</span></article>
  <article class="ts-evidence-card"><strong>Current web context</strong><p>Tavily checks a small set of trusted scientific domains for context. Web results remain clearly separate from paper evidence.</p><span class="ts-source-chip">Supplementary only</span></article>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="ts-footer" id="about"><span><strong>TrialSignal Research</strong><br>Open literature discovery with an inspectable trail.</span><span>Prototype only—not medical advice. Ranking supports review, not clinical or scientific conclusions. Always read the original publication.</span></div>
""", unsafe_allow_html=True)
