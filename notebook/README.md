# Reranker pipeline notebooks

These notebooks demonstrate each ranking pipeline from scratch, using small toy datasets and local scoring functions instead of importing the app code or saved model artifacts.

- `01_tree_rerankers_from_scratch.ipynb`: standalone XGBoost-style, LightGBM-style, and CatBoost-style rerankers.
- `02_llm_reranker_from_scratch.ipynb`: standalone LLM reranker with prompt construction and deterministic mock scoring.
- `03_combined_parallel_blend_from_scratch.ipynb`: parallel GBT plus LLM-context blend using `0.8 * gbt_score + 0.2 * llm_context_score`.
- `04_sequential_gbt_to_llm_from_scratch.ipynb`: GBT first-pass shortlist followed by LLM-style reranking.
