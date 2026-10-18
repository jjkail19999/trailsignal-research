# TrialSignal Research

A hackathon-ready research-paper discovery prototype for the Nebius Healthcare / Life Sciences challenge.

**Live demo:** [TrialSignal Research on Nebius](https://port8080-kzng6204m1ccsjw.tunnel.applications.uk-south2.nebius.cloud/)

> The live demo is available while its Nebius endpoint is running.

Built with Nebius Token Factory, NVIDIA Nemotron, Tavily, OpenAlex, and Streamlit.

## Why this idea is differentiated

Most paper recommenders optimize for similarity and return an opaque list. TrialSignal Research instead makes every recommendation answer three questions:

1. **How was it found?** A visible discovery trail shows citation, shared-reference, and question-search paths.
2. **Why is it ranked here?** The score is composed of inspectable, deterministic signals rather than an LLM's hidden judgment.
3. **What text supports the explanation?** Nemotron must return an exact quote from the supplied abstract; the application removes quotes it cannot verify.

This is deliberately a **candidate review tool**, not an automatic scientific-quality evaluator.

## Recommended MVP

The winning wedge is **multi-seed evidence trails**: find papers that connect multiple seeds, then explain the connection with verifiable source text. The demo should compare this with a normal keyword search and show a useful bridge paper the keyword baseline missed.

### Inputs

- A research question
- 3–5 seed papers as DOI links, PubMed URLs/PMIDs, OpenAlex IDs, or titles

### Outputs

- Ranked papers not present in the seed collection
- Metadata and source links
- A transparent score breakdown
- Discovery paths back to individual seeds
- Year and multi-seed bridge filters plus CSV export
- A Nemotron relevance explanation with a validated abstract passage
- Optional Tavily web context for the selected result
- A public Method and Evidence Standard that exposes ranking weights, source roles, validation rules, and limitations before a user runs a search

## Architecture

```text
Streamlit UI (Nebius Serverless Endpoint)
        |
        v
Python discovery orchestrator
   |              |                 |
   v              v                 v
OpenAlex       Tavily          Token Factory
metadata +     top-result      Nemotron explanation
citation graph enrichment      + evidence quote
   |
   v
Deterministic hybrid ranker
(question 40%, seed graph 25%, seed text 20%, citations 10%, recency 5%)
```

OpenAlex provides the scholarly graph and reconstructed abstracts. Tavily is purposefully limited to supplementary context on a result the user chooses, reducing latency, cost, and web noise. Token Factory is used for the final interpretive layer, not for identity resolution or numerical scoring.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
streamlit run app.py
```

Or use `make setup`, followed by `make run`. Run the checks with `make check`.

## Hackathon deployment without Docker

The `deploy/endpoint-dry-run.sh` script validates a CPU-only Nebius Serverless Endpoint that starts from `python:3.11-slim` and injects the small application files. This avoids requiring a local container engine or registry during the hackathon. It uses managed HTTPS and platform-generated bearer-token authentication, so it does not consume the project's single public-IP allowance.

Run `make deploy-dry-run` to validate only. It never creates a resource. The current hackathon configuration maps `NEBIUS_API_KEY` and `TAVILY_API_KEY` from separate SecretStash resources through `--env-secret`; their values never appear in source files or shell arguments. `OPENALEX_API_KEY` remains optional.

The discovery and deterministic ranking work without private model/search keys, subject to OpenAlex's shared unauthenticated budget. Add `OPENALEX_API_KEY` for a dedicated API budget, `NEBIUS_API_KEY` for Nemotron explanations, and `TAVILY_API_KEY` for supplementary web context. The default Token Factory model and base URL follow the supplied workshop notebook; change `NEBIUS_MODEL` if the event catalog differs.

## Demo script (three minutes)

1. Enter a narrow research question and three known papers.
2. Resolve the seeds and show the top results.
3. Open a result connected to more than one seed; show its discovery trail and score components.
4. Generate the evidence-checked Nemotron explanation and point to the exact abstract passage.
5. Show the uncertainty statement and optional Tavily sources.
6. Close with: “Keyword search finds words. TrialSignal finds and explains the papers your collection points toward.”

## Concrete alternatives considered

| Idea | Differentiator | Hackathon fit | Main risk |
|---|---|---:|---|
| **Evidence Trail** (recommended) | Multi-seed graph + verified explanations | High | OpenAlex coverage varies |
| Contradiction Scout | Finds papers that challenge seed conclusions | High drama | Reliable contradiction detection is hard from abstracts |
| Methods Transfer Radar | Finds methods used in adjacent diseases | Strong niche | Needs careful taxonomy/evaluation |
| Living Review Delta | Finds papers published after a review's search cutoff | Useful product | Extracting cutoff dates and inclusion criteria adds scope |
| Trial-to-Paper Gap Map | Links active trials to the publication graph | Strategic extension | Less aligned with the core seed-collection brief |

Build **Evidence Trail** first. If time remains, add a “bridge / adjacent / challenging” intent filter; it changes ranking weights without changing the architecture.

## Evaluation plan

Create a 20-candidate pool for one domain and have a knowledgeable reviewer label each result `useful`, `uncertain`, or `not useful`.

- **Primary:** Precision@5 versus OpenAlex question search alone
- **Secondary:** useful novel papers found, seed coverage, explanation quote validity, time-to-first-useful-paper
- **Ablation:** remove graph signals, then remove question match, to show each component's contribution
- **Guardrail:** percentage of explanations whose quoted evidence is an exact abstract substring (target: 100%)

## Deployment plan

1. Build and test the container locally: `docker build -t trialsignal-research .`
2. Push the image to a registry accessible by Nebius.
3. Create a Nebius Serverless **Endpoint** for the long-running interactive Streamlit service. A Job is better for finite batch work; DevLab is for development, not the public demo.
4. Expose port `8080`, pass the environment variables shown in `.env.example`, and keep secrets in the platform's secret/environment configuration rather than the image.
5. Configure a health check for `/` and start with one instance plus scale-to-zero if supported by the event environment.
6. Smoke-test seed resolution, discovery, a Nemotron explanation, and Tavily enrichment from the deployed URL.

For a production evolution, split the UI from a FastAPI backend, cache OpenAlex responses, persist sessions/results, add rate limiting, and evaluate ranking weights on expert judgments.

## Known limitations

- Citation and abstract coverage is incomplete and biased toward indexed work.
- Citation count is a visibility signal, not a quality measure.
- Token overlap is intentionally simple for the hackathon; Token Factory embeddings can replace it after model availability is confirmed.
- An exact supporting quote constrains hallucination but does not prove the explanation is scientifically correct.
- Full-text and paywalled content are outside the MVP.

