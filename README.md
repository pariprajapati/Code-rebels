# Operation Abhedya-Chakra — Full Offline Website

Void Hacks() 8.0 | Offline-first Money Mule Investigation Platform

This is a complete hackathon-ready implementation scaffold covering Modules A, B, C and D:

- Module A: DuckDB high-throughput CSV ingestion, normalization, indexes and benchmark
- Module B: deterministic Mule Risk Index (0–100), velocity, fan-in, fan-out and terminal indicators
- Module C: local FastAPI investigation API + zero-dependency offline graph UI
- Module D: evidence-only local Ollama document generation with post-generation anti-hallucination validation

## Requirements

- Windows 10/11 or Linux
- Python 3.11+
- 16 GB RAM recommended for the 2M-row dataset
- SSD strongly recommended
- Optional: Ollama for local AI document drafting

## Quick Start — Windows

1. Extract this ZIP.
2. Open a terminal in the project folder.
3. Run:

   setup.bat

4. Build the local database:

   ingest.bat

5. Start the website:

   run.bat

6. Open http://127.0.0.1:8000

## Quick Start — PowerShell/Linux

    python -m venv .venv
    .venv\\Scripts\\activate       # Windows
    # source .venv/bin/activate     # Linux/macOS
    python -m pip install -r backend/requirements.txt
    python scripts/prepare_data.py --csv data/raw/VoidHacks8_MuleAccount_2M_Transactions.csv
    python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000

## Optional Local AI

Install Ollama separately, then pull a small local model, for example:

    ollama pull llama3.2:3b

The website works without Ollama: Module D falls back to a deterministic evidence template. Ollama is never the source of forensic facts.

## Important Performance Note

The supplied dataset is included in this package. The benchmark is measured on the actual data at runtime. Do not promise a <=60s result until you run `python scripts/prepare_data.py` on the exact jury laptop. Hardware, SSD speed, Python/DuckDB versions and index build time affect the result.

## Architecture

CSV -> DuckDB -> derived account features -> deterministic risk engine -> investigation API -> offline graph UI -> evidence JSON -> optional local Ollama -> validator -> draft notice/case diary

The browser never receives the full 2M-edge dataset. It receives only the selected account's 4-hop investigation subgraph.
