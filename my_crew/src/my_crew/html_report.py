"""
Generates a professional HTML investment report from agent outputs + live yfinance data.
All layout and styling is done in Python — never delegated to the LLM.
"""
import html as _h
import yfinance as yf
from datetime import datetime, timedelta


# ─────────────────────────── Stock data ───────────────────────────────────────

def _fetch(symbol: str) -> dict:
    ticker = yf.Ticker(symbol)
    today = datetime.today()
    ytd_start = datetime(today.year, 1, 1)

    period_defs = [
        ("1 Week",   today - timedelta(weeks=1)),
        ("1 Month",  today - timedelta(days=30)),
        ("3 Months", today - timedelta(days=90)),
        ("6 Months", today - timedelta(days=180)),
        ("YTD",      ytd_start),
        ("1 Year",   today - timedelta(days=365)),
        ("2 Years",  today - timedelta(days=730)),
        ("3 Years",  today - timedelta(days=1095)),
        ("5 Years",  today - timedelta(days=1825)),
    ]

    periods = []
    for label, start in period_defs:
        hist = ticker.history(start=start.strftime("%Y-%m-%d"), end=today.strftime("%Y-%m-%d"))
        if hist.empty:
            continue
        op = hist["Open"].iloc[0]
        cl = hist["Close"].iloc[-1]
        pct = (cl - op) / op * 100
        periods.append({
            "label": label,
            "start": op,
            "current": cl,
            "high": hist["High"].max(),
            "low": hist["Low"].min(),
            "volume": hist["Volume"].mean(),
            "pct": pct,
        })

    hist_1y = ticker.history(
        start=(today - timedelta(days=365)).strftime("%Y-%m-%d"),
        end=today.strftime("%Y-%m-%d"),
    )
    current_price = ma50 = ma200 = None
    if not hist_1y.empty:
        closes = hist_1y["Close"]
        current_price = closes.iloc[-1]
        ma50  = closes.tail(50).mean()  if len(closes) >= 50  else None
        ma200 = closes.tail(200).mean() if len(closes) >= 200 else None

    info = ticker.info
    return {
        "periods": periods,
        "current_price": current_price,
        "ma50": ma50,
        "ma200": ma200,
        "info": info,
    }


# ─────────────────────────── Text → HTML ──────────────────────────────────────

def _fmt(text: str) -> str:
    """Convert plain-text agent output to tidy HTML paragraphs / lists."""
    lines = text.strip().splitlines()
    out, in_list = [], False

    for raw in lines:
        line = raw.strip()
        if not line:
            if in_list:
                out.append("</ul>")
                in_list = False
            continue

        is_bullet = line.startswith(("- ", "* ", "• "))
        is_numbered = (
            len(line) > 2
            and line[0].isdigit()
            and line[1] in ".)"
            and line[2] == " "
        )
        is_header = (
            not is_bullet
            and not is_numbered
            and line.endswith(":")
            and len(line) < 70
        )

        if is_bullet or is_numbered:
            if not in_list:
                out.append('<ul class="agent-list">')
                in_list = True
            content = line[2:].strip() if (is_bullet or is_numbered) else line
            out.append(f"  <li>{_h.escape(content)}</li>")
        else:
            if in_list:
                out.append("</ul>")
                in_list = False
            if is_header:
                out.append(f'<h4 class="sub-heading">{_h.escape(line)}</h4>')
            else:
                out.append(f"<p>{_h.escape(line)}</p>")

    if in_list:
        out.append("</ul>")
    return "\n".join(out)


# ─────────────────────────── Helpers ──────────────────────────────────────────

def _fmt_num(v, prefix="$", suffix="", decimals=2):
    if v is None or v == "N/A":
        return "—"
    try:
        return f"{prefix}{float(v):,.{decimals}f}{suffix}"
    except Exception:
        return str(v)

def _fmt_large(v):
    if v is None or v == "N/A":
        return "—"
    try:
        v = float(v)
        if v >= 1e12: return f"${v/1e12:.2f}T"
        if v >= 1e9:  return f"${v/1e9:.2f}B"
        if v >= 1e6:  return f"${v/1e6:.2f}M"
        return f"${v:,.0f}"
    except Exception:
        return str(v)

def _pct_class(pct):
    return "up" if pct >= 0 else "down"

def _pct_str(pct):
    return f"{pct:+.2f}%"


# ─────────────────────────── Main generator ───────────────────────────────────

def generate_report(
    company: str,
    symbol: str,
    report_date: str,
    fundamental_text: str,
    technical_text: str,
    outlook_text: str,
    output_path: str = "stock_report.html",
) -> None:
    print("  [html] Fetching live stock data…", flush=True)
    data = _fetch(symbol)
    info = data["info"]
    cp   = data["current_price"]
    ma50 = data["ma50"]
    ma200= data["ma200"]

    # ── Metric cards ──────────────────────────────────────────────────────────
    mktcap   = _fmt_large(info.get("marketCap"))
    pe       = _fmt_num(info.get("trailingPE"), prefix="", decimals=1)
    fwd_pe   = _fmt_num(info.get("forwardPE"),  prefix="", decimals=1)
    w52h     = _fmt_num(info.get("fiftyTwoWeekHigh"))
    w52l     = _fmt_num(info.get("fiftyTwoWeekLow"))
    beta_v   = _fmt_num(info.get("beta"), prefix="", decimals=2)
    dy_raw   = info.get("dividendYield")
    div_y    = f"{dy_raw*100:.2f}%" if isinstance(dy_raw, float) else "—"
    sector   = info.get("sector", "—")
    cur_str  = _fmt_num(cp) if cp else "—"

    # ── Price table rows ───────────────────────────────────────────────────────
    rows_html = ""
    for p in data["periods"]:
        cls = _pct_class(p["pct"])
        rows_html += f"""
        <tr>
          <td class="period-label">{_h.escape(p['label'])}</td>
          <td>{_fmt_num(p['start'])}</td>
          <td><strong>{_fmt_num(p['current'])}</strong></td>
          <td class="up">{_fmt_num(p['high'])}</td>
          <td class="down">{_fmt_num(p['low'])}</td>
          <td>{int(p['volume']/1e6*10)/10}M</td>
          <td class="{cls} bold">{_pct_str(p['pct'])}</td>
        </tr>"""

    # ── Moving average rows ────────────────────────────────────────────────────
    def ma_row(label, ma_val):
        if ma_val is None or cp is None:
            return f"<tr><td>{label}</td><td>—</td><td>—</td></tr>"
        rel = "above" if cp > ma_val else "below"
        cls = "up" if cp > ma_val else "down"
        return (f'<tr><td>{label}</td>'
                f'<td><strong>{_fmt_num(ma_val)}</strong></td>'
                f'<td class="{cls}">{rel}</td></tr>')

    golden = "—"
    if ma50 and ma200:
        golden = '<span class="up">Golden Cross ✓</span>' if ma50 > ma200 else '<span class="down">Death Cross ✗</span>'

    # ── Format agent sections ──────────────────────────────────────────────────
    fundamental_html = _fmt(fundamental_text)
    technical_html   = _fmt(technical_text)
    outlook_html     = _fmt(outlook_text)

    # ── Full HTML ──────────────────────────────────────────────────────────────
    html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{_h.escape(company)} ({_h.escape(symbol)}) — Investment Report {_h.escape(report_date)}</title>
<style>
  /* ── Reset & base ── */
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', system-ui, Arial, sans-serif;
         background: #eef1f6; color: #1e2433; font-size: 15px; line-height: 1.6; }}
  a {{ color: #3b82f6; }}

  /* ── Layout ── */
  .page {{ max-width: 980px; margin: 0 auto; padding: 28px 18px 48px; }}

  /* ── Header ── */
  .header {{ background: linear-gradient(135deg, #0d1b36 0%, #1a3a6b 55%, #0f5ca8 100%);
             color: #fff; border-radius: 14px; padding: 40px 44px 36px; margin-bottom: 26px;
             box-shadow: 0 6px 24px rgba(15,92,168,.3); }}
  .header-top {{ display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 16px; }}
  .header h1 {{ font-size: 2.2rem; font-weight: 800; letter-spacing: -.5px; }}
  .header .ticker {{ font-size: 1.1rem; color: #7eb8f7; margin-top: 4px; }}
  .header .date-badge {{ background: rgba(255,255,255,.1); border: 1px solid rgba(255,255,255,.2);
                          border-radius: 8px; padding: 8px 16px; font-size: .85rem; color: #c8dff8;
                          white-space: nowrap; }}
  .sector-pill {{ display: inline-block; margin-top: 14px; padding: 5px 14px;
                  background: rgba(255,255,255,.12); border: 1px solid rgba(255,255,255,.25);
                  border-radius: 20px; font-size: .82rem; color: #a8d0f5; }}

  /* ── Metric strip ── */
  .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(110px, 1fr));
              gap: 12px; margin-bottom: 26px; }}
  .metric {{ background: #fff; border-radius: 10px; padding: 16px 12px; text-align: center;
             box-shadow: 0 2px 8px rgba(0,0,0,.06); border-top: 3px solid #e5e7eb; }}
  .metric.accent  {{ border-top-color: #3b82f6; }}
  .metric.green   {{ border-top-color: #16a34a; }}
  .metric.red     {{ border-top-color: #dc2626; }}
  .metric .mlabel {{ font-size: .68rem; text-transform: uppercase; letter-spacing: .6px;
                     color: #9ca3af; margin-bottom: 6px; }}
  .metric .mval   {{ font-size: 1.18rem; font-weight: 700; color: #1e2433; }}

  /* ── Agent section cards ── */
  .agent-card {{ background: #fff; border-radius: 12px; margin-bottom: 22px;
                 box-shadow: 0 2px 10px rgba(0,0,0,.07); overflow: hidden; }}
  .agent-header {{ display: flex; align-items: center; gap: 14px; padding: 18px 26px;
                   border-bottom: 1px solid #f0f2f7; }}
  .agent-icon {{ width: 42px; height: 42px; border-radius: 10px; display: flex;
                 align-items: center; justify-content: center; font-size: 1.3rem;
                 flex-shrink: 0; }}
  .icon-fundamental {{ background: #eff6ff; }}
  .icon-technical   {{ background: #f0fdf4; }}
  .icon-outlook     {{ background: #fffbeb; }}
  .agent-title {{ flex: 1; }}
  .agent-title h2 {{ font-size: 1.05rem; font-weight: 700; color: #1e2433; }}
  .agent-title .agent-role {{ font-size: .78rem; color: #9ca3af; margin-top: 1px; }}
  .agent-badge {{ font-size: .72rem; padding: 3px 10px; border-radius: 12px; font-weight: 600; }}
  .badge-fundamental {{ background: #dbeafe; color: #1d4ed8; }}
  .badge-technical   {{ background: #dcfce7; color: #15803d; }}
  .badge-outlook     {{ background: #fef3c7; color: #92400e; }}
  .agent-body {{ padding: 22px 26px; }}

  /* ── Text formatting ── */
  .agent-body p {{ color: #374151; margin-bottom: 10px; }}
  .agent-body h4.sub-heading {{ font-size: .9rem; font-weight: 700; color: #0f5ca8;
                                 margin: 16px 0 6px; text-transform: uppercase;
                                 letter-spacing: .4px; }}
  .agent-list {{ padding-left: 22px; margin-bottom: 10px; }}
  .agent-list li {{ color: #374151; margin-bottom: 5px; }}

  /* ── Price table ── */
  .table-wrap {{ overflow-x: auto; margin-bottom: 22px; }}
  .price-table {{ width: 100%; border-collapse: collapse; font-size: .87rem; white-space: nowrap; }}
  .price-table thead tr {{ background: #0d1b36; color: #fff; }}
  .price-table th {{ padding: 11px 14px; text-align: right; font-weight: 600; letter-spacing: .3px; }}
  .price-table th:first-child {{ text-align: left; }}
  .price-table td {{ padding: 9px 14px; text-align: right; border-bottom: 1px solid #f0f2f7; }}
  .price-table td.period-label {{ text-align: left; font-weight: 600; color: #374151; }}
  .price-table tbody tr:hover {{ background: #f9fafb; }}
  .price-table tbody tr:nth-child(even) {{ background: #fafbfc; }}
  .price-table tbody tr:nth-child(even):hover {{ background: #f3f4f6; }}
  .bold {{ font-weight: 700; }}

  /* ── MA + key levels ── */
  .two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 6px; }}
  @media (max-width: 640px) {{ .two-col {{ grid-template-columns: 1fr; }} }}
  .mini-card {{ background: #f9fafb; border-radius: 8px; padding: 16px; }}
  .mini-card h4 {{ font-size: .82rem; font-weight: 700; text-transform: uppercase;
                   letter-spacing: .5px; color: #6b7280; margin-bottom: 10px; }}
  .mini-table {{ width: 100%; border-collapse: collapse; font-size: .86rem; }}
  .mini-table td {{ padding: 7px 8px; border-bottom: 1px solid #e5e7eb; }}
  .mini-table td:first-child {{ color: #6b7280; }}
  .mini-table td:last-child {{ font-weight: 600; text-align: right; }}
  .mini-table tr:last-child td {{ border-bottom: none; }}

  /* ── Colours ── */
  .up   {{ color: #16a34a; }}
  .down {{ color: #dc2626; }}

  /* ── Footer ── */
  .footer {{ background: #f1f3f8; border: 1px solid #dde1ea; border-radius: 10px;
             padding: 18px 22px; font-size: .76rem; color: #9ca3af; line-height: 1.7; }}
  .footer strong {{ color: #6b7280; }}
</style>
</head>
<body>
<div class="page">

  <!-- ── HEADER ───────────────────────────────────────────────────────────── -->
  <div class="header">
    <div class="header-top">
      <div>
        <h1>{_h.escape(company)}</h1>
        <div class="ticker">{_h.escape(symbol)} &nbsp;·&nbsp; Investment Research Report</div>
      </div>
      <div class="date-badge">📅 {_h.escape(report_date)}</div>
    </div>
    <div class="sector-pill">🏢 {_h.escape(sector)}</div>
  </div>

  <!-- ── METRIC STRIP ──────────────────────────────────────────────────────── -->
  <div class="metrics">
    <div class="metric accent">
      <div class="mlabel">Current Price</div>
      <div class="mval">{cur_str}</div>
    </div>
    <div class="metric accent">
      <div class="mlabel">Market Cap</div>
      <div class="mval">{mktcap}</div>
    </div>
    <div class="metric green">
      <div class="mlabel">52W High</div>
      <div class="mval up">{w52h}</div>
    </div>
    <div class="metric red">
      <div class="mlabel">52W Low</div>
      <div class="mval down">{w52l}</div>
    </div>
    <div class="metric">
      <div class="mlabel">P/E (TTM)</div>
      <div class="mval">{pe}</div>
    </div>
    <div class="metric">
      <div class="mlabel">Fwd P/E</div>
      <div class="mval">{fwd_pe}</div>
    </div>
    <div class="metric">
      <div class="mlabel">Beta</div>
      <div class="mval">{beta_v}</div>
    </div>
    <div class="metric">
      <div class="mlabel">Dividend Yield</div>
      <div class="mval">{div_y}</div>
    </div>
  </div>

  <!-- ── AGENT 1 — FUNDAMENTAL ANALYST ────────────────────────────────────── -->
  <div class="agent-card">
    <div class="agent-header">
      <div class="agent-icon icon-fundamental">📊</div>
      <div class="agent-title">
        <h2>Fundamental Analysis</h2>
        <div class="agent-role">Fundamental Research Analyst · {_h.escape(company)}</div>
      </div>
      <span class="agent-badge badge-fundamental">Agent 1 / 3</span>
    </div>
    <div class="agent-body">
      {fundamental_html}
    </div>
  </div>

  <!-- ── AGENT 2 — TECHNICAL ANALYST ──────────────────────────────────────── -->
  <div class="agent-card">
    <div class="agent-header">
      <div class="agent-icon icon-technical">📈</div>
      <div class="agent-title">
        <h2>Technical Analysis</h2>
        <div class="agent-role">Technical Analysis Specialist · {_h.escape(symbol)}</div>
      </div>
      <span class="agent-badge badge-technical">Agent 2 / 3</span>
    </div>
    <div class="agent-body">

      <!-- Price table built from live yfinance data -->
      <div class="table-wrap">
        <table class="price-table">
          <thead>
            <tr>
              <th>Period</th>
              <th>Start Price</th>
              <th>Current</th>
              <th>High</th>
              <th>Low</th>
              <th>Avg Volume</th>
              <th>Change %</th>
            </tr>
          </thead>
          <tbody>{rows_html}
          </tbody>
        </table>
      </div>

      <!-- Moving averages + key levels -->
      <div class="two-col">
        <div class="mini-card">
          <h4>Moving Averages</h4>
          <table class="mini-table">
            {ma_row("50-Day MA", ma50)}
            {ma_row("200-Day MA", ma200)}
            <tr><td>MA Signal</td><td>{golden}</td></tr>
          </table>
        </div>
        <div class="mini-card">
          <h4>Key Price Levels</h4>
          <table class="mini-table">
            <tr><td>52W High (resistance)</td><td class="up">{w52h}</td></tr>
            <tr><td>52W Low (support)</td><td class="down">{w52l}</td></tr>
            <tr><td>Current Price</td><td>{cur_str}</td></tr>
          </table>
        </div>
      </div>

      <!-- Agent narrative -->
      <br>
      {technical_html}
    </div>
  </div>

  <!-- ── AGENT 3 — SUMMARY / OUTLOOK ───────────────────────────────────────── -->
  <div class="agent-card">
    <div class="agent-header">
      <div class="agent-icon icon-outlook">🎯</div>
      <div class="agent-title">
        <h2>Investment Outlook &amp; Summary</h2>
        <div class="agent-role">Investment Research Summariser · {_h.escape(company)}</div>
      </div>
      <span class="agent-badge badge-outlook">Agent 3 / 3</span>
    </div>
    <div class="agent-body">
      {outlook_html}
    </div>
  </div>

  <!-- ── FOOTER ──────────────────────────────────────────────────────────────── -->
  <div class="footer">
    <strong>Disclaimer:</strong> This report is generated by an AI research system for informational
    purposes only and does not constitute financial advice. Data is sourced from public market feeds and
    AI-generated analysis — it may contain errors or omissions. Past performance is not indicative of
    future results. Always conduct your own due diligence and consult a licensed financial advisor
    before making any investment decisions. &nbsp;·&nbsp; Generated {_h.escape(report_date)}.
  </div>

</div>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_doc)
    print(f"  [html] Report written → {output_path}", flush=True)
