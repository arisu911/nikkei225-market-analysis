# Nikkei 225 Market Microstructure & Quantitative Research Dashboard

[![Python](https://img.shields.io/badge/Python-3.14%2B-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Plotly.js](https://img.shields.io/badge/Plotly.js-2.35.2-3F4F75.svg?logo=plotly&logoColor=white)](https://plotly.com/javascript/)
[![Vanilla ES6](https://img.shields.io/badge/Frontend-Vanilla%20ES6%20%2B%20CSS3-F7DF1E.svg?logo=javascript&logoColor=black)](https://developer.mozilla.org/en-US/docs/Web/JavaScript)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An institutional-grade, asynchronous quantitative research platform dedicated to the empirical study of Tokyo Stock Exchange (TSE) cash equity dynamics, price dispersion, intraday volatility regimes, and auction gap structures for the **Nikkei 225 Stock Average (`^N225`)**.

---

## 1. Executive Summary

The **Nikkei 225 Quantitative Research Dashboard** provides statistical and empirical microstructural analysis of Japan's benchmark equity index. Rather than offering predictive trade signals or speculative recommendations, this platform delivers descriptive quantitative profiles across multi-year lookbacks, examining:

- Realized session price dispersion and non-parametric quantile behavior.
- Day-of-week structural anomalies and multi-year calendar seasonality.
- Cash open auction price gaps, mean-reverting gap-fill frequencies, and time-to-fill dynamics.
- Morning versus Afternoon session variance, volume distributions, and high-low range expansion ratios.
- Intraday Maximum Favorable Excursion (**MFE**) and Maximum Adverse Excursion (**MAE**) paths measured from the cash market open.

### Session Schedule & Timezone Normalization

All timestamps across API endpoints, data pipelines, charts, and table displays are strictly normalized to **Malaysia Time (MYT, UTC+8)**, representing a -1 hour translation from Japan Standard Time (JST, UTC+9). The standard 60-minute Tokyo Stock Exchange lunch break is formally masked and excluded from all continuous intraday return and volatility series:

| TSE Session Segment | Japan Standard Time (JST, UTC+9) | Display Timezone (MYT, UTC+8) | Microstructural Classification |
| :--- | :---: | :---: | :--- |
| **Morning Session (Zenba)** | 09:00 – 11:30 JST | **08:00 – 10:30 MYT** | Continuous cash auction; high liquidity, price discovery, and volatility. |
| **Lunch Break** | 11:30 – 12:30 JST | **10:30 – 11:30 MYT** | **Strictly Masked & Excluded**; zero trading on cash equities. |
| **Afternoon Session (Goba)** | 12:30 – 15:30 JST | **11:30 – 14:30 MYT** | Re-open auction, institutional rebalancing, and cash settlement close. |

---

## 2. Core Quantitative Research Modules

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        NIKKEI 225 QUANTITATIVE RESEARCH ENGINE                        │
├───────────────────────┬─────────────────────────┬──────────────────────────────────────┤
│ 01. Market Overview   │ 02. Day-of-Week         │ 03. Intraday Profile                 │
│ • Cumulative Paths    │ • Mon–Fri Stats         │ • 15m/30m Time Windows               │
│ • Annual Performance  │ • Timeslot Heatmaps     │ • Morning vs Afternoon Volatility    │
│ • Monthly Seasonality │ • Distribution Boxplots │ • Pos/Neg Progression Frequency      │
├───────────────────────┼─────────────────────────┼──────────────────────────────────────┤
│ 04. Opening & Gaps    │ 05. Volatility & Path   │ 06. Distributions                    │
│ • 08:00 MYT Cash Gaps │ • Rolling Vol (20/60/120│ • Parametric & Non-Parametric Stats  │
│ • Fill Frequencies    │ • Morning vs Afternoon  │ • Directional Probability Tables     │
│ • 5/15/30/60m Ranges  │ • MFE vs MAE Excursions │ • Threshold Move Frequencies         │
└───────────────────────┴─────────────────────────┴──────────────────────────────────────┘
```

### Module 1: Market Overview & Seasonality
- **Cumulative Performance Path:** Normalized session price progression across user-selectable periods (`1Y`, `3Y`, `5Y`, `10Y`).
- **Calendar-Year Summary:** Tabular breakdown of annual cumulative return, mean daily return, daily session volatility, annualized volatility ($\sigma \times \sqrt{250}$), maximum peak-to-trough drawdown, and trading session sample count ($n$).
- **Monthly Seasonality Matrix:** Month-by-month historical returns (January through December), median returns, price dispersion, and positive-close probability.

### Module 2: Day-of-Week Behavior (Monday – Friday)
- **Weekday Comparative Metrics:** Descriptive return and high-low range statistics broken down across individual weekdays.
- **Dispersion & Outlier Analysis:** Multi-trace boxplots highlighting interquartile ranges (IQR), median return skew, and tail occurrences for each trading day.
- **Timeslot Heatmap Matrix:** Two-dimensional color-mapped density grid visualizing mean percentage returns across specific intraday intervals against each day of the week.

### Module 3: Intraday Time-of-Day Profile
- **Sub-Session Time Buckets:** Multi-panel progression charts tracking Average Return, Median Return, Volatility (Standard Deviation of returns), High-Low Range, and Positive vs. Negative bar ratios across standard 5m, 15m, and 30m windows.
- **Session Segmentation:** Granular breakdown separating the opening rush (08:00–08:30 MYT), morning consolidation, afternoon re-opening (11:30 MYT), and pre-close institutional market-on-close (MOC) flows.

### Module 4: Opening Behavior & Gap Analysis (08:00 MYT / 09:00 JST)
- **Cash Gap Identification:** Quantifies the auction price gap between the previous TSE cash close and the current 08:00 MYT cash open.
- **Directional Gap Regimes:** Segregates gaps into Gap Up, Gap Down, and Flat conditions with parametric distribution histograms.
- **Empirical Gap-Fill Probability:** Measures the historical frequency with which an opening gap is touched or closed during the subsequent regular session, alongside time-to-fill duration distributions.
- **Opening Range Expansion:** Computes 5-minute, 15-minute, 30-minute, and 60-minute opening ranges, calculating their average percentage ratio relative to the full-day high-low envelope.

### Module 5: Volatility & Excursion Path Analysis (MFE / MAE)
- **Multi-Window Rolling Volatility:** 20-session (1-month), 60-session (1-quarter), and 120-session (semi-annual) annualized realized historical volatility.
- **Morning vs. Afternoon Segment Comparison:** Parametric and non-parametric comparison of price discovery in the 2.5-hour morning session versus the 3.0-hour afternoon session.
- **Maximum Favorable / Adverse Excursion (MFE/MAE):** Evaluates the maximum peak run-up (`High - Open`) and maximum adverse draw-down (`Low - Open`) from the 08:00 MYT open, rendered via two-dimensional color-coded scatter matrices and empirical histograms.

### Module 6: Statistical Distributions & Movement Frequencies
- **Empirical Quantile Breakdown:** Comprehensive descriptive table covering Mean, Median, Standard Deviation, Skewness, Excess Kurtosis, and percentile markers ($P_{10}, P_{25}, P_{50}, P_{75}, P_{90}$) for Session Returns, Absolute Moves, and Daily High-Low Ranges.
- **Historical Occurrence Frequencies:** Empirical probability tables categorizing positive sessions ($>0\%$), negative sessions ($<0\%$), flat sessions ($=0\%$), absolute movement thresholds ($>0.25\%, >0.50\%, >0.75\%, >1.00\%, >1.50\%, >2.00\%$), and range expansion thresholds ($\ge 0.50\%, \ge 0.75\%, \ge 1.00\%, \ge 1.50\%, \ge 2.00\%$).

---

## 3. System Architecture & Technology Stack

The platform is built as a zero-framework, decoupled web application pairing an asynchronous Python backend with a high-performance Vanilla ES6 frontend.

```
┌────────────────────────────────────────────────────────┐
│                   BROWSER CLIENT                      │
│  Vanilla HTML5 + Modern CSS Grid + Vanilla ES6 JS      │
│  • DOM State Store & Route Manager                     │
│  • Asynchronous Fetch Pipeline                         │
│  • Non-destructive Canvas Updates via Plotly.react()   │
└───────────────────────────▲────────────────────────────┘
                            │  JSON REST Payloads
                            │  (Headless Serialization)
┌───────────────────────────▼────────────────────────────┐
│                  FASTAPI BACKEND                      │
│  • In-Memory Quantitative Data Caching Engine          │
│  • Strict NaN/Inf/Timestamp Sanitization Pipeline      │
│  • Static File Mount (/static -> CSS/JS/HTML)          │
└───────────────────────────▲────────────────────────────┘
                            │  In-Memory DataFrames
┌───────────────────────────▼────────────────────────────┐
│                 ENGINE PACKAGE (engine/)               │
│  • calculations.py : Mathematical & Excursion Core     │
│  • market_sessions.py : TSE Window & Masking Logic     │
│  • statistics.py   : Quantiles, Skew, Kurtosis, Freq   │
│  • charts.py       : Dark Themed Plotly Figure Factory │
│  • data_loader.py  : Parquet Cache & Pipeline          │
└────────────────────────────────────────────────────────┘
```

- **Backend:** [FastAPI](https://fastapi.tiangolo.com/) served by [Uvicorn](https://www.uvicorn.org/). Numerical computations are executed in pure [NumPy](https://numpy.org/), [Pandas](https://pandas.pydata.org/), and [SciPy](https://scipy.org/). Interactive charts are produced via [Plotly](https://plotly.com/python/) and serialized directly to JSON, keeping figure schemas decoupled from frontend templates.
- **Frontend:** Zero bloated UI frameworks (no React, no Vue, no Tailwind). Built with standard HTML5 semantic elements, Vanilla CSS using institutional dark palettes (`#0e1117`, `#161b22`, `#21262d`), and ES6 JavaScript utilizing `Plotly.react()` for non-destructive canvas re-renders without full-page reloads.

---

## 4. Directory Structure

```
Nikkei225_MKT_ANALYSIS/web/
├── .gitignore               # Production git exclusion definitions
├── README.md                # Institutional documentation (this file)
├── main.py                  # Asynchronous FastAPI application entrypoint & REST endpoints
├── requirements.txt         # Pinned production dependency definitions
├── config/
│   ├── __init__.py          # Config package marker
│   └── settings.py          # Session hours, timezone constants, paths, and thresholds
├── data/
│   ├── cache/               # Parquet dataset storage with cached intraday & daily bars
│   │   ├── .gitkeep
│   │   └── *.parquet
│   ├── processed/           # Sanitized session datasets
│   │   └── .gitkeep
│   └── raw/                 # Original market feeds
│       └── .gitkeep
├── engine/
│   ├── __init__.py          # Analytical package exports
│   ├── calculations.py      # Quantitative routines (returns, ranges, gaps, MFE/MAE)
│   ├── charts.py            # Dark-themed Plotly chart generator factory
│   ├── data_cleaner.py      # Anomaly filtration, deduplication, and sanity checking
│   ├── data_loader.py       # Local parquet caching and market feed provider
│   ├── market_sessions.py   # TSE session classification and 10:30–11:30 lunch break masking
│   ├── statistics.py        # Quantiles, higher moments, frequencies, and aggregations
│   └── timezone_utils.py    # UTC/JST to MYT conversion utilities
└── static/
    ├── index.html           # Semantic Single-Page Application container
    ├── css/
    │   └── dashboard.css    # Institutional dark theme styling and responsive grid layout
    └── js/
        └── app.js           # Client-side state manager, async fetcher, and Plotly controller
```

---

## 5. REST API Documentation

All data endpoints accept HTTP `GET` requests and return sanitized JSON responses. `NaN`, `+Infinity`, and `-Infinity` values are sanitized to `null` to comply with strict JSON standards.

### Endpoints Overview

| Method | Endpoint | Description | Primary Query Parameters |
| :---: | :--- | :--- | :--- |
| `GET` | `/` | Serves the Single-Page Application UI | None |
| `GET` | `/api/metadata` | Dataset coverage, session parameters, and instrument metadata | `period`, `resolution`, `weekday`, `instrument` |
| `GET` | `/api/overview/metrics` | Hydrates top KPI cards (Mean Return, Median, Volatility, Range) | `period`, `resolution`, `weekday`, `instrument` |
| `GET` | `/api/overview/cumulative-chart` | Returns serialized Plotly figure of cumulative return paths | `period`, `resolution`, `weekday`, `instrument` |
| `GET` | `/api/overview/seasonality` | Returns annual summary and monthly seasonality datasets | `period`, `resolution`, `weekday`, `instrument` |
| `GET` | `/api/weekday/analysis` | Weekday comparison charts, distribution boxplots, and heatmaps | `period`, `resolution`, `weekday`, `instrument` |
| `GET` | `/api/weekday/table` | Tabular statistical summary across individual weekdays | `period`, `resolution`, `weekday`, `instrument` |
| `GET` | `/api/intraday/profile` | 4-panel intraday progression chart and time bucket summary table | `period`, `resolution`, `weekday`, `instrument` |
| `GET` | `/api/gaps/analysis` | Gap distributions, gap fill rate chart, and opening range tables | `period`, `resolution`, `weekday`, `instrument` |
| `GET` | `/api/volatility/excursions` | Rolling vol, Morning vs. Afternoon comparison, MFE/MAE scatter | `period`, `resolution`, `weekday`, `instrument` |
| `GET` | `/api/distributions/quantiles` | Full empirical quantile breakdown, histograms, and frequency tables | `period`, `resolution`, `weekday`, `instrument` |
| `POST`| `/api/refresh` | Force clears the in-memory backend market data cache | None |

### Standard Query Parameters

- `period` *(string, default: `"5Y"`)*: Historical sample window. Supported options: `"1Y"`, `"3Y"`, `"5Y"`, `"10Y"`, `"max"`.
- `resolution` *(string, default: `"15m"`)*: Intraday bar interval. Supported options: `"5m"`, `"15m"`, `"30m"`, `"60m"`.
- `weekday` *(string, default: `"All"`)*: Day-of-week filter. Supported options: `"All"`, `"Monday"`, `"Tuesday"`, `"Wednesday"`, `"Thursday"`, `"Friday"`.
- `instrument` *(string, default: `"1321.T"`)*: Tradable proxy ticker. Supported options: `"1321.T"`, `"1329.T"`, `"NKD=F"`.
- `force_reload` *(boolean, default: `false`)*: Forces data re-extraction bypassing the parquet cache.

---

## 6. Installation & Execution Guide

### Prerequisites
- Python 3.10, 3.11, 3.12, 3.13, or 3.14+
- Modern Web Browser (Microsoft Edge, Google Chrome, Mozilla Firefox, or Safari)

### Step 1: Navigate to the Web Workspace
Open a terminal (PowerShell, Command Prompt, or Bash) and navigate to the `web` application directory:
```bash
cd C:\Users\HP\Documents\Nikkei225_MKT_ANALYSIS\web
```

### Step 2: Install Dependencies
Install all required libraries specified in `requirements.txt`:
```bash
pip install -r requirements.txt
```

### Step 3: Launch the Production Application Server
Start the Uvicorn server hosting the FastAPI application:
```bash
py -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```
*Note: If port 8000 is occupied by an external service, bind to an alternate port such as `8001`:*
```bash
py -m uvicorn main:app --host 127.0.0.1 --port 8001 --reload
```

### Step 4: Access the Dashboard
Open your web browser and navigate to:
```
http://127.0.0.1:8000
```
*(or `http://127.0.0.1:8001` if running on port 8001)*

---

## 7. Quantitative Methodology & Institutional Disclaimers

### Volume Proxy Selection (NEXT FUNDS Nikkei 225 ETF - TSE: 1321)
The primary cash index (`^N225`) is an arithmetic price-weighted average and does not record continuous transactional share volume. To perform empirical Relative Volume (RVOL), volume-weighted profile studies, and morning-versus-afternoon liquidity comparisons, this platform links the cash index to Japan's premier tradable index ETF: **NEXT FUNDS Nikkei 225 Exchange Traded Fund (TSE: 1321.T)** managed by Nomura Asset Management.

### Lunch Break Masking Methodology
Continuous price discovery on the Tokyo Stock Exchange pauses between 11:30 JST (10:30 MYT) and 12:30 JST (11:30 MYT). Intraday bar metrics treat the 10:30 MYT morning close and the 11:30 MYT afternoon re-open as adjacent trading intervals for rolling window calculations, preventing artificial zero-volume and flat-line variance contamination during the lunch recess.

### Institutional Disclaimer
> **RESEARCH AND EDUCATIONAL USE ONLY**  
> This platform and its quantitative outputs are provided exclusively for academic research, financial modeling, and empirical market microstructure education. None of the statistical frequencies, quantile breakdowns, excursion paths, or metrics displayed constitute financial advice, investment recommendations, or trade endorsements. Past empirical behavior does not guarantee future market outcomes.
