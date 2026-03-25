import yfinance as yf
from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
from datetime import datetime, timedelta


class StockDataInput(BaseModel):
    """Input schema for StockDataTool."""
    symbol: str = Field(..., description="Stock ticker symbol, e.g. 'AAPL'")


class StockDataTool(BaseTool):
    name: str = "Stock Price Data Tool"
    description: str = (
        "Fetches historical stock price data for a given ticker symbol. "
        "Returns OHLCV (Open, High, Low, Close, Volume) summary statistics "
        "for the following periods: 1 week, 1 month, 3 months, 6 months, "
        "YTD, 1 year, 2 years, 3 years, and 5 years. "
        "Also includes 50-day and 200-day moving averages and key fundamentals. "
        "Use this to perform technical price analysis on a stock."
    )
    args_schema: Type[BaseModel] = StockDataInput

    def _run(self, symbol: str) -> str:
        try:
            ticker = yf.Ticker(symbol)
            today = datetime.today()
            ytd_start = datetime(today.year, 1, 1)

            periods = {
                "1 Week":   today - timedelta(weeks=1),
                "1 Month":  today - timedelta(days=30),
                "3 Months": today - timedelta(days=90),
                "6 Months": today - timedelta(days=180),
                "YTD":      ytd_start,
                "1 Year":   today - timedelta(days=365),
                "2 Years":  today - timedelta(days=730),
                "3 Years":  today - timedelta(days=1095),
                "5 Years":  today - timedelta(days=1825),
            }

            results = []
            for label, start_date in periods.items():
                hist = ticker.history(
                    start=start_date.strftime("%Y-%m-%d"),
                    end=today.strftime("%Y-%m-%d"),
                )
                if hist.empty:
                    results.append(f"{label}: No data available.")
                    continue

                open_price = hist["Open"].iloc[0]
                close_price = hist["Close"].iloc[-1]
                high = hist["High"].max()
                low = hist["Low"].min()
                avg_volume = hist["Volume"].mean()
                pct_change = ((close_price - open_price) / open_price) * 100

                results.append(
                    f"{label}:\n"
                    f"  Period Start Price : ${open_price:.2f}\n"
                    f"  Current Price      : ${close_price:.2f}\n"
                    f"  Period High        : ${high:.2f}\n"
                    f"  Period Low         : ${low:.2f}\n"
                    f"  Avg Daily Volume   : {avg_volume:,.0f}\n"
                    f"  Price Change       : {pct_change:+.2f}%\n"
                )

            # Moving averages using 1-year history
            hist_1y = ticker.history(
                start=(today - timedelta(days=365)).strftime("%Y-%m-%d"),
                end=today.strftime("%Y-%m-%d"),
            )
            ma_lines = ""
            if not hist_1y.empty:
                closes = hist_1y["Close"]
                current = closes.iloc[-1]
                ma50 = closes.tail(50).mean() if len(closes) >= 50 else None
                ma200 = closes.tail(200).mean() if len(closes) >= 200 else None
                ma50_str = f"${ma50:.2f} ({'above' if current > ma50 else 'below'})" if ma50 else "N/A"
                ma200_str = f"${ma200:.2f} ({'above' if current > ma200 else 'below'})" if ma200 else "N/A"
                ma_lines = (
                    f"\nMoving Averages (current price ${current:.2f}):\n"
                    f"  50-Day MA  : {ma50_str}\n"
                    f"  200-Day MA : {ma200_str}\n"
                )

            info = ticker.info
            company_name = info.get("longName", symbol)
            market_cap = info.get("marketCap", "N/A")
            pe_ratio = info.get("trailingPE", "N/A")
            fwd_pe = info.get("forwardPE", "N/A")
            week_52_high = info.get("fiftyTwoWeekHigh", "N/A")
            week_52_low = info.get("fiftyTwoWeekLow", "N/A")
            sector = info.get("sector", "N/A")
            dividend_yield = info.get("dividendYield", "N/A")
            beta = info.get("beta", "N/A")

            if isinstance(market_cap, (int, float)):
                market_cap_str = f"${market_cap / 1e9:.1f}B"
            else:
                market_cap_str = str(market_cap)

            if isinstance(dividend_yield, float):
                dividend_yield_str = f"{dividend_yield * 100:.2f}%"
            else:
                dividend_yield_str = str(dividend_yield)

            header = (
                f"Stock Data for {company_name} ({symbol})\n"
                f"Sector: {sector}\n"
                f"Market Cap: {market_cap_str}\n"
                f"Trailing P/E: {pe_ratio}\n"
                f"Forward P/E: {fwd_pe}\n"
                f"52-Week High: ${week_52_high}\n"
                f"52-Week Low:  ${week_52_low}\n"
                f"Dividend Yield: {dividend_yield_str}\n"
                f"Beta: {beta}\n"
                f"{'=' * 50}\n"
            )

            return header + ma_lines + "\n" + "\n".join(results)

        except Exception as e:
            return f"Error fetching stock data for '{symbol}': {str(e)}"
