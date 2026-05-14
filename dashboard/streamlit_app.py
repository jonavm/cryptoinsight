from datetime import UTC, datetime

import pandas as pd
import streamlit as st

from app.core.config import get_settings
from dashboard.api_client import (
    fetch_alerts,
    fetch_health,
    fetch_history,
    fetch_latest,
    fetch_summary,
    fetch_watchlist,
)
from dashboard.formatters import format_compact_currency, status_chip, to_float
from dashboard.ui import apply_global_styles, render_card, render_hero, render_sidebar, render_topbar
from dashboard.views import (
    render_alerts,
    render_assets,
    render_markets,
    render_overview,
    render_settings,
    render_watchlist,
)

settings = get_settings()

st.set_page_config(page_title="CryptoInsight", layout="wide")
apply_global_styles()
render_topbar()
render_hero()

summary = fetch_summary()
health = fetch_health()
latest = fetch_latest()
latest_df = pd.DataFrame(latest)

if latest_df.empty:
    st.info("No market data yet. Wait for the first ingestion cycle to finish.")
    st.stop()

latest_df["current_price_usd"] = latest_df["current_price_usd"].astype(float)
latest_df["market_cap_usd"] = latest_df["market_cap_usd"].astype(float)
latest_df["total_volume_usd"] = latest_df["total_volume_usd"].astype(float)
latest_df["price_change_percentage_24h"] = latest_df["price_change_percentage_24h"].astype(float)
latest_df["snapshot_at"] = pd.to_datetime(latest_df["snapshot_at"], utc=True)

latest_snapshot_at = latest_df["snapshot_at"].max()
snapshot_age_seconds = (datetime.now(UTC) - latest_snapshot_at.to_pydatetime()).total_seconds()
market_status_label, market_status_class = status_chip(snapshot_age_seconds, settings.ingestion_interval_seconds)
pipeline_status = health.get("pipeline")
pipeline_last_error = pipeline_status.get("last_error") if pipeline_status else None
pipeline_rows_inserted = pipeline_status.get("rows_inserted") if pipeline_status else None
pipeline_rows_fetched = pipeline_status.get("rows_fetched") if pipeline_status else None
pipeline_duration = pipeline_status.get("last_duration_seconds") if pipeline_status else None
btc_row = latest_df.loc[latest_df["asset_id"] == "bitcoin"]
btc_dominance = 0.0
if not btc_row.empty and to_float(summary.get("total_market_cap_usd")) > 0:
    btc_dominance = (to_float(btc_row.iloc[0]["market_cap_usd"]) / to_float(summary.get("total_market_cap_usd"))) * 100

asset_options = latest_df[["asset_id", "name", "symbol"]].copy()
asset_options["label"] = asset_options.apply(lambda row: f"{row['name']} ({row['symbol']})", axis=1)
asset_lookup = dict(zip(asset_options["label"], asset_options["asset_id"], strict=False))

current_view, selected_label, history_limit = render_sidebar(
    asset_options=asset_options,
    latest_snapshot_at=latest_snapshot_at,
    snapshot_age_seconds=snapshot_age_seconds,
    market_status_label=market_status_label,
)
selected_asset_id = asset_lookup[selected_label]

alerts_payload = fetch_alerts()
asset_alerts_payload: list[dict] = []
history_df = pd.DataFrame()
history_analytics = None

if current_view == "Assets":
    asset_alerts_payload = fetch_alerts(selected_asset_id)
    history_payload = fetch_history(selected_asset_id, history_limit)
    history_df = pd.DataFrame(history_payload.get("snapshots", []))
    history_analytics = history_payload.get("analytics")

    if not history_df.empty:
        history_df["snapshot_at"] = pd.to_datetime(history_df["snapshot_at"], utc=True)
        history_df["current_price_usd"] = history_df["current_price_usd"].astype(float)
        history_df["market_cap_usd"] = history_df["market_cap_usd"].astype(float)
        history_df["total_volume_usd"] = history_df["total_volume_usd"].astype(float)
        history_df["price_change_percentage_24h"] = history_df["price_change_percentage_24h"].astype(float)
        history_df = history_df.sort_values("snapshot_at")

top_mover = latest_df.sort_values("price_change_percentage_24h", ascending=False).iloc[0]
largest_volume = latest_df.sort_values("total_volume_usd", ascending=False).iloc[0]
largest_cap = latest_df.sort_values("market_cap_usd", ascending=False).iloc[0]

topbar_cols = st.columns([1.2, 1, 1])
with topbar_cols[0]:
    st.markdown(
        f"""
        <div class="{market_status_class}">
            {market_status_label} feed / last successful update {latest_snapshot_at.strftime("%H:%M:%S UTC")}
        </div>
        """,
        unsafe_allow_html=True,
    )
with topbar_cols[1]:
    st.markdown(f'<div class="chip mono">BTC dominance {btc_dominance:.2f}%</div>', unsafe_allow_html=True)
with topbar_cols[2]:
    st.markdown(f'<div class="chip mono">Tracked universe {summary.get("tracked_assets", 0)} assets</div>', unsafe_allow_html=True)

kpi_cols = st.columns(4)
with kpi_cols[0]:
    render_card("Total market cap", format_compact_currency(summary.get("total_market_cap_usd")), "Sum of tracked assets")
with kpi_cols[1]:
    render_card("Total volume", format_compact_currency(summary.get("total_volume_usd")), "24h volume in the latest snapshot")
with kpi_cols[2]:
    render_card("Market leader", largest_cap["symbol"], format_compact_currency(largest_cap["market_cap_usd"]))
with kpi_cols[3]:
    render_card("Top mover 24h", top_mover["symbol"], f"{top_mover['price_change_percentage_24h']:.2f}%")

ops_cols = st.columns(3)
with ops_cols[0]:
    render_card("Feed status", pipeline_status["status"] if pipeline_status else "unknown", "Current ingestion state")
with ops_cols[1]:
    inserted_copy = "Rows inserted in last cycle" if pipeline_rows_inserted is not None else "No run data yet"
    render_card("Last cycle writes", str(pipeline_rows_inserted) if pipeline_rows_inserted is not None else "n/a", inserted_copy)
with ops_cols[2]:
    duration_label = f"{pipeline_duration:.2f}s" if pipeline_duration is not None else "n/a"
    render_card("Cycle duration", duration_label, "Last completed ingestion cycle")

watchlist_payload = fetch_watchlist()
persisted_watchlist_assets = watchlist_payload.get("asset_ids", [])
if "watchlist_assets" not in st.session_state:
    st.session_state.watchlist_assets = persisted_watchlist_assets or latest_df["asset_id"].head(2).tolist()

if current_view == "Overview":
    render_overview(
        latest_df=latest_df,
        alerts_payload=alerts_payload,
        largest_cap=largest_cap,
        largest_volume=largest_volume,
        top_mover=top_mover,
        market_status_label=market_status_label,
        snapshot_age_seconds=snapshot_age_seconds,
    )
elif current_view == "Markets":
    render_markets(latest_df=latest_df)
elif current_view == "Watchlist":
    render_watchlist(
        latest_df=latest_df,
        asset_options=asset_options,
        persisted_watchlist_assets=persisted_watchlist_assets,
    )
elif current_view == "Alerts":
    render_alerts(
        alerts_payload=alerts_payload,
        asset_options=asset_options,
        asset_lookup=asset_lookup,
    )
elif current_view == "Assets":
    render_assets(
        latest_df=latest_df,
        selected_label=selected_label,
        selected_asset_id=selected_asset_id,
        history_df=history_df,
        history_analytics=history_analytics,
        asset_alerts_payload=asset_alerts_payload,
        pipeline_status=pipeline_status,
        pipeline_rows_fetched=pipeline_rows_fetched,
        pipeline_rows_inserted=pipeline_rows_inserted,
        market_status_label=market_status_label,
        latest_snapshot_at=latest_snapshot_at,
    )
else:
    render_settings(settings=settings, pipeline_last_error=pipeline_last_error, asset_options=asset_options)
