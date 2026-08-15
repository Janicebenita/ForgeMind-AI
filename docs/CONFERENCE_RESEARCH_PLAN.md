# ForgeMind AI conference research plan

## Research question

Does evidence-gated hybrid retrieval improve source recall, citation correctness, and safe abstention for industrial maintenance questions compared with keyword-only and deterministic local retrieval?

## Experimental systems

1. Local deterministic retrieval baseline.
2. Azure AI Search keyword-only baseline.
3. Azure AI Search hybrid RAG with Microsoft Foundry embeddings and generation.
4. Ablation of hybrid RAG without evidence-sufficiency gating.

## Required held-out dataset

The bundled eight-case corpus is a development smoke test only. Before submission, build a versioned and anonymized corpus with:

- at least 100 supported questions spanning work orders, incidents, SOPs, inspections, quality records, and compliance clauses
- at least 30 unsupported or adversarial questions
- document- and chunk-level relevance labels from at least two reviewers
- frozen train, development, and test splits with no document leakage
- inter-reviewer agreement and a documented disagreement process

## Metrics

- Recall@5 and Recall@10
- mean reciprocal rank
- citation precision and citation coverage
- claim-to-source groundedness
- unsupported-question abstention accuracy
- P50 and P95 end-to-end latency
- cost per answered question and per ingested document

## Acceptance gates

- No metric is a hard-coded estimate.
- Every result comes from a committed evaluator and versioned dataset.
- All baselines use the same held-out questions and relevance labels.
- Model names, versions, Search settings, dates, dataset version, and Azure region are recorded.
- Main comparisons include statistical uncertainty.
- Sensitive documents are filtered before retrieval.

## Azure benchmark

Use a dedicated Search index whose name contains `eval` or `benchmark`. The evaluator refuses to clear a general-purpose index.

```powershell
$env:AI_PROVIDER = "azure"
$env:RETRIEVAL_BACKEND = "azure_search"
$env:DOCUMENT_STORAGE_BACKEND = "azure_blob"
$env:AZURE_SEARCH_INDEX_NAME = "forgemind-eval-v1"
python backend/scripts/evaluate_retrieval.py --backend azure_search --output backend/evaluation/results/azure_search.json
```

## Milestones

1. Deploy ForgeMind to a dedicated Azure resource group after approving the budget.
2. Record the exact deployed resource/model configuration.
3. Expand and independently label the corpus.
4. Run local, keyword, hybrid, and ablation experiments.
5. Complete failure, latency, cost, and security analyses.
6. Freeze results before drafting the paper.
