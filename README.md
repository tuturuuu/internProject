# Intern Project — Ranking & Retrieval

Small research/prototype codebase for retrieval, ranking, and LLM-based re-ranking.

## Overview
- `app/` : application entry and API routes
- `retrieval/` : retrieval components (mock retrieval)
- `ranking/` : ranking implementations and ranker wrappers
- `llm/` : prompts and LLM-related utilities
- `data/` : sample datasets (business, user history, labels)
- `models/` : model artifacts and predictions
- `script/` : utilities and evaluation/generation scripts

## Prerequisites
- Python 3.8+
- Install dependencies:

```bash
pip install -r requirements.txt
```

## Quick start
- Run the example combined pipeline:

```bash
python script/combined.py
```

- Run the API (if applicable):

```bash
python app/main.py
```

## Project notes
- Configuration can use a `.env` file (ignored by default).
- Large/generated artifacts (models, processed data) can be ignored via `.gitignore` — see the commented lines in that file.

## Structure (high level)
- See `script/` for generation and evaluation helpers.
- Check `ranking/` for ranker implementations and `retrieval/` for retrieval mocks.

## License & Contact
This repository is provided as-is for internal use. For questions, contact the project owner.
