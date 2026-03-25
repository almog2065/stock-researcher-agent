#!/usr/bin/env python
import sys
import warnings
import os
from datetime import datetime

from dotenv import dotenv_values

# Explicitly load env vars from the shared agents .env file
os.environ.update(dotenv_values('/Users/almogbensimon/Projects/agents/.env'))

from my_crew.crew import MyCrew
from my_crew.html_report import generate_report

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")


def fetch_search_results(company: str, symbol: str) -> str:
    """Fetch web search results using DuckDuckGo (free, no API key required)."""
    from ddgs import DDGS
    queries = [
        f"{company} stock news 2026",
        f"{symbol} latest earnings revenue EPS results",
        f"{symbol} analyst rating price target consensus",
        f"{symbol} insider buying selling activity",
    ]
    sections = []
    with DDGS() as ddgs:
        for query in queries:
            try:
                results = list(ddgs.text(query, max_results=4))
                lines = [f"Query: {query}"]
                for r in results:
                    lines.append(f"- {r.get('title', '')}: {r.get('body', '')}")
                sections.append("\n".join(lines))
                print(f"  [ddg] ✓ {query[:50]}", flush=True)
            except Exception as e:
                sections.append(f"Query: {query}\n- Search failed: {e}")
                print(f"  [ddg] ✗ {query[:50]} — {e}", flush=True)
    return "\n\n---\n\n".join(sections)


def fetch_stock_data(symbol: str) -> str:
    """Use StockDataTool directly to get live price data."""
    from my_crew.tools.stock_data_tool import StockDataTool
    tool = StockDataTool()
    return tool._run(symbol=symbol)


def run():
    """
    Run the Stock Researcher crew.
    """
    inputs = {
        'company': 'Apple Inc',
        'stock_symbol': 'AAPL',
        'current_date': datetime.now().strftime("%Y-%m-%d"),
    }

    print(f"\n{'='*60}", flush=True)
    print(f"  Stock Research Crew — {inputs['company']} ({inputs['stock_symbol']})", flush=True)
    print(f"  Date: {inputs['current_date']}", flush=True)
    print(f"{'='*60}\n", flush=True)

    # Pre-fetch all data in Python — agents only summarize, no tool-calling needed
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 Fetching web search results via DuckDuckGo…", flush=True)
    inputs['search_results'] = fetch_search_results(inputs['company'], inputs['stock_symbol'])
    print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Search results ready", flush=True)

    print(f"[{datetime.now().strftime('%H:%M:%S')}] 📈 Fetching live stock data…", flush=True)
    inputs['stock_data'] = fetch_stock_data(inputs['stock_symbol'])
    print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Stock data ready", flush=True)

    try:
        start = datetime.now()
        print(f"[{start.strftime('%H:%M:%S')}] 🚀 Crew started", flush=True)
        result = MyCrew().crew().kickoff(inputs=inputs)
        elapsed = (datetime.now() - start).seconds
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🏁 Agents finished in {elapsed}s", flush=True)

        # Extract each agent's raw text output
        task_outputs = result.tasks_output  # [fundamental, technical, summary]
        fundamental_text = task_outputs[0].raw if len(task_outputs) > 0 else ""
        technical_text   = task_outputs[1].raw if len(task_outputs) > 1 else ""
        outlook_text     = task_outputs[2].raw if len(task_outputs) > 2 else ""

        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🎨 Generating HTML report…", flush=True)
        generate_report(
            company=inputs['company'],
            symbol=inputs['stock_symbol'],
            report_date=inputs['current_date'],
            fundamental_text=fundamental_text,
            technical_text=technical_text,
            outlook_text=outlook_text,
            output_path='stock_report.html',
        )
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Done → stock_report.html\n", flush=True)
    except Exception as e:
        raise Exception(f"An error occurred while running the crew: {e}")


def train():
    """
    Train the crew for a given number of iterations.
    """
    inputs = {
        'company': 'Apple Inc',
        'stock_symbol': 'AAPL',
        'current_date': datetime.now().strftime("%Y-%m-%d"),
    }
    try:
        MyCrew().crew().train(
            n_iterations=int(sys.argv[1]),
            filename=sys.argv[2],
            inputs=inputs,
        )
    except Exception as e:
        raise Exception(f"An error occurred while training the crew: {e}")


def replay():
    """
    Replay the crew execution from a specific task.
    """
    try:
        MyCrew().crew().replay(task_id=sys.argv[1])
    except Exception as e:
        raise Exception(f"An error occurred while replaying the crew: {e}")


def test():
    """
    Test the crew execution and returns the results.
    """
    inputs = {
        'company': 'Apple Inc',
        'stock_symbol': 'AAPL',
        'current_date': datetime.now().strftime("%Y-%m-%d"),
    }
    try:
        MyCrew().crew().test(
            n_iterations=int(sys.argv[1]),
            eval_llm=sys.argv[2],
            inputs=inputs,
        )
    except Exception as e:
        raise Exception(f"An error occurred while testing the crew: {e}")


def run_with_trigger():
    """
    Run the crew with trigger payload.
    """
    import json

    if len(sys.argv) < 2:
        raise Exception("No trigger payload provided. Please provide JSON payload as argument.")

    try:
        trigger_payload = json.loads(sys.argv[1])
    except json.JSONDecodeError:
        raise Exception("Invalid JSON payload provided as argument")

    inputs = {
        "crewai_trigger_payload": trigger_payload,
        "company": trigger_payload.get("company", ""),
        "stock_symbol": trigger_payload.get("stock_symbol", ""),
        "current_date": datetime.now().strftime("%Y-%m-%d"),
    }

    try:
        result = MyCrew().crew().kickoff(inputs=inputs)
        return result
    except Exception as e:
        raise Exception(f"An error occurred while running the crew with trigger: {e}")
