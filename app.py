"""Real Exchange Rate Simulator.

Pulls monthly CPI and exchange-rate data from the IMF SDMX 3.0 API and computes
the bilateral real exchange rate between two countries:

    S(t)   = units of Country 2 currency per 1 unit of Country 1 currency
    RER(t) = S(t) * P1(t) / P2(t)
    RER*   = mean of RER(t) over valid months in the selected sample
    Real Index(t) = 100 * RER(t) / RER*

Run with:  streamlit run app.py
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
from plotly.subplots import make_subplots

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
BASE_URL = "https://api.imf.org/external/sdmx/3.0"
AGENCY = "IMF.STA"
START = pd.Period("1976-01", freq="M")
EURO_AREA = "G163"
REAL_COLOR = "#2563eb"
NOMINAL_COLOR = "#ea580c"
PPP_COLOR = "#9ca3af"

# ISO3 | name | current currency code. IMF members plus the Euro area aggregate.
_COUNTRY_TABLE = """
AFG|Afghanistan|AFN
ALB|Albania|ALL
DZA|Algeria|DZD
AND|Andorra|EUR
AGO|Angola|AOA
ATG|Antigua and Barbuda|XCD
ARG|Argentina|ARS
ARM|Armenia|AMD
ABW|Aruba|AWG
AUS|Australia|AUD
AUT|Austria|EUR
AZE|Azerbaijan|AZN
BHS|Bahamas|BSD
BHR|Bahrain|BHD
BGD|Bangladesh|BDT
BRB|Barbados|BBD
BLR|Belarus|BYN
BEL|Belgium|EUR
BLZ|Belize|BZD
BEN|Benin|XOF
BTN|Bhutan|BTN
BOL|Bolivia|BOB
BIH|Bosnia and Herzegovina|BAM
BWA|Botswana|BWP
BRA|Brazil|BRL
BRN|Brunei Darussalam|BND
BGR|Bulgaria|EUR
BFA|Burkina Faso|XOF
BDI|Burundi|BIF
CPV|Cabo Verde|CVE
KHM|Cambodia|KHR
CMR|Cameroon|XAF
CAN|Canada|CAD
CAF|Central African Republic|XAF
TCD|Chad|XAF
CHL|Chile|CLP
CHN|China|CNY
COL|Colombia|COP
COM|Comoros|KMF
COD|Congo, Dem. Rep.|CDF
COG|Congo, Rep.|XAF
CRI|Costa Rica|CRC
CIV|Côte d'Ivoire|XOF
HRV|Croatia|EUR
CYP|Cyprus|EUR
CZE|Czech Republic|CZK
DNK|Denmark|DKK
DJI|Djibouti|DJF
DMA|Dominica|XCD
DOM|Dominican Republic|DOP
ECU|Ecuador|USD
EGY|Egypt|EGP
SLV|El Salvador|USD
GNQ|Equatorial Guinea|XAF
ERI|Eritrea|ERN
EST|Estonia|EUR
SWZ|Eswatini|SZL
ETH|Ethiopia|ETB
G163|Euro area|EUR
FJI|Fiji|FJD
FIN|Finland|EUR
FRA|France|EUR
GAB|Gabon|XAF
GMB|Gambia|GMD
GEO|Georgia|GEL
DEU|Germany|EUR
GHA|Ghana|GHS
GRC|Greece|EUR
GRD|Grenada|XCD
GTM|Guatemala|GTQ
GIN|Guinea|GNF
GNB|Guinea-Bissau|XOF
GUY|Guyana|GYD
HTI|Haiti|HTG
HND|Honduras|HNL
HKG|Hong Kong SAR|HKD
HUN|Hungary|HUF
ISL|Iceland|ISK
IND|India|INR
IDN|Indonesia|IDR
IRN|Iran|IRR
IRQ|Iraq|IQD
IRL|Ireland|EUR
ISR|Israel|ILS
ITA|Italy|EUR
JAM|Jamaica|JMD
JPN|Japan|JPY
JOR|Jordan|JOD
KAZ|Kazakhstan|KZT
KEN|Kenya|KES
KIR|Kiribati|AUD
KOR|Korea|KRW
KWT|Kuwait|KWD
KGZ|Kyrgyz Republic|KGS
LAO|Lao P.D.R.|LAK
LVA|Latvia|EUR
LBN|Lebanon|LBP
LSO|Lesotho|LSL
LBR|Liberia|LRD
LBY|Libya|LYD
LIE|Liechtenstein|CHF
LTU|Lithuania|EUR
LUX|Luxembourg|EUR
MAC|Macao SAR|MOP
MDG|Madagascar|MGA
MWI|Malawi|MWK
MYS|Malaysia|MYR
MDV|Maldives|MVR
MLI|Mali|XOF
MLT|Malta|EUR
MHL|Marshall Islands|USD
MRT|Mauritania|MRU
MUS|Mauritius|MUR
MEX|Mexico|MXN
FSM|Micronesia|USD
MDA|Moldova|MDL
MNG|Mongolia|MNT
MNE|Montenegro|EUR
MAR|Morocco|MAD
MOZ|Mozambique|MZN
MMR|Myanmar|MMK
NAM|Namibia|NAD
NRU|Nauru|AUD
NPL|Nepal|NPR
NLD|Netherlands|EUR
NZL|New Zealand|NZD
NIC|Nicaragua|NIO
NER|Niger|XOF
NGA|Nigeria|NGN
MKD|North Macedonia|MKD
NOR|Norway|NOK
OMN|Oman|OMR
PAK|Pakistan|PKR
PLW|Palau|USD
PAN|Panama|PAB
PNG|Papua New Guinea|PGK
PRY|Paraguay|PYG
PER|Peru|PEN
PHL|Philippines|PHP
POL|Poland|PLN
PRT|Portugal|EUR
QAT|Qatar|QAR
ROU|Romania|RON
RUS|Russia|RUB
RWA|Rwanda|RWF
WSM|Samoa|WST
SMR|San Marino|EUR
STP|São Tomé and Príncipe|STN
SAU|Saudi Arabia|SAR
SEN|Senegal|XOF
SRB|Serbia|RSD
SYC|Seychelles|SCR
SLE|Sierra Leone|SLE
SGP|Singapore|SGD
SVK|Slovak Republic|EUR
SVN|Slovenia|EUR
SLB|Solomon Islands|SBD
SOM|Somalia|SOS
ZAF|South Africa|ZAR
SSD|South Sudan|SSP
ESP|Spain|EUR
LKA|Sri Lanka|LKR
KNA|St. Kitts and Nevis|XCD
LCA|St. Lucia|XCD
VCT|St. Vincent and the Grenadines|XCD
SDN|Sudan|SDG
SUR|Suriname|SRD
SWE|Sweden|SEK
CHE|Switzerland|CHF
SYR|Syria|SYP
TJK|Tajikistan|TJS
TZA|Tanzania|TZS
THA|Thailand|THB
TLS|Timor-Leste|USD
TGO|Togo|XOF
TON|Tonga|TOP
TTO|Trinidad and Tobago|TTD
TUN|Tunisia|TND
TUR|Türkiye|TRY
TKM|Turkmenistan|TMT
TUV|Tuvalu|AUD
UGA|Uganda|UGX
UKR|Ukraine|UAH
ARE|United Arab Emirates|AED
GBR|United Kingdom|GBP
USA|United States|USD
URY|Uruguay|UYU
UZB|Uzbekistan|UZS
VUT|Vanuatu|VUV
VEN|Venezuela|VES
VNM|Vietnam|VND
YEM|Yemen|YER
ZMB|Zambia|ZMW
ZWE|Zimbabwe|ZWG
"""

COUNTRIES: dict[str, tuple[str, str]] = {
    iso: (name, cur)
    for iso, name, cur in (
        line.split("|") for line in _COUNTRY_TABLE.strip().splitlines()
    )
}
COUNTRY_CODES = sorted(COUNTRIES, key=lambda c: COUNTRIES[c][0])
# Countries that adopted the euro: their national series may change units at adoption.
EURO_MEMBERS = {
    "AUT", "BEL", "BGR", "HRV", "CYP", "EST", "FIN", "FRA", "DEU", "GRC", "IRL",
    "ITA", "LVA", "LTU", "LUX", "MLT", "NLD", "PRT", "SVK", "SVN", "ESP",
}


def country_label(iso: str) -> str:
    name, cur = COUNTRIES[iso]
    return f"{name} · {cur}"


def currency(iso: str) -> str:
    return COUNTRIES[iso][1]


# --------------------------------------------------------------------------- #
# IMF data access
# --------------------------------------------------------------------------- #
_PERIOD_RE = re.compile(r"^(\d{4})-?M?(\d{1,2})$")


def _to_period(value: object) -> pd.Period | None:
    """Parse IMF monthly periods such as '1976-M01', '1976M01' or '1976-01'."""
    match = _PERIOD_RE.match(str(value).strip())
    if not match:
        return None
    year, month = int(match.group(1)), int(match.group(2))
    if not 1 <= month <= 12:
        return None
    return pd.Period(year=year, month=month, freq="M")


def _series_from_pairs(pairs) -> pd.Series:
    """Build a clean monthly series (positive, finite, from 1976-01 onward)."""
    data: dict[pd.Period, float] = {}
    for period, raw in pairs:
        p = _to_period(period)
        try:
            x = float(raw)
        except (TypeError, ValueError):
            continue
        if p is not None and p >= START and np.isfinite(x) and x > 0:
            data[p] = x
    if not data:
        return pd.Series(dtype=float)
    s = pd.Series(data, dtype=float).sort_index()
    s.index = pd.PeriodIndex(s.index, freq="M")
    return s


def _parse_sdmx_json(payload: dict) -> pd.Series:
    """Parse SDMX-JSON (2.0 or 1.0). Returns the longest series in the message."""
    data = payload.get("data", payload)
    structures = data.get("structures") or [data.get("structure", {})]
    obs_dims = structures[0]["dimensions"].get("observation", [])
    time_dim = next((d for d in obs_dims if d.get("id") == "TIME_PERIOD"), None)
    if time_dim is None:
        raise ValueError("No TIME_PERIOD dimension in response")
    times = [v.get("value", v.get("id")) for v in time_dim["values"]]

    best = pd.Series(dtype=float)
    for dataset in data.get("dataSets", []):
        for series in (dataset.get("series") or {}).values():
            pairs = []
            for key, obs in (series.get("observations") or {}).items():
                value = obs[0] if isinstance(obs, list) and obs else obs
                pairs.append((times[int(str(key).split(":")[-1])], value))
            s = _series_from_pairs(pairs)
            if len(s) > len(best):
                best = s
    return best


def _parse_sdmx_xml(text: str) -> pd.Series:
    """Fallback parser for SDMX-ML (structure-specific or generic)."""
    root = ET.fromstring(text)
    pairs = []
    for el in root.iter():
        if not el.tag.endswith("Obs"):
            continue
        if el.get("TIME_PERIOD") is not None:  # structure-specific
            pairs.append((el.get("TIME_PERIOD"), el.get("OBS_VALUE")))
            continue
        period = value = None  # generic
        for child in el:
            if child.tag.endswith("ObsDimension"):
                period = child.get("value")
            elif child.tag.endswith("ObsValue"):
                value = child.get("value")
        pairs.append((period, value))
    return _series_from_pairs(pairs)


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def fetch_series(dataflow: str, key: str) -> pd.Series:
    """Fetch one IMF monthly series. Empty series means 'no data for this key'."""
    url = f"{BASE_URL}/data/dataflow/{AGENCY}/{dataflow}/+/{key}"
    headers = {
        "Accept": "application/vnd.sdmx.data+json;version=2.0.0",
        "User-Agent": "rer-simulator/1.0",
    }
    resp = requests.get(url, headers=headers, timeout=60)
    if resp.status_code in (204, 404):
        return pd.Series(dtype=float)
    resp.raise_for_status()
    try:
        return _parse_sdmx_json(resp.json())
    except Exception:  # not JSON or unexpected shape: try SDMX-ML
        try:
            return _parse_sdmx_xml(resp.text)
        except ET.ParseError as exc:
            raise RuntimeError(f"Unrecognized IMF response for {key}") from exc


def _ones_until_now() -> pd.Series:
    idx = pd.period_range(START, pd.Period.now("M"), freq="M")
    return pd.Series(1.0, index=idx)


def load_country(iso: str) -> tuple[pd.Series, pd.Series, list[str]]:
    """Return (local currency per USD, CPI, notes) for one country."""
    notes: list[str] = []
    cpi = fetch_series("CPI", f"{iso}.CPI._T.IX.M")
    if iso == "USA":
        fx = _ones_until_now()
    else:
        fx = fetch_series("ER", f"{iso}.XDC_USD.PA_RT.M")
        if fx.empty and currency(iso) == "USD":
            fx = _ones_until_now()
            notes.append(f"{COUNTRIES[iso][0]} uses USD; exchange rate set to 1 per USD.")
    return fx, cpi, notes


def build_frame(fx1: pd.Series, p1: pd.Series,
                fx2: pd.Series, p2: pd.Series) -> pd.DataFrame:
    df =pd.DataFrame({"fx1": fx1, "fx2": fx2, "P1": p1, "P2": p2})
    if df.empty:
        return df
    df = df.reindex(pd.period_range(df.index.min(), df.index.max(), freq="M"))
    df["S"] = df["fx2"] / df["fx1"]  # (C2 per USD) / (C1 per USD) = C2 per C1
    df["RER"] = df["S"] * df["P1"] / df["P2"]
    return df


# --------------------------------------------------------------------------- #
# Presentation helpers
# --------------------------------------------------------------------------- #
def fmt(x: float) -> str:
    if not np.isfinite(x):
        return "n/a"
    ax = abs(x)
    if ax >= 1000:
        return f"{x:,.0f}"
    if ax >= 1:
        return f"{x:,.2f}"
    return f"{x:.4g}"


def make_chart(sub: pd.DataFrame, view: str, c1: str, c2: str,
               log_nominal: bool, show_ppp: bool) -> go.Figure:
    x = sub.index.to_timestamp()
    unit = f"{currency(c2)} per {currency(c1)}"
    both = view == "Both"
    fig = make_subplots(specs=[[{"secondary_y": both}]])

    if view in ("Real", "Both"):
        fig.add_trace(
            go.Scatter(x=x, y=sub["real_index"], name="Real index (sample avg = 100)",
                       line=dict(color=REAL_COLOR, width=2),
                       hovertemplate="%{y:.1f}<extra>Real index</extra>"),
            secondary_y=False,
        )
        fig.add_hline(y=100, line_dash="dot", line_color=PPP_COLOR, line_width=1)
        fig.update_yaxes(title_text="Real index (avg = 100)", secondary_y=False,
                         title_font_color=REAL_COLOR if both else None)

    if view in ("Nominal", "Both"):
        fig.add_trace(
            go.Scatter(x=x, y=sub["S"], name=f"Nominal S ({unit})",
                       line=dict(color=NOMINAL_COLOR, width=2),
                       hovertemplate="%{y:,.4g}<extra>S</extra>"),
            secondary_y=both,
        )
        if show_ppp:
            fig.add_trace(
                go.Scatter(x=x, y=sub["ppp_S"], name="PPP-implied S (RER at average)",
                           line=dict(color=PPP_COLOR, width=1.5, dash="dash"),
                           hovertemplate="%{y:,.4g}<extra>PPP-implied S</extra>"),
                secondary_y=both,
            )
        fig.update_yaxes(title_text=unit, secondary_y=both,
                         type="log" if log_nominal else "linear",
                         title_font_color=NOMINAL_COLOR if both else None,
                         showgrid=not both)

    fig.update_layout(
        height=460, template="plotly_white", hovermode="x unified",
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )
    return fig


def export_frame(sub: pd.DataFrame, c1: str, c2: str, rer_star: float) -> pd.DataFrame:
    k1, k2 = currency(c1), currency(c2)
    out = pd.DataFrame({
        "month": sub.index.strftime("%Y-%m"),
        f"{c1}_{k1}_per_USD": sub["fx1"],
        f"{c2}_{k2}_per_USD": sub["fx2"],
        f"S_{k2}_per_{k1}": sub["S"],
        f"P1_CPI_{c1}": sub["P1"],
        f"P2_CPI_{c2}": sub["P2"],
        "RER": sub["RER"],
        "valid_month": sub["RER"].notna(),
        "RER_star": rer_star,
        "real_index": sub["real_index"],
        f"PPP_implied_S_{k2}_per_{k1}": sub["ppp_S"],
    })
    return out.reset_index(drop=True)


def swap_countries() -> None:
    st.session_state.c1, st.session_state.c2 = st.session_state.c2, st.session_state.c1


# --------------------------------------------------------------------------- #
# App
# --------------------------------------------------------------------------- #
def main() -> None:
    st.set_page_config(page_title="Real Exchange Rate Simulator", page_icon="💱",
                       layout="wide")
    st.title("Real Exchange Rate Simulator")
    st.caption("Monthly IMF CPI and exchange-rate data, January 1976 onward. "
               "RER(t) = S(t) × P1(t) / P2(t), where S is Country 2 currency per "
               "1 unit of Country 1 currency.")

    st.session_state.setdefault("c1", "USA")
    st.session_state.setdefault("c2", "JPN")

    col1, col_swap, col2 = st.columns([10, 1, 10], vertical_alignment="bottom")
    c1 = col1.selectbox("Country 1 (base currency)", COUNTRY_CODES,
                        format_func=country_label, key="c1")
    col_swap.button("⇄", on_click=swap_countries, help="Swap countries",
                    width="stretch")
    c2 = col2.selectbox("Country 2 (quote currency)", COUNTRY_CODES,
                        format_func=country_label, key="c2")

    if c1 == c2:
        st.info("Pick two different countries to compare.")
        return

    try:
        with st.spinner("Fetching IMF data…"):
            fx1, p1, n1 = load_country(c1)
            fx2, p2, n2 = load_country(c2)
    except Exception as exc:  # network or API failure
        st.error(f"Could not retrieve IMF data: {exc}. Please try again shortly.")
        return

    for note in n1 + n2:
        st.caption(f"ℹ️ {note}")
    for iso in (c1, c2):
        if iso in EURO_MEMBERS:
            st.caption(f"ℹ️ {COUNTRIES[iso][0]} is a euro adopter; its national series may "
                       "change currency units at adoption. Euro area (G163) is cleaner "
                       "for post-1999 work.")

    missing = [f"{COUNTRIES[iso][0]} {what}"
               for iso, fx, cpi in ((c1, fx1, p1), (c2, fx2, p2))
               for what, s in (("exchange rate", fx), ("CPI", cpi)) if s.empty]
    if missing:
        st.warning("The IMF has no monthly data for: " + ", ".join(missing) + ".")
        return

    df = build_frame(fx1, p1, fx2, p2)

    valid = df.index[df["RER"].notna()]
    if valid.empty:
        st.warning("The two countries' series do not overlap in any month.")
        return

    months = [str(p) for p in pd.period_range(valid.min(), valid.max(), freq="M")]
    start_s, end_s = st.select_slider(
        "Sample period (RER* is the average over valid months in this window)",
        options=months, value=(months[0], months[-1]), key=f"range_{c1}_{c2}",
    )
    start, end = pd.Period(start_s, "M"), pd.Period(end_s, "M")
    if start >= end:
        st.info("Choose a sample of at least two months.")
        return

    sub = df.loc[start:end].copy()
    rer_star = sub["RER"].mean()  # skips missing months
    sub["real_index"] = 100 * sub["RER"] / rer_star
    sub["ppp_S"] = rer_star * sub["P2"] / sub["P1"]
    n_valid = int(sub["RER"].notna().sum())

    s_valid = sub["S"].dropna()
    ratio = s_valid.max() / s_valid.min() if len(s_valid) else 1.0

    o1, o2, o3 = st.columns([3, 2, 2])
    view = o1.radio("Show", ["Real", "Nominal", "Both"], index=2, horizontal=True)
    log_nominal = o2.checkbox("Log scale for nominal S", value=bool(ratio > 20),
                              key=f"log_{c1}_{c2}", disabled=view == "Real")
    show_ppp = o3.checkbox("PPP-implied S", value=True, disabled=view == "Real",
                           help="RER* × P2/P1: the nominal rate that would keep the "
                                "real rate at its sample average.")

    last = sub["RER"].last_valid_index()
    last_idx = sub.at[last, "real_index"]
    first_s, last_s = s_valid.iloc[0], s_valid.iloc[-1]
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Valid months", f"{n_valid} / {len(sub)}")
    m2.metric("RER*", fmt(rer_star),
              help="Average of S×P1/P2. Its level depends on CPI base years; "
                   "only the index is economically comparable.")
    m3.metric(f"Real index, {last}", f"{last_idx:.1f}",
              f"{last_idx - 100:+.1f}% vs sample avg", delta_color="off")
    m4.metric(f"Nominal S, {s_valid.index[-1]}", fmt(last_s),
              f"{(last_s / first_s - 1) * 100:+,.1f}% over sample", delta_color="off")

    st.plotly_chart(make_chart(sub, view, c1, c2, log_nominal, show_ppp),
                    width="stretch")
    name1 = COUNTRIES[c1][0]
    st.caption(f"Real index above 100: {name1}'s currency is stronger in real terms than "
               f"its sample average (its goods are relatively expensive). Below 100: "
               f"weaker. Gaps in the lines are months with missing IMF data.")

    export = export_frame(sub, c1, c2, rer_star)
    st.download_button(
        "Download CSV", export.to_csv(index=False).encode("utf-8"),
        file_name=f"rer_{c1}_{c2}_{start}_{end}.csv", mime="text/csv",
        type="primary",
    )

    with st.expander("Data coverage and table"):
        rows = []
        for iso, fx, cpi in ((c1, fx1, p1), (c2, fx2, p2)):
            for what, s in (("Exchange rate per USD", fx), ("CPI", cpi)):
                rows.append({"Country": COUNTRIES[iso][0], "Series": what,
                             "First": str(s.index.min()), "Last": str(s.index.max()),
                             "Observations": len(s)})
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        st.dataframe(export, hide_index=True, width="stretch")


if __name__ == "__main__":
    main()
