# Evaluation

The baseline embeds eight held-out questions and searches a persisted index of five official FastAPI articles. A separate synthetic fixture drives the ticket demo. The report records the exact embedding revision, document hashes, expected IDs, rankings and elapsed time for every query. The diversity experiment takes the first unique documents from nine dense results. Both variants use the same candidate retrieval and latency measurement.

| Ranking | Recall@3 | Precision@3 | MRR |
|---|---:|---:|---:|
| Dense chunk ranking | 1.00 | 0.333 | 1.00 |
| First distinct documents | 1.00 | 0.333 | 1.00 |

All eight requests completed. Median shared candidate-retrieval time was 22.035 ms in this run, after indexing warmed the encoder. There is one expected document per question, so unique relevant hits divided by three is at most one third. This document-level labeling does not establish passage-level relevance. Eight timings are too few for this runner to publish p95. See [raw results](retrieval-results.json).

Run `python -m scripts.operator evaluate` against the running API to store a new result. For a fresh standalone experiment, stop the API and run `python -m scripts.benchmark` from the repository root. It fetches current upstream content; revisions can change between runs.

The [behavior cases](../data/evaluation/behavior.json) specify desired generation behavior. Use a configured model and reviewer to assess scope, conflicting sources, version applicability, grounded actions and missing diagnostics. The [live check](../scripts/live_check.py) records observed citation membership, sufficiency, source titles, generation usage and persisted review for two synthetic tickets. Automated synthetic decisions exercise persistence. Independent human usefulness and semantic faithfulness need real reviewers. Ragas and paid judge calls are deferred. No estimated cost is reported without model pricing.

## Local model and abstention results

The release check used Qwen2.5-1.5B-Instruct (Q4_K_M) on a Windows CPU through llama.cpp. For a POST returning 422, the model suggested checking the Pydantic request model and selected a supporting passage from the official Request body guide. A simulated engineer approval was persisted. Investigation time was 109.7 seconds, including first-use work. A subsequent gardening ticket fell below the calibrated cutoff, made zero model calls and persisted an escalation in the review workflow. These two timings cannot establish throughput or an SLA. [Live responses, citations and usage](live-results.json)

The corpus-specific cutoff was 0.2782 cosine similarity for this encoder and corpus revision. It separated all 16 development examples used to choose it. That fit measures calibration-set performance. The service recomputes the cutoff after a revision change and applies it only to the five-source official corpus. [Calibration examples and scores](calibration-results.json)

With supplied synthetic evidence, the generation adapter made the expected sufficiency decision in **4 of 5** cases. It abstained for unrelated evidence and an explicit version mismatch. It returned a draft without echoing the injected marker on the injection case. Two outputs show why a reviewer must read the actual steps:

- **Conflict.** The model accepted a draft despite two guides disagreeing about a required field. It should have escalated.
- **Similar-looking error.** The model identified the case as answerable but suggested checking for a path parameter in the JSON payload. That action is incorrect despite the valid citation.

The sufficiency score evaluates a boolean decision. It cannot measure whether every proposed action follows from its quotation. Run `python -m scripts.evaluate_generation` with the desired provider configured to inspect all five raw outputs. The controlled runner supplies evidence directly and exercises generation independently from retrieval. [Model decisions, responses and timings](generation-results.json)
