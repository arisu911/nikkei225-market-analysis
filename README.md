# Nikkei 225 Intraday Market Behavior Research Dashboard

A quantitative, descriptive and statistical historical market-behavior research application for the **Nikkei 225 Index (`^N225`)** and paired Tokyo Stock Exchange instruments (such as `1321.T` NEXT FUNDS Nikkei 225 ETF).

All displayed timestamps and market sessions are converted to **Malaysia Time (MYT, UTC+8)**.

---

## 📌 1. Project Purpose & Scope

### What this project does:
* **Descriptive & Statistical Analysis:** Quantifies how the Nikkei 225 index typically moves across different segments of the TSE trading day, across weekdays (Monday–Friday), and across multi-year historical periods (1Y, 3Y, 5Y, 10Y).
* **Multi-Resolution Intraday Profiling:** Measures returns, ranges, volatilities, and volumes at 5m, 10m, 15m, 30m, and 60m resolutions.
* **Opening Dynamics:** Measures 08:00 MYT opening gaps, gap-fill frequencies, and opening range expansions (5m, 15m, 30m, 60m).
* **Session Comparison:** Compares Morning Session (08:00–10:30 MYT) vs Afternoon Session (11:30–14:30 MYT).
* **Intraday Excursion Paths:** Evaluates Maximum Favorable Excursion (MFE) and Maximum Adverse Excursion (MAE) from the 08:00 MYT cash open.
* **Empirical Probability Distributions:** Reports historical empirical frequencies and quantiles for price movements without predictive extrapolation.

### What this project does NOT do:
* ❌ **NOT a trading strategy or signal generator.**
* ❌ **NOT a backtester or automated execution system.**
* ❌ **NO buy/sell recommendations, stop losses, take profits, or equity curves.**
* ❌ **NO synthetic or fabricated fake data.**

---

## 🕒 2. Timezone & Market Session Schedule

| Market Phase | JST (Japan, UTC+9) | **MYT (Malaysia, UTC+8)** | Continuous Analytics Status |
| :--- | :--- | :--- | :--- |
| **TSE Cash Open** | `09:00 JST` | **`08:00 MYT`** | Included |
| **Morning Session** | `09:00 – 11:30 JST` | **`08:00 – 10:30 MYT`** | Included |
| **TSE Lunch Break** | `11:30 – 12:30 JST` | **`10:30 – 11:30 MYT`** | **Excluded / Filtered Out** |
| **Afternoon Session** | `12:30 – 15:30 JST` | **`11:30 – 14:30 MYT`** | Included |
| **TSE Cash Close** | `15:30 JST` | **`14:30 MYT`** | Included |

> [!NOTE]
> Timestamps are converted using timezone-aware conversions from `Asia/Tokyo` to `Asia/Kuala_Lumpur` via `pytz` / `zoneinfo`.

---

### 3. Quantitative Mathematical Formulas

#### Return Metrics
* **Session Simple Return ($R_t$):**
  $$R_t = \frac{\text{Close}_{\text{14:30 MYT}} - \text{Open}_{\text{08:00 MYT}}}{\text{Open}_{\text{08:00 MYT}}} \times 100\%$$
* **Bar Return ($r_i$):**
  $$r_i = \frac{\text{Close}_i - \text{Open}_i}{\text{Open}_i} \times 100\%$$
* **Absolute Return ($|R_t|$):**
  $$|R_{\text{abs}}| = |R_t|$$

#### High-Low Range
* **Absolute Range:**
  $$\text{Range}_{\text{abs}} = \text{High} - \text{Low}$$
* **Normalized Range (% of Open):**
  $$\text{Range}_{\%} = \frac{\text{High} - \text{Low}}{\text{Open}} \times 100\%$$

#### Volatility Measures
* **Sample Standard Deviation ($\sigma$):**
  $$\sigma = \sqrt{\frac{1}{N - 1} \sum_{i=1}^{N} (R_i - \bar{R})^2}$$
* **Annualized Volatility ($\sigma_{\text{annual}}$):**
  $$\sigma_{\text{annual}} = \sigma_{\text{daily}} \times \sqrt{250}$$
* **Rolling Volatility:** Rolling sample standard deviation computed over $k \in \{20, 60, 120\}$ trading sessions.

#### Opening Gaps & Gap-Fill
* **Opening Gap %:**
  $$\text{Gap}_{\%} = \frac{\text{Open}_{\text{08:00 MYT}} - \text{Close}_{\text{prev}}}{\text{Close}_{\text{prev}}} \times 100\%$$
* **Gap-Fill Condition:**
  * **Gap Up ($\text{Open} > \text{Close}_{\text{prev}}$):** Filled if intraday $\text{Low} \le \text{Close}_{\text{prev}}$.
  * **Gap Down ($\text{Open} < \text{Close}_{\text{prev}}$):** Filled if intraday $\text{High} \ge \text{Close}_{\text{prev}}$.
* **Time-to-Fill:** Elapsed minutes from 08:00 MYT until the first bar touching $\text{Close}_{\text{prev}}$.

#### Maximum Excursions (MFE / MAE)
* **Maximum Favorable Excursion (MFE):**
  $$\text{MFE}_{\%} = \frac{\text{High}_{\text{session}} - \text{Open}_{\text{08:00 MYT}}}{\text{Open}_{\text{08:00 MYT}}} \times 100\%$$
* **Maximum Adverse Excursion (MAE):**
  $$\text{MAE}_{\%} = \frac{\text{Low}_{\text{session}} - \text{Open}_{\text{08:00 MYT}}}{\text{Open}_{\text{08:00 MYT}}} \times 100\%$$

#### Relative Volume (RVOL)
* **Relative Volume for Intraday Slot $t$:**
  $$\text{RVOL}_{d,t} = \frac{\text{Volume}_{d,t}}{\bar{V}_t}$$
  where $\bar{V}_t$ is the historical average volume for that specific time bucket across the analyzed period.
---

## 📈 4. Volume Separation & Instruments

* **Nikkei 225 Index (`^N225`):** Used for Price, Returns, Volatilities, High-Low Ranges, Opening Gaps, and MFE/MAE excursions. (The index itself is a calculated benchmark and has 0 intraday volume in exchange feeds).
* **Tradable TSE ETF Proxy (`1321.T` NEXT FUNDS Nikkei 225 ETF):** Default linked instrument providing authentic Tokyo Stock Exchange intraday trading volume and relative volume.
* **Alternative Instruments:** `1329.T` (iShares Nikkei 225 ETF) and `NKD=F` (CME Nikkei 225 Futures).

---

## 📡 5. Data Coverage & Free Provider Limitations

| Timeframe / Resolution | Free Yahoo Finance History | Primary Research Usage |
| :--- | :--- | :--- |
| **Daily (`1d`)** | **1965 – Present (15,000+ sessions)** | 1Y, 3Y, 5Y, 10Y multi-year day-of-week, opening gaps, seasonality, distributions |
| **60-Minute (`60m`)** | **Up to 730 Days (~2 Years)** | Hourly time-of-day progression profile |
| **5m / 10m / 15m / 30m**| **Up to 60 Days** | High-resolution intraday profile & opening ranges |
| **1-Minute (`1m`)** | **Up to 7 Days** | Ultra-fine opening minute analysis |

> **Custom Offline Datasets:** You can drop custom long-term intraday CSV or Parquet files into `data/raw/` (e.g. `n225_5m.parquet`) and the application will automatically read them.

---

## 📁 6. Project Structure

```text
nikkei225_market_analysis/
│
├── main.py                    # Asynchronous FastAPI application entrypoint & REST API routes
├── requirements.txt           # Pinned production dependency definitions
├── README.md                  # Project documentation & mathematical formulas
├── .gitignore                 # Production Git ignore rules
│
├── config/
│   ├── __init__.py            # Config package marker
│   └── settings.py            # Timezones, TSE session hours (MYT UTC+8), thresholds, symbols
│
├── data/
│   ├── raw/                   # Raw historical downloads and custom offline datasets
│   ├── processed/             # Sanitized and structured session datasets
│   └── cache/                 # Local disk Parquet cache for high-speed retrieval
│
├── engine/
│   ├── __init__.py            # Analytical engine exports
│   ├── calculations.py        # Returns, high-low ranges, gaps, MFE/MAE excursions
│   ├── charts.py              # Interactive dark-themed Plotly figure factory
│   ├── data_cleaner.py        # Anomaly checks, duplicate filtration, diagnostic reporting
│   ├── data_loader.py         # YFinance data provider with Parquet caching & coverage metrics
│   ├── market_sessions.py     # TSE session filtering (08:00–10:30, 11:30–14:30) & lunch exclusion
│   ├── statistics.py          # Empirical quantiles (P10–P90), higher moments, movement frequencies
│   └── timezone_utils.py      # Timezone-aware conversions (JST UTC+9 to MYT UTC+8)
│
├── static/
│   ├── index.html             # Single-Page Application container (6 research modules, 6 KPI cards)
│   ├── css/
│   │   └── dashboard.css      # Institutional dark theme styling (#0e1117 palette) & responsive grid
│   └── js/
│       └── app.js             # Client state store, async fetch pipeline & Plotly.react() controller
│
└── tests/
    ├── __init__.py
    ├── test_timezone.py       # Timezone conversion unit tests
    ├── test_sessions.py       # TSE session filter unit tests
    ├── test_calculations.py   # Return, gap-fill, and excursion unit tests
    └── test_statistics.py     # Statistical and distribution unit tests
```

---

## 🚀 7. Installation & Running

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Automated Unit Tests
```bash
pytest tests/ -v
```

### 3. Launch the FastAPI Application Server
```bash
py -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

*Note: If port 8000 is occupied by another service on your system, launch on port 8001:*
```bash
py -m uvicorn main:app --host 127.0.0.1 --port 8001 --reload
```

### 4. Access the Research Dashboard
Open your web browser and navigate to:
```
http://127.0.0.1:8000
```
*(or `http://127.0.0.1:8001` if running on port 8001)*
