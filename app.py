# geopolitical_dashboard_worldbank_streamlit.py
# Run with: streamlit run geopolitical_dashboard_worldbank_streamlit.py

import requests
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(
    page_title="Strategic Power Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------
# UI THEME
# -----------------------------
st.markdown(
    """
    <style>
        .main {background-color: #0b1020; color: #f5f5f5;}
        .block-container {padding-top: 2rem; padding-bottom: 2rem;}
        h1, h2, h3 {color: #f8fafc; font-family: 'Inter', sans-serif;}
        .metric-card {
            background: linear-gradient(135deg, #111827 0%, #1f2937 100%);
            padding: 1.2rem;
            border-radius: 18px;
            border: 1px solid #334155;
            box-shadow: 0 10px 30px rgba(0,0,0,0.25);
        }
        .small-muted {color: #94a3b8; font-size: 0.88rem;}
        .signal-high {color: #f87171; font-weight: 700;}
        .signal-medium {color: #facc15; font-weight: 700;}
        .signal-low {color: #4ade80; font-weight: 700;}
        div[data-testid="stMetricValue"] {color: #f8fafc;}
        div[data-testid="stMetricLabel"] {color: #cbd5e1;}
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# WORLD BANK INDICATORS
# -----------------------------
INDICATORS = {
    "Military expenditure (% of GDP)": "MS.MIL.XPND.GD.ZS",
    "Military expenditure (% of govt expenditure)": "MS.MIL.XPND.ZS",
    "GDP current US$": "NY.GDP.MKTP.CD",
    "GDP growth annual %": "NY.GDP.MKTP.KD.ZG",
    "Inflation consumer prices annual %": "FP.CPI.TOTL.ZG",
    "Population total": "SP.POP.TOTL",
    "Current account balance (% of GDP)": "BN.CAB.XOKA.GD.ZS",
    "Trade (% of GDP)": "NE.TRD.GNFS.ZS",
}

COUNTRIES = {
    "India": "IND",
    "United States": "USA",
    "China": "CHN",
    "Russia": "RUS",
    "Israel": "ISR",
    "United Kingdom": "GBR",
    "France": "FRA",
    "Germany": "DEU",
    "Japan": "JPN",
    "South Korea": "KOR",
    "Turkey": "TUR",
    "Poland": "POL",
    "Saudi Arabia": "SAU",
    "Ukraine": "UKR",
    "Pakistan": "PAK",
}

# -----------------------------
# DATA FETCHING
# -----------------------------
@st.cache_data(ttl=60 * 60 * 12, show_spinner=False)
def fetch_world_bank(country_code: str, indicator_code: str) -> pd.DataFrame:
    """Fetch World Bank indicator data for one country and one indicator."""
    url = (
        f"https://api.worldbank.org/v2/country/{country_code}/indicator/"
        f"{indicator_code}?format=json&per_page=20000"
    )
    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        st.warning(f"API error for {country_code} - {indicator_code}: {exc}")
        return pd.DataFrame()

    if not isinstance(payload, list) or len(payload) < 2 or payload[1] is None:
        return pd.DataFrame()

    rows = []
    for item in payload[1]:
        if item.get("value") is not None:
            rows.append(
                {
                    "country": item["country"]["value"],
                    "country_code": country_code,
                    "indicator": item["indicator"]["value"],
                    "indicator_code": indicator_code,
                    "year": int(item["date"]),
                    "value": float(item["value"]),
                }
            )
    return pd.DataFrame(rows)

@st.cache_data(ttl=60 * 60 * 12, show_spinner=True)
def build_dataset(selected_countries, selected_indicators) -> pd.DataFrame:
    frames = []
    for country_name in selected_countries:
        country_code = COUNTRIES[country_name]
        for indicator_name in selected_indicators:
            indicator_code = INDICATORS[indicator_name]
            df = fetch_world_bank(country_code, indicator_code)
            if not df.empty:
                df["indicator_short"] = indicator_name
                frames.append(df)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)

# -----------------------------
# ANALYTICS HELPERS
# -----------------------------
def latest_value(df: pd.DataFrame, country: str, indicator: str):
    temp = df[(df["country"] == country) & (df["indicator_short"] == indicator)].sort_values("year")
    if temp.empty:
        return None, None
    row = temp.iloc[-1]
    return row["value"], int(row["year"])

def calc_cagr(start, end, years):
    if start is None or end is None or start <= 0 or years <= 0:
        return None
    return ((end / start) ** (1 / years) - 1) * 100

def pressure_label(value):
    if value is None:
        return "No Data", "signal-medium"
    if value >= 4:
        return "High", "signal-high"
    if value >= 2:
        return "Elevated", "signal-medium"
    return "Moderate", "signal-low"

# -----------------------------
# SIDEBAR
# -----------------------------
st.sidebar.title("🛡️ Control Room")
st.sidebar.caption("Strategic power indicators using World Bank API")

selected_countries = st.sidebar.multiselect(
    "Countries",
    options=list(COUNTRIES.keys()),
    default=["India", "United States", "China", "Russia", "Israel"],
)

selected_indicators = st.sidebar.multiselect(
    "Indicators",
    options=list(INDICATORS.keys()),
    default=[
        "Military expenditure (% of GDP)",
        "Military expenditure (% of govt expenditure)",
        "GDP growth annual %",
        "Inflation consumer prices annual %",
        "Trade (% of GDP)",
    ],
)

year_range = st.sidebar.slider("Year range", 1990, datetime.now().year, (2000, datetime.now().year))

primary_indicator = st.sidebar.selectbox(
    "Primary analysis indicator",
    options=selected_indicators if selected_indicators else list(INDICATORS.keys()),
    index=0,
)

st.sidebar.markdown("---")
st.sidebar.caption("Note: World Bank indicators are structural, not live. Use this layer with market/news/conflict APIs later.")

# -----------------------------
# LOAD DATA
# -----------------------------
if not selected_countries or not selected_indicators:
    st.error("Select at least one country and one indicator. Even empires need inputs.")
    st.stop()

with st.spinner("Fetching World Bank data and building dashboard..."):
    data = build_dataset(selected_countries, selected_indicators)

if data.empty:
    st.error("No data returned. Check country/indicator choices or API availability.")
    st.stop()

data = data[(data["year"] >= year_range[0]) & (data["year"] <= year_range[1])]

# -----------------------------
# HEADER
# -----------------------------
st.title("Strategic Power Dashboard")
st.markdown(
    """
    <div class='small-muted'>
    A clean macro-defense intelligence layer tracking military expenditure, economic pressure,
    and strategic capacity across countries. This is the slow structural base of your future geopolitical-financial dashboard.
    </div>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# TOP METRICS
# -----------------------------
primary_df = data[data["indicator_short"] == primary_indicator].copy()
latest_rows = primary_df.sort_values("year").groupby("country", as_index=False).tail(1)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Countries tracked", len(selected_countries))
with col2:
    st.metric("Indicators tracked", len(selected_indicators))
with col3:
    st.metric("Latest available year", int(data["year"].max()))
with col4:
    avg_latest = latest_rows["value"].mean() if not latest_rows.empty else None
    st.metric("Avg latest primary value", f"{avg_latest:,.2f}" if avg_latest is not None else "N/A")

st.markdown("---")

# -----------------------------
# PRIMARY CHART + RANKING
# -----------------------------
left, right = st.columns([2, 1])

with left:
    st.subheader(f"Trend: {primary_indicator}")
    fig = px.line(
        primary_df.sort_values("year"),
        x="year",
        y="value",
        color="country",
        markers=True,
        template="plotly_dark",
        title=None,
    )
    fig.update_layout(
        height=520,
        paper_bgcolor="#0b1020",
        plot_bgcolor="#111827",
        legend_title_text="Country",
        xaxis_title="Year",
        yaxis_title=primary_indicator,
        margin=dict(l=20, r=20, t=20, b=20),
    )
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Latest ranking")
    rank_df = latest_rows[["country", "year", "value"]].sort_values("value", ascending=False)
    st.dataframe(
        rank_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "country": "Country",
            "year": "Year",
            "value": st.column_config.NumberColumn("Value", format="%.2f"),
        },
    )

# -----------------------------
# STRATEGIC PRESSURE CARDS
# -----------------------------
st.subheader("Country Signal Cards")
card_cols = st.columns(min(3, len(selected_countries)))

for idx, country_name in enumerate(selected_countries):
    country_display = data[data["country_code"] == COUNTRIES[country_name]]["country"].dropna().unique()
    country_label = country_display[0] if len(country_display) else country_name
    mil_value, mil_year = latest_value(data, country_label, "Military expenditure (% of GDP)")
    govt_value, govt_year = latest_value(data, country_label, "Military expenditure (% of govt expenditure)")
    gdp_growth, gdp_year = latest_value(data, country_label, "GDP growth annual %")
    label, css = pressure_label(mil_value)

    with card_cols[idx % len(card_cols)]:
        st.markdown(
            f"""
            <div class='metric-card'>
                <h3>{country_label}</h3>
                <p class='small-muted'>Military burden signal</p>
                <h2>{mil_value:.2f}%</h2>
                <p class='{css}'>{label}</p>
                <p class='small-muted'>Military expenditure as % of GDP, latest year: {mil_year if mil_year else 'N/A'}</p>
                <hr style='border: 0.5px solid #334155;'>
                <p><b>Govt expenditure share:</b> {govt_value:.2f}%</p>
                <p><b>GDP growth:</b> {gdp_growth:.2f}%</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.markdown("---")

# -----------------------------
# MULTI-INDICATOR COMPARISON
# -----------------------------
st.subheader("Multi-Indicator Comparison")
selected_country_for_detail = st.selectbox("Country detail view", selected_countries)
country_code = COUNTRIES[selected_country_for_detail]
country_df = data[data["country_code"] == country_code]

fig2 = go.Figure()
for indicator in selected_indicators:
    temp = country_df[country_df["indicator_short"] == indicator].sort_values("year")
    if not temp.empty:
        normalized = temp.copy()
        min_v = normalized["value"].min()
        max_v = normalized["value"].max()
        if max_v != min_v:
            normalized["normalized_value"] = (normalized["value"] - min_v) / (max_v - min_v) * 100
        else:
            normalized["normalized_value"] = 50
        fig2.add_trace(
            go.Scatter(
                x=normalized["year"],
                y=normalized["normalized_value"],
                mode="lines+markers",
                name=indicator,
            )
        )

fig2.update_layout(
    template="plotly_dark",
    height=520,
    paper_bgcolor="#0b1020",
    plot_bgcolor="#111827",
    yaxis_title="Normalized score (0–100)",
    xaxis_title="Year",
    margin=dict(l=20, r=20, t=20, b=20),
)
st.plotly_chart(fig2, use_container_width=True)

# -----------------------------
# RAW DATA + DOWNLOAD
# -----------------------------
with st.expander("View and download processed data"):
    st.dataframe(data.sort_values(["country", "indicator_short", "year"]), use_container_width=True, hide_index=True)
    csv = data.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download CSV",
        data=csv,
        file_name="strategic_power_worldbank_data.csv",
        mime="text/csv",
    )

# -----------------------------
# NEXT LAYER NOTE
# -----------------------------
st.info(
    "Next upgrade: add market APIs, GDELT news intensity, UCDP/ACLED conflict events, and a Two-Clocks Gap Score. "
    "This app is the macro-defense foundation, not the full intelligence engine yet."
)
