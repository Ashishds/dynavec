# Dynavec Retrieval Evaluation Benchmarks

This directory stores offline retrieval quality evaluation results produced by dynavec.eval.run_eval().

## File Format

Each benchmark run is saved as a JSON file named eval-<timestamp>.json:

`json
{
  "dataset": "attention-paper-qa",
  "n_queries": 15,
  "mrr": 0.83,
  "recall@1": 0.73,
  "recall@3": 0.87,
  "recall@5": 0.93,
  "ndcg@1": 0.73,
  "ndcg@3": 0.85,
  "ndcg@5": 0.91,
  "timestamp": 1726567812,
  "embedder": "all-MiniLM-L6-v2",
  "namespace": "production-core",
  "elapsed_sec": 42.5
}
`

## Running a Benchmark

`powershell
# Make sure the attention paper has been ingested first:
.venv\Scripts\python.exe examples\ingest_attention_paper.py

# Then run the evaluation:
.venv\Scripts\python.exe examples\run_attention_eval.py --namespace production-core

# Results will be saved to evals/eval-<timestamp>.json
# The EvalTrends chart in the Next.js dashboard will automatically pick them up.
`

## Ground-Truth Dataset

ttention_paper_qa.json — 15 verified Q&A pairs from "Attention Is All You Need" (Vaswani et al., 2017).

Each query includes:
- 	ext: The natural language question
- elevant_ids: DynamoDB chunk IDs containing the correct answer
- expected_page: The paper page number for human verification
- 
otes: Key facts expected in the answer

## Dashboard Integration

The EvalTrends.tsx component reads all eval-*.json files via the /api/eval endpoint and plots:
- **Recall@k** — Fraction of relevant docs found in Top-K
- **MRR** — Mean Reciprocal Rank (position of first correct result)
- **nDCG@k** — Normalized Discounted Cumulative Gain

Files are loaded by the Python dashboard server via _load_eval_runs(eval_dir) in dashboard.py.
