# Real Exchange Rate Simulator

A Streamlit app that builds the bilateral real exchange rate between any two IMF countries (or the Euro area) from monthly IMF CPI and exchange rate data, January 1976 onward.

## Quick start (Python 3.12)

```bash
python3.12 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

The app opens at http://localhost:8501. It needs internet access to `api.imf.org`.

## Economics

| Symbol | Definition |
|---|---|
| S(t) | Units of Country 2 currency per 1 unit of Country 1 currency |
| P1(t), P2(t) | Monthly CPI of Country 1 and Country 2 |
| RER(t) | S(t) × P1(t) / P2(t) |
| RER* | Average of RER(t) over valid months in the selected sample |
| Real Index(t) | 100 × RER(t) / RER* |
| PPP-implied S(t) | RER* × P2(t) / P1(t), the nominal rate that would hold the real rate at its sample average |

IMF rates are local currency per USD, so the app converts them:
S(t) = (Country 2 per USD) / (Country 1 per USD). For the United States the per USD rate is 1.

**Reading the chart.** A Real Index above 100 means Country 1's currency is stronger in real terms than its sample average (its goods are relatively expensive in Country 2 terms). Below 100 means weaker. When nominal S sits below the PPP-implied line, Country 1's currency is overvalued relative to the sample norm, and vice versa. RER* itself has no economic meaning in levels because CPI base years differ; only the index is comparable.

A month is valid only when S, P1 and P2 all exist. RER* averages only valid months, and it is recalculated every time the sample dates change.

## Features

* Country pickers covering IMF members plus the Euro area (`G163`), with a swap button.
* Sample period slider limited to months where both countries have data.
* Chart view: **Real**, **Nominal**, or **Both** (separate y axes). Nominal S is plotted in actual currency units, never normalized.
* Optional log scale for nominal S (on by default when the rate moves more than 20×, common for high inflation economies), and an optional PPP-implied S line.
* Headline metrics: valid months, RER*, latest Real Index, latest S and its change over the sample.
* **Download CSV** with every month in the sample: both per USD rates, S, P1, P2, RER, a validity flag, RER*, Real Index and PPP-implied S.
* Data coverage table showing first and last observation of each series.

## Data source

IMF SDMX 3.0 API, `https://api.imf.org/external/sdmx/3.0`

| Series | Dataflow | Key |
|---|---|---|
| CPI, all items, index | `IMF.STA/CPI` | `{ISO3}.CPI._T.IX.M` |
| Exchange rate, local currency per USD, period average | `IMF.STA/ER` | `{ISO3}.XDC_USD.PA_RT.M` |

Request pattern: `GET {base}/data/dataflow/IMF.STA/{dataflow}/+/{key}` with an SDMX-JSON `Accept` header. The parser also accepts SDMX-ML (XML) responses as a fallback. Responses are cached for 24 hours.

## Data caveats

* **Coverage varies.** Many series start after 1976 and some countries have no monthly CPI or exchange rate. The app shows a warning when a series is missing and leaves gaps in the chart for missing months.
* **Euro adopters.** National series for euro area members may change units at euro adoption. Use Euro area (`G163`) for post-1999 analysis; its data starts later than 1976.
* **Currency redenominations.** The IMF generally restates history in the current currency unit (for example Brazil before the real), so very small early values are expected. Currency codes in the app labels are current codes.
* **Dollarized economies.** If the IMF has no rate for a country whose currency is USD, the app uses 1 per USD and says so.

## Files

* `app.py`: the Streamlit app (data access, calculations, UI)
* `requirements.txt`: dependencies
* `README.md`: this file
