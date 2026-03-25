# Stock Research Crew

An AI-powered investment research system built with [CrewAI](https://crewai.com). Three specialised agents collaborate to produce a professional HTML investment report for any publicly traded stock — combining live web search data, real-time price history, and LLM-generated analysis.

---

## Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Stock Research Crew                  │
│                                                         │
│  🔍 Python pre-fetches DuckDuckGo search results        │
│                        │                               │
│  ┌─────────────────────▼──────────────────────────┐    │
│  │  Agent 1 — Fundamental Research Analyst        │    │
│  │  Summarises live news, earnings, analyst        │    │
│  │  consensus, insider activity & catalysts        │    │
│  └─────────────────────┬──────────────────────────┘    │
│                        │                               │
│  ┌─────────────────────▼──────────────────────────┐    │
│  │  Agent 2 — Technical Analysis Specialist       │    │
│  │  Uses StockDataTool (yfinance) to analyse       │    │
│  │  price action across 9 time periods + MAs       │    │
│  └─────────────────────┬──────────────────────────┘    │
│                        │                               │
│  ┌─────────────────────▼──────────────────────────┐    │
│  │  Agent 3 — Investment Research Summariser      │    │
│  │  Synthesises both analyses into executive       │    │
│  │  summary, outlook, and key risks                │    │
│  └─────────────────────┬──────────────────────────┘    │
│                        │                               │
│  🎨 Python renders professional HTML report            │
│     (layout, tables & styling done in code,            │
│      not delegated to the LLM)                         │
└─────────────────────────────────────────────────────────┘
```

---

## Features

- **Live web search** — DuckDuckGo queries are pre-fetched in Python and injected into the fundamental agent's prompt (no API key required), making it work reliably with any local LLM
- **Real-time stock data** — yfinance provides OHLCV data for **9 time periods**: 1W · 1M · 3M · 6M · YTD · 1Y · 2Y · 3Y · 5Y
- **Moving averages** — 50-day and 200-day MAs with Golden Cross / Death Cross signal
- **Key fundamentals** — Market Cap, P/E (TTM & Forward), 52-Week High/Low, Beta, Dividend Yield
- **Code-rendered HTML** — The report layout, price table, and metric cards are generated entirely in Python (`html_report.py`), guaranteeing quality regardless of LLM size
- **Three agent sections** — Each agent's output is displayed in its own clearly labelled card
- **Progress logging** — Timestamped console output shows crew progress in real time
- **Local LLM support** — Runs on Ollama (no cloud API required)

---

## Report Output

The generated `stock_report.html` includes:

| Section | Source |
|---|---|
| Header + Metric Strip (8 KPIs) | yfinance — live data |
| Fundamental Analysis | Agent 1 — LLM summary of DuckDuckGo results |
| Technical Analysis — 9-period price table | yfinance — live data (Python-rendered) |
| Moving Averages + Key Price Levels | yfinance — live data |
| Technical Narrative | Agent 2 — LLM synthesis |
| Investment Outlook & Risks | Agent 3 — LLM synthesis |

---

## Requirements

- Python 3.10–3.13
- [Ollama](https://ollama.com) running locally

---

## Setup

### 1. Install dependencies

```bash
uv sync
```

### 2. Configure environment variables

Add the following to your shared `.env` file (loaded by `main.py`):

```env
# LLM — Ollama local model
OLLAMA_URL=http://localhost:11434/v1
OLLAMA_MODEL=openai/llama3.2:3b
OLLAMA_API_KEY=ollama
```

### 3. Pull the Ollama model

```bash
ollama pull llama3.2:3b
```

### 4. Start Ollama (if not already running)

```bash
ollama serve
```

---

## Usage

```bash
# Run the crew (default: Apple Inc / AAPL)
uv run my_crew
```

The report is written to `stock_report.html` in the project root. Open it in any browser.

### Other commands

```bash
uv run train      # Train the crew for N iterations
uv run replay     # Replay from a specific task ID
uv run test       # Run evaluation test
```

---

## Project Structure

```
my_crew/
├── src/my_crew/
│   ├── main.py                 # Entry point — DuckDuckGo pre-fetch, crew kickoff, HTML generation
│   ├── crew.py                 # Agent and task definitions
│   ├── html_report.py          # Python HTML report generator (yfinance + agent outputs)
│   ├── config/
│   │   ├── agents.yaml         # Agent roles, goals, and backstories
│   │   └── tasks.yaml          # Task descriptions and expected outputs
│   └── tools/
│       └── stock_data_tool.py  # CrewAI tool wrapping yfinance (9 periods + MAs)
├── stock_report.html           # Generated output
├── pyproject.toml
└── README.md
```

---

## Customising the Target Stock

Edit the `inputs` dict in `main.py`:

```python
inputs = {
    'company': 'Microsoft Corporation',
    'stock_symbol': 'MSFT',
    'current_date': datetime.now().strftime("%Y-%m-%d"),
}
```

---

## Architecture Notes

### Why search results are pre-fetched in Python

Small local models (e.g. `llama3.2:3b`) do not reliably follow CrewAI's ReAct tool-calling pattern — they output a JSON tool description as their final answer instead of actually invoking the tool. To work around this, `main.py` uses `ddgs` (DuckDuckGo Search) to fetch results before the crew starts and injects them into the fundamental agent's prompt as plain text. The agent only needs to summarise, not call tools. DuckDuckGo requires no API key.

### Why HTML is generated in Python

Delegating HTML generation to a small LLM produces inconsistent, often malformed output. Instead, `html_report.py` renders the full report using Python string templating and live yfinance data. Agent outputs are passed in as plain text and formatted with a simple text-to-HTML converter, guaranteeing a professional result every time.

---

## Dependencies

| Package | Purpose |
|---|---|
| `crewai[tools]` | Multi-agent orchestration framework |
| `yfinance` | Real-time and historical stock data |
| `ddgs` | DuckDuckGo web search (free, no API key) |

---

## License

MIT
