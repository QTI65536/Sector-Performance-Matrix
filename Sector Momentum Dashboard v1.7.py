import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
import streamlit.components.v1 as components

# 1. Dashboard Configuration
st.set_page_config(page_title="Sector Terminal v2.0.0-Raw", layout="wide")
refresh_count = st_autorefresh(interval=5 * 60 * 1000, key="data_update")

# 2. Architect's Custom CSS
st.markdown("""
    <style>
    .main .block-container {
        max-width: 98% !important;
        padding-left: 1% !important;
        padding-right: 1% !important;
        padding-top: 1.5rem !important;
    }
    h1 { font-size: 64px !important; color: #00FF00; font-weight: 800; margin-bottom: 0px; }
    .refresh-text { font-size: 22px; color: #888; margin-bottom: 15px; }
    .version-tag { font-size: 18px; color: #555; float: right; margin-top: -100px; }
    h2 { font-size: 40px !important; color: #FAFAFA; border-bottom: 2px solid #00FF00; padding-bottom: 5px; margin-bottom: 20px; }

    .legend-box {
        padding: 10px;
        border-radius: 5px;
        font-size: 14px;
        font-weight: bold;
        text-align: center;
        margin-bottom: 10px;
        border: 1px solid #444;
    }
    .legend-desc { font-size: 12px; font-weight: normal; display: block; margin-top: 2px; }
    </style>
    """, unsafe_allow_html=True)


# 3. Momentum Engine (Raw Price Logic)
@st.cache_data(ttl=300)
def fetch_live_momentum():
    tickers = ["XLE", "XLU", "XLB", "XLI", "XLP", "XLRE", "SPY", "XLC", "XLK", "XLV", "XLY", "XLF"]
    names = {"XLE": "Energy", "XLU": "Utilities", "XLB": "Materials", "XLI": "Industrials", "XLP": "Staples",
             "XLRE": "Real Estate", "SPY": "S&P 500", "XLC": "Comm Svcs", "XLK": "Technology", "XLV": "Healthcare",
             "XLY": "Discretionary", "XLF": "Financials"}

    # CRITICAL FIX: auto_adjust=False to get Raw Prices (Price Return)
    raw_data = yf.download(tickers, period="6y", interval="1d", auto_adjust=False, progress=False)
    price_data = raw_data['Close']

    momentum_list = []
    for ticker in tickers:
        if ticker not in price_data.columns: continue
        series = price_data[ticker].dropna()
        p_now = series.iloc[-1]

        # Returns based on Raw Close (Matches Schwab/Brokerage)
        r_5d = ((p_now / series.iloc[-6]) - 1) * 100
        r_1m = ((p_now / series.iloc[-21]) - 1) * 100

        # Logic Tree
        if r_5d >= 0 and r_1m >= r_5d:
            signal = "🚀 ACCELERATING" if r_5d > (0.333 * r_1m) else "📈 STEADY UP"
        elif r_5d <= 0 and r_1m <= r_5d:
            signal = "⚠️ PLUMMETING" if abs(r_5d) > (0.333 * abs(r_1m)) else "📉 STEADY DOWN"
        elif r_5d >= 0:
            signal = "🔄 REVERSAL UP"
        else:
            signal = "🔄 REVERSAL DOWN"

        momentum_list.append({
            "Ticker": ticker, "Sector": names[ticker], "Signal": signal,
            "Price": float(p_now),
            "1D": float(((p_now / series.iloc[-2]) - 1) * 100),
            "5D": float(r_5d),
            "1M": float(r_1m),
            "6M": float(((p_now / series.iloc[-126]) - 1) * 100),
            "YTD": float(((p_now / series[series.index >= f'{datetime.now().year}-01-01'].iloc[0]) - 1) * 100),
            "1Y": float(((p_now / series.iloc[-252]) - 1) * 100),
            "5Y": float(((p_now / series.iloc[-1260]) - 1) * 100) # Fix: Exactly 5 trading years
        })
    return pd.DataFrame(momentum_list)


# 4. Styling
def style_signal(val):
    colors = {
        "🚀 ACCELERATING": "background-color: #00FF00; color: black;",
        "📈 STEADY UP": "background-color: #2E7D32; color: white;",
        "🔄 REVERSAL UP": "background-color: #00FFFF; color: black;",
        "🔄 REVERSAL DOWN": "background-color: #FFA500; color: black;",
        "📉 STEADY DOWN": "background-color: #C62828; color: white;",
        "⚠️ PLUMMETING": "background-color: #FF0000; color: white;"
    }
    return f"{colors.get(val, '')} font-weight: bold; text-align: center; border: 1px solid #444;"


def style_matrix(val):
    if not isinstance(val, (int, float)): return 'border: 1px solid #444;'
    color = '#1B5E20' if val > 3 else '#2E7D32' if val > 0 else '#8B0000' if val < -3 else '#C62828' if val < 0 else '#424242'
    return f'background-color: {color}; color: white; font-weight: bold; text-align: center; border: 1px solid #444;'


# --- UI Execution ---
try:
    raw_df = fetch_live_momentum()
    st.markdown('<h1>🛰️ LIVE SECTOR MOMENTUM TERMINAL</h1>', unsafe_allow_html=True)
    st.markdown(f'<div class="version-tag">v2.0.0-RawFix</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="refresh-text">Last Refresh: {datetime.now().strftime("%H:%M:%S")} | Cycle Count: {refresh_count}</div>', unsafe_allow_html=True)

    st.header("I. PERFORMANCE MATRIX")
    col_s1, col_s2 = st.columns([2, 1])
    sort_col = col_s1.selectbox("Sort by:", raw_df.columns, index=0)
    sort_order = col_s2.radio("Order:", ["Ascending", "Descending"], horizontal=True)

    df = raw_df.sort_values(by=sort_col, ascending=(sort_order == "Ascending")).reset_index(drop=True)

    # Render Matrix
    perf_cols = ["1D", "5D", "1M", "6M", "YTD", "1Y", "5Y"]
    styler = df.style.map(style_matrix, subset=perf_cols).map(style_signal, subset=["Signal"])
    table_html = styler.format("{:.2f}", subset=["Price"]).format("{:.2f}%", subset=perf_cols).to_html()

    full_html = f"""
    <style>
        body {{ background-color: #0e1117; margin: 0; padding: 0; overflow: hidden; }}
        table {{ width: 100%; border-collapse: collapse; font-family: sans-serif; color: white; }}
        th {{ background-color: #111; color: #00FF00; font-size: 20px; padding: 15px; border: 1px solid #444; }}
        td {{ font-size: 19px; padding: 10px; border: 1px solid #444; }}
    </style>
    {table_html}
    """
    components.html(full_html, height=760, scrolling=False)

    # --- Market Interpretation Legend ---
    st.markdown("### Market Interpretation Legend")
    l_cols = st.columns(6)
    legend_items = [
        ("🚀 ACCELERATING", "#00FF00", "black", "Strength > Monthly Avg"),
        ("📈 STEADY UP", "#2E7D32", "white", "Stable Advance"),
        ("🔄 REVERSAL UP", "#00FFFF", "black", "Prior Neg / Current Pos"),
        ("🔄 REVERSAL DOWN", "#FFA500", "black", "Prior Pos / Current Neg"),
        ("📉 STEADY DOWN", "#C62828", "white", "Stable Decline"),
        ("⚠️ PLUMMETING", "#FF0000", "white", "Selling Accelerating")
    ]

    for i, (label, b_color, t_color, desc) in enumerate(legend_items):
        with l_cols[i]:
            st.markdown(f'<div class="legend-box" style="background-color: {b_color}; color: {t_color};">{label}<span class="legend-desc">{desc}</span></div>', unsafe_allow_html=True)

    # --- Chart Section ---
    st.header("II. MOMENTUM VISUALIZATION")
    chart_periods = ["5D", "1M", "6M"]
    df_melted = df.melt(id_vars=["Ticker"], value_vars=chart_periods, var_name="Period", value_name="Return")

    fig = px.bar(df_melted, x="Ticker", y="Return", color="Period", barmode="group", text_auto='.2f',
                 color_discrete_map={"5D": "#00FF00", "1M": "#FF4B4B", "6M": "#FFD700"}, template="plotly_dark")
    fig.update_layout(font=dict(size=24), height=700,
                      xaxis=dict(categoryorder='array', categoryarray=df['Ticker'].tolist(), title=""),
                      yaxis=dict(title="Return %", gridcolor='#333'),
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
                      paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=10, r=10, t=100, b=50))
    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"Error: {e}")
