import streamlit as st


def apply_global_styles() -> None:
    st.markdown(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap');
            .stApp {
                background:
                    radial-gradient(circle at 14% 10%, rgba(24, 182, 122, 0.10), transparent 18%),
                    radial-gradient(circle at 84% 12%, rgba(41, 91, 255, 0.08), transparent 22%),
                    linear-gradient(180deg, #081019 0%, #0B1020 45%, #121A2B 100%);
                font-family: 'IBM Plex Sans', sans-serif;
            }
            .block-container {
                max-width: 1440px;
                padding-top: 1.25rem;
                padding-bottom: 2rem;
            }
            [data-testid="stSidebar"] {
                background: rgba(8, 14, 26, 0.98);
                border-right: 1px solid rgba(167, 179, 201, 0.10);
            }
            .topbar {
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 1rem;
                margin-bottom: 1rem;
                padding: 0.85rem 1rem;
                border-radius: 18px;
                border: 1px solid rgba(84, 196, 145, 0.14);
                background:
                    linear-gradient(180deg, rgba(12, 22, 26, 0.92), rgba(18, 26, 43, 0.82));
            }
            .brand-wrap {
                display: flex;
                align-items: center;
                gap: 0.8rem;
            }
            .brand-mark {
                width: 12px;
                height: 12px;
                border-radius: 999px;
                background: #18B67A;
                box-shadow: 0 0 0 6px rgba(24, 182, 122, 0.14);
            }
            .brand-title {
                color: #F5F7FB;
                font-size: 1.1rem;
                font-weight: 700;
            }
            .brand-copy {
                color: #A7B3C9;
                font-size: 0.88rem;
            }
            .topbar-meta {
                display: flex;
                gap: 0.65rem;
                align-items: center;
                flex-wrap: wrap;
                justify-content: flex-end;
            }
            .chip {
                padding: 0.42rem 0.65rem;
                border-radius: 999px;
                background: rgba(255, 255, 255, 0.03);
                color: #9DB0AA;
                font-size: 0.8rem;
                border: 1px solid rgba(84, 196, 145, 0.10);
            }
            .chip-live {
                color: #18B67A;
                border-color: rgba(24, 182, 122, 0.28);
                background: rgba(24, 182, 122, 0.10);
                box-shadow: inset 0 0 18px rgba(24, 182, 122, 0.05);
            }
            .chip-delayed {
                color: #F2B84B;
                border-color: rgba(242, 184, 75, 0.28);
                background: rgba(242, 184, 75, 0.08);
            }
            .hero {
                border-radius: 26px;
                padding: 1.4rem 1.4rem 1.15rem 1.4rem;
                margin-bottom: 1rem;
                border: 1px solid rgba(84, 196, 145, 0.14);
                background:
                    linear-gradient(135deg, rgba(10, 18, 24, 0.96), rgba(18, 26, 43, 0.76));
            }
            .hero-eyebrow {
                text-transform: uppercase;
                letter-spacing: 0.18em;
                color: #6EE7B7;
                font-size: 0.72rem;
                font-weight: 800;
                margin-bottom: 0.4rem;
                font-family: 'IBM Plex Mono', monospace;
            }
            .hero-title {
                color: #F5F7FB;
                font-size: 2.9rem;
                line-height: 0.98;
                font-weight: 820;
                margin-bottom: 0.55rem;
            }
            .hero-copy {
                color: #A7B3C9;
                max-width: 840px;
                line-height: 1.65;
                font-size: 0.98rem;
            }
            .section-title {
                color: #F5F7FB;
                font-size: 1.14rem;
                font-weight: 720;
                margin-bottom: 0.18rem;
            }
            .section-copy {
                color: #8FA0B7;
                margin-bottom: 0.8rem;
            }
            .card {
                border-radius: 18px;
                padding: 1rem 1rem 0.85rem 1rem;
                border: 1px solid rgba(84, 196, 145, 0.12);
                background: linear-gradient(180deg, rgba(11, 21, 28, 0.88), rgba(18, 26, 43, 0.76));
                min-height: 126px;
            }
            .card-label {
                color: #8FAE9A;
                font-size: 0.76rem;
                text-transform: uppercase;
                letter-spacing: 0.08em;
                margin-bottom: 0.3rem;
                font-family: 'IBM Plex Mono', monospace;
            }
            .card-value {
                color: #F5F7FB;
                font-size: 2rem;
                font-weight: 760;
                line-height: 1.0;
                margin-bottom: 0.2rem;
                font-variant-numeric: tabular-nums;
            }
            .card-subtle {
                color: #6EE7B7;
                font-size: 0.88rem;
                font-weight: 600;
            }
            .panel {
                border-radius: 20px;
                padding: 1rem;
                border: 1px solid rgba(84, 196, 145, 0.12);
                background: rgba(14, 20, 31, 0.78);
                margin-bottom: 1rem;
            }
            .mini-row {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 0.55rem 0;
                border-bottom: 1px solid rgba(167, 179, 201, 0.08);
            }
            .mini-row:last-child {
                border-bottom: none;
            }
            .mono {
                font-family: "IBM Plex Mono", monospace;
                font-variant-numeric: tabular-nums;
            }
            .state-up {
                color: #18B67A;
                font-weight: 650;
            }
            .state-down {
                color: #E85D75;
                font-weight: 650;
            }
            .state-warn {
                color: #F2B84B;
                font-weight: 650;
            }
            .stTabs [data-baseweb="tab-list"] {
                gap: 0.4rem;
            }
            .stTabs [data-baseweb="tab"] {
                background: rgba(255, 255, 255, 0.03);
                border-radius: 999px;
                padding: 0.45rem 0.9rem;
            }
            .stTabs [aria-selected="true"] {
                background: rgba(24, 182, 122, 0.12) !important;
                color: #D1FAE5 !important;
            }
            div[data-testid="stMetric"] {
                background: linear-gradient(180deg, rgba(11, 21, 28, 0.88), rgba(18, 26, 43, 0.76));
                border: 1px solid rgba(84, 196, 145, 0.10);
                border-radius: 16px;
                padding: 0.75rem 0.85rem;
            }
            div[data-testid="stMetricLabel"] {
                color: #8FAE9A;
                font-family: 'IBM Plex Mono', monospace;
                text-transform: uppercase;
                letter-spacing: 0.06em;
            }
            div[data-testid="stMetricValue"] {
                color: #F5F7FB;
                font-variant-numeric: tabular-nums;
            }
            div[data-testid="stDataFrame"] {
                border: 1px solid rgba(84, 196, 145, 0.10);
                border-radius: 16px;
                overflow: hidden;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_card(label: str, value: str, subtle: str) -> None:
    st.markdown(
        f"""
        <div class="card">
            <div class="card-label">{label}</div>
            <div class="card-value">{value}</div>
            <div class="card-subtle">{subtle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_topbar() -> None:
    st.markdown(
        """
        <div class="topbar">
            <div class="brand-wrap">
                <div class="brand-mark"></div>
                <div>
                    <div class="brand-title">CryptoInsight</div>
                    <div class="brand-copy">Market intelligence for real-time crypto monitoring</div>
                </div>
            </div>
            <div class="topbar-meta">
                <div class="chip mono">Sources: CoinGecko / Binance / WazirX</div>
                <div class="chip mono">Flow: market scan to asset detail to tracking</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_hero() -> None:
    st.markdown(
        """
        <div class="hero">
            <div class="hero-eyebrow">Research Terminal</div>
            <div class="hero-title">Read the market before the move.</div>
            <div class="hero-copy">
                Follow market state, inspect asset history, and verify feed health from one interface built for quick reading.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar(asset_options, latest_snapshot_at, snapshot_age_seconds: float, market_status_label: str) -> tuple[str, str, int]:
    with st.sidebar:
        st.markdown("## Navigation")
        current_view = st.radio(
            "Current view",
            options=["Overview", "Markets", "Watchlist", "Alerts", "Assets", "Settings"],
            label_visibility="collapsed",
        )

        st.divider()
        st.markdown("## Asset Focus")
        selected_label = st.selectbox("Tracked asset", options=asset_options["label"].tolist())
        history_limit = st.slider("History points", min_value=10, max_value=100, value=50, step=10)

        st.divider()
        st.markdown("## Feed Status")
        st.markdown(f"**Market state:** `{market_status_label}`")
        st.markdown(f"**Last sync:** `{latest_snapshot_at.strftime('%Y-%m-%d %H:%M:%S UTC')}`")
        st.markdown(f"**Snapshot age:** `{int(snapshot_age_seconds)}s`")
        st.caption("Use this panel to confirm freshness before reading the rest of the screen.")

    return current_view, selected_label, history_limit
