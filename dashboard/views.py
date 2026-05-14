import altair as alt
import pandas as pd
import streamlit as st

from dashboard.api_client import fetch_alert_rules, fetch_alerts, save_alert_rules, save_watchlist
from dashboard.formatters import format_compact_currency, format_currency, format_percent
from dashboard.ui import render_card


def _render_ranked_market_table(latest_df: pd.DataFrame) -> None:
    table_df = latest_df.copy().sort_values("market_cap_usd", ascending=False)
    table_df["current_price_usd"] = table_df["current_price_usd"].map(format_currency)
    table_df["market_cap_usd"] = table_df["market_cap_usd"].map(format_compact_currency)
    table_df["total_volume_usd"] = table_df["total_volume_usd"].map(format_compact_currency)
    table_df["price_change_percentage_24h"] = table_df["price_change_percentage_24h"].map(format_percent)
    table_df["snapshot_at"] = table_df["snapshot_at"].dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    st.dataframe(
        table_df[
            [
                "asset_id",
                "symbol",
                "name",
                "current_price_usd",
                "market_cap_usd",
                "total_volume_usd",
                "price_change_percentage_24h",
                "snapshot_at",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )


def render_overview(latest_df: pd.DataFrame, alerts_payload: list[dict], largest_cap, largest_volume, top_mover, market_status_label: str, snapshot_age_seconds: float) -> None:
    left_col, right_col = st.columns([1.35, 0.65])

    with left_col:
        st.markdown('<div class="section-title">24h move ranking</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-copy">Quick view of 24h performance across tracked assets.</div>', unsafe_allow_html=True)
        movers_chart = (
            alt.Chart(latest_df)
            .mark_bar(cornerRadiusTopRight=8, cornerRadiusBottomRight=8)
            .encode(
                x=alt.X("price_change_percentage_24h:Q", title="24h change (%)"),
                y=alt.Y("name:N", sort="-x", title=None),
                color=alt.condition(
                    alt.datum.price_change_percentage_24h >= 0,
                    alt.value("#18B67A"),
                    alt.value("#E85D75"),
                ),
                tooltip=[
                    alt.Tooltip("name:N", title="Asset"),
                    alt.Tooltip("current_price_usd:Q", title="Price", format=",.2f"),
                    alt.Tooltip("price_change_percentage_24h:Q", title="24h change", format=".2f"),
                ],
            )
            .properties(height=340)
        )
        st.altair_chart(movers_chart, use_container_width=True)

    with right_col:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Market scan</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-copy">Signals that deserve attention right now.</div>', unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="mini-row">
                <span>{largest_cap['name']} leads by market cap</span>
                <span class="mono">{format_compact_currency(largest_cap['market_cap_usd'])}</span>
            </div>
            <div class="mini-row">
                <span>{largest_volume['name']} carries the highest volume</span>
                <span class="mono">{format_compact_currency(largest_volume['total_volume_usd'])}</span>
            </div>
            <div class="mini-row">
                <span>{top_mover['name']} is the strongest 24h mover</span>
                <span class="mono {'state-up' if top_mover['price_change_percentage_24h'] >= 0 else 'state-down'}">{format_percent(top_mover['price_change_percentage_24h'])}</span>
            </div>
            <div class="mini-row">
                <span>Feed freshness</span>
                <span class="mono {'state-up' if market_status_label == 'Live' else 'state-warn'}">{int(snapshot_age_seconds)}s age</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Alerts panel</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-copy">Signals derived from market movement and feed freshness.</div>', unsafe_allow_html=True)
        for alert in alerts_payload[:5]:
            severity_class = "state-up" if alert["severity"] == "low" else "state-warn" if alert["severity"] == "medium" else "state-down"
            st.markdown(
                f"""
                <div class="mini-row">
                    <span>{alert['title']}</span>
                    <span class="mono {severity_class}">{alert['severity']}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.caption(alert["message"])
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="section-title">Market table</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-copy">Current ranked view of the tracked market.</div>', unsafe_allow_html=True)
    _render_ranked_market_table(latest_df)


def render_markets(latest_df: pd.DataFrame) -> None:
    st.markdown('<div class="section-title">Markets</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-copy">Current cross-section of the tracked universe.</div>', unsafe_allow_html=True)

    market_chart = (
        alt.Chart(latest_df)
        .mark_circle(size=260, opacity=0.85)
        .encode(
            x=alt.X("market_cap_usd:Q", title="Market cap (USD)"),
            y=alt.Y("total_volume_usd:Q", title="24h volume (USD)"),
            color=alt.condition(
                alt.datum.price_change_percentage_24h >= 0,
                alt.value("#18B67A"),
                alt.value("#E85D75"),
            ),
            tooltip=[
                alt.Tooltip("name:N", title="Asset"),
                alt.Tooltip("current_price_usd:Q", title="Price", format=",.2f"),
                alt.Tooltip("market_cap_usd:Q", title="Market cap", format=",.2f"),
                alt.Tooltip("total_volume_usd:Q", title="Volume", format=",.2f"),
                alt.Tooltip("price_change_percentage_24h:Q", title="24h change", format=".2f"),
            ],
        )
        .properties(height=360)
    )
    st.altair_chart(market_chart, use_container_width=True)

    markets_df = latest_df.copy().sort_values(["market_cap_usd", "total_volume_usd"], ascending=[False, False])
    markets_df["current_price_usd"] = markets_df["current_price_usd"].map(format_currency)
    markets_df["market_cap_usd"] = markets_df["market_cap_usd"].map(format_compact_currency)
    markets_df["total_volume_usd"] = markets_df["total_volume_usd"].map(format_compact_currency)
    markets_df["price_change_percentage_24h"] = markets_df["price_change_percentage_24h"].map(format_percent)
    markets_df["snapshot_at"] = markets_df["snapshot_at"].dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    st.dataframe(
        markets_df[
            [
                "asset_id",
                "symbol",
                "name",
                "current_price_usd",
                "market_cap_usd",
                "total_volume_usd",
                "price_change_percentage_24h",
                "snapshot_at",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )


def render_watchlist(latest_df: pd.DataFrame, asset_options: pd.DataFrame, persisted_watchlist_assets: list[str]) -> None:
    st.markdown('<div class="section-title">Watchlist</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-copy">Tracked assets you want to review more often.</div>', unsafe_allow_html=True)

    with st.form("watchlist_form"):
        selected_watchlist = st.multiselect(
            "Choose watchlist assets",
            options=asset_options["asset_id"].tolist(),
            default=st.session_state.watchlist_assets,
            format_func=lambda asset_id: asset_options.loc[asset_options["asset_id"] == asset_id, "label"].iloc[0],
        )
        save_pressed = st.form_submit_button("Save watchlist", use_container_width=True)

    st.session_state.watchlist_assets = selected_watchlist
    if save_pressed:
        saved_watchlist = save_watchlist(selected_watchlist)
        st.session_state.watchlist_assets = saved_watchlist.get("asset_ids", selected_watchlist)
        st.success("Watchlist updated.")
    elif selected_watchlist != persisted_watchlist_assets:
        st.info("Review the selection and save when ready.")

    watchlist_df = latest_df.loc[latest_df["asset_id"].isin(selected_watchlist)].copy()
    if watchlist_df.empty:
        st.info("Add at least one asset to the watchlist to populate this view.")
        return

    watchlist_df = watchlist_df.sort_values("market_cap_usd", ascending=False)
    metric_cols = st.columns(min(len(watchlist_df), 3))
    for idx, (_, asset_row) in enumerate(watchlist_df.head(3).iterrows()):
        with metric_cols[idx]:
            render_card(
                f"{asset_row['symbol']} price",
                format_currency(asset_row["current_price_usd"]),
                format_percent(asset_row["price_change_percentage_24h"]),
            )

    watchlist_df["current_price_usd"] = watchlist_df["current_price_usd"].map(format_currency)
    watchlist_df["market_cap_usd"] = watchlist_df["market_cap_usd"].map(format_compact_currency)
    watchlist_df["total_volume_usd"] = watchlist_df["total_volume_usd"].map(format_compact_currency)
    watchlist_df["price_change_percentage_24h"] = watchlist_df["price_change_percentage_24h"].map(format_percent)
    st.dataframe(
        watchlist_df[
            ["symbol", "name", "current_price_usd", "price_change_percentage_24h", "market_cap_usd", "total_volume_usd"]
        ],
        use_container_width=True,
        hide_index=True,
    )


def render_alerts(alerts_payload: list[dict], asset_options: pd.DataFrame, asset_lookup: dict[str, str]) -> None:
    st.markdown('<div class="section-title">Alerts</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-copy">Rule-based signals from market behavior and feed health.</div>', unsafe_allow_html=True)

    alert_asset_filter = st.selectbox(
        "Filter alerts by asset",
        options=["All assets"] + asset_options["label"].tolist(),
    )
    filtered_alerts = alerts_payload
    if alert_asset_filter != "All assets":
        filtered_asset_id = asset_lookup[alert_asset_filter]
        filtered_alerts = fetch_alerts(filtered_asset_id)

    for alert in filtered_alerts:
        severity_class = "state-up" if alert["severity"] == "low" else "state-warn" if alert["severity"] == "medium" else "state-down"
        explanation_parts: list[str] = []
        observed_value = alert.get("observed_value")
        threshold_value = alert.get("threshold_value")
        high_threshold_value = alert.get("high_threshold_value")
        unit = alert.get("unit") or ""
        if observed_value is not None:
            explanation_parts.append(f"Observed: {observed_value:.2f}{unit}")
        if threshold_value is not None:
            explanation_parts.append(f"Threshold: {threshold_value:.2f}{unit}")
        if high_threshold_value is not None:
            explanation_parts.append(f"High: {high_threshold_value:.2f}{unit}")
        st.markdown(
            f"""
            <div class="panel">
                <div class="mini-row">
                    <span>{alert['title']}</span>
                    <span class="mono {severity_class}">{alert['severity']}</span>
                </div>
                <div class="section-copy" style="margin-top:0.75rem;margin-bottom:0;">{alert['message']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if explanation_parts:
            st.caption(" | ".join(explanation_parts))
        if alert.get("severity_reason"):
            st.caption(alert["severity_reason"])


def render_assets(latest_df: pd.DataFrame, selected_label: str, selected_asset_id: str, history_df: pd.DataFrame, history_analytics: dict | None, asset_alerts_payload: list[dict], pipeline_status: dict | None, pipeline_rows_fetched, pipeline_rows_inserted, market_status_label: str, latest_snapshot_at) -> None:
    st.markdown('<div class="section-title">Asset detail</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="section-copy">Recent behavior for <strong>{selected_label}</strong> across the selected window.</div>',
        unsafe_allow_html=True,
    )

    if history_df.empty:
        st.warning("No historical snapshots found for the selected asset yet.")
        return

    latest_point = history_df.iloc[-1]
    history_df["moving_average_5"] = history_df["current_price_usd"].rolling(window=5).mean()
    history_df["moving_average_10"] = history_df["current_price_usd"].rolling(window=10).mean()
    delta_price = history_analytics["window_change_usd"] if history_analytics else None
    delta_percent = history_analytics["window_change_pct"] if history_analytics else None

    asset_kpis = st.columns(4)
    with asset_kpis[0]:
        render_card("Selected asset", selected_asset_id, latest_point["name"])
    with asset_kpis[1]:
        render_card("Latest price", format_currency(latest_point["current_price_usd"]), latest_point["snapshot_at"].strftime("%H:%M UTC"))
    with asset_kpis[2]:
        render_card("Window change", format_currency(delta_price), format_percent(delta_percent))
    with asset_kpis[3]:
        volatility_value = history_analytics["rolling_volatility_pct"] if history_analytics else None
        volatility_copy = "Std. dev. of snapshot returns" if volatility_value is not None else f"{len(history_df)} points loaded"
        render_card(
            "Rolling volatility",
            format_percent(volatility_value) if volatility_value is not None else "n/a",
            volatility_copy,
        )

    chart_col, context_col = st.columns([1.45, 0.55])

    with chart_col:
        st.markdown('<div class="section-title">Price trajectory</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-copy">Price path across persisted snapshots.</div>', unsafe_allow_html=True)
        price_area = (
            alt.Chart(history_df)
            .mark_area(
                line={"color": "#295BFF", "strokeWidth": 2.8},
                color=alt.Gradient(
                    gradient="linear",
                    stops=[
                        alt.GradientStop(color="rgba(41,91,255,0.35)", offset=0),
                        alt.GradientStop(color="rgba(41,91,255,0.02)", offset=1),
                    ],
                    x1=1,
                    x2=1,
                    y1=1,
                    y2=0,
                ),
            )
            .encode(
                x=alt.X("snapshot_at:T", title="Snapshot time"),
                y=alt.Y("current_price_usd:Q", title="Price (USD)", scale=alt.Scale(zero=False)),
                tooltip=[
                    alt.Tooltip("snapshot_at:T", title="Snapshot"),
                    alt.Tooltip("current_price_usd:Q", title="Price", format=",.2f"),
                    alt.Tooltip("market_cap_usd:Q", title="Market cap", format=",.2f"),
                ],
            )
            .properties(height=360)
        )
        ma5_line = (
            alt.Chart(history_df.dropna(subset=["moving_average_5"]))
            .mark_line(color="#6EE7B7", strokeWidth=2)
            .encode(
                x="snapshot_at:T",
                y="moving_average_5:Q",
                tooltip=[alt.Tooltip("moving_average_5:Q", title="MA 5", format=",.2f")],
            )
        )
        ma10_line = (
            alt.Chart(history_df.dropna(subset=["moving_average_10"]))
            .mark_line(color="#F2B84B", strokeWidth=2, strokeDash=[5, 4])
            .encode(
                x="snapshot_at:T",
                y="moving_average_10:Q",
                tooltip=[alt.Tooltip("moving_average_10:Q", title="MA 10", format=",.2f")],
            )
        )
        st.altair_chart(price_area + ma5_line + ma10_line, use_container_width=True)

    with context_col:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Window summary</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-copy">Short reading of the selected period.</div>', unsafe_allow_html=True)
        direction_class = "state-up" if (delta_price or 0) >= 0 else "state-down"
        direction_word = "up" if (delta_price or 0) >= 0 else "down"
        st.markdown(
            f"""
            <div class="mini-row">
                <span>Price moved {direction_word} over the loaded window</span>
                <span class="mono {direction_class}">{format_currency(delta_price)}</span>
            </div>
            <div class="mini-row">
                <span>Relative change</span>
                <span class="mono {direction_class}">{format_percent(delta_percent)}</span>
            </div>
            <div class="mini-row">
                <span>Moving average 5</span>
                <span class="mono">{format_currency(history_analytics["moving_average_5"]) if history_analytics and history_analytics["moving_average_5"] is not None else "n/a"}</span>
            </div>
            <div class="mini-row">
                <span>Moving average 10</span>
                <span class="mono">{format_currency(history_analytics["moving_average_10"]) if history_analytics and history_analytics["moving_average_10"] is not None else "n/a"}</span>
            </div>
            <div class="mini-row">
                <span>Latest 24h source change</span>
                <span class="mono {'state-up' if latest_point['price_change_percentage_24h'] >= 0 else 'state-down'}">{format_percent(latest_point['price_change_percentage_24h'])}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Asset alerts</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-copy">Signals tied to the selected asset.</div>', unsafe_allow_html=True)
        for alert in asset_alerts_payload[:4]:
            severity_class = "state-up" if alert["severity"] == "low" else "state-warn" if alert["severity"] == "medium" else "state-down"
            st.markdown(
                f"""
                <div class="mini-row">
                    <span>{alert['title']}</span>
                    <span class="mono {severity_class}">{alert['severity']}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.caption(alert["message"])
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Feed health</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-copy">Operational signals for this view.</div>', unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="mini-row">
                <span>CoinGecko source</span>
                <span class="mono {'state-up' if pipeline_status and pipeline_status['status'] == 'success' else 'state-warn'}">{pipeline_status['status'] if pipeline_status else 'unknown'}</span>
            </div>
            <div class="mini-row">
                <span>Last successful update</span>
                <span class="mono">{pipeline_status['last_success_at'] if pipeline_status and pipeline_status['last_success_at'] else latest_snapshot_at.strftime('%H:%M:%S UTC')}</span>
            </div>
            <div class="mini-row">
                <span>Data freshness</span>
                <span class="mono {'state-up' if market_status_label == 'Live' else 'state-warn'}">{market_status_label}</span>
            </div>
            <div class="mini-row">
                <span>Rows fetched / inserted</span>
                <span class="mono">{pipeline_rows_fetched if pipeline_rows_fetched is not None else 'n/a'} / {pipeline_rows_inserted if pipeline_rows_inserted is not None else 'n/a'}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

        peer_rows = latest_df.copy()
        peer_rows["market_cap_rank"] = peer_rows["market_cap_usd"].rank(method="dense", ascending=False).astype(int)
        selected_peer = peer_rows.loc[peer_rows["asset_id"] == selected_asset_id].iloc[0]
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Peer comparison</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-copy">Selected asset against the tracked universe.</div>', unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="mini-row">
                <span>Market cap rank</span>
                <span class="mono">#{selected_peer['market_cap_rank']}</span>
            </div>
            <div class="mini-row">
                <span>Current market cap</span>
                <span class="mono">{format_compact_currency(selected_peer['market_cap_usd'])}</span>
            </div>
            <div class="mini-row">
                <span>Current 24h volume</span>
                <span class="mono">{format_compact_currency(selected_peer['total_volume_usd'])}</span>
            </div>
            <div class="mini-row">
                <span>24h move vs peers</span>
                <span class="mono {'state-up' if selected_peer['price_change_percentage_24h'] >= 0 else 'state-down'}">{format_percent(selected_peer['price_change_percentage_24h'])}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    volume_chart = (
        alt.Chart(history_df)
        .mark_bar(color="#18B67A", cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X("snapshot_at:T", title="Snapshot time"),
            y=alt.Y("total_volume_usd:Q", title="Volume (USD)"),
            tooltip=[
                alt.Tooltip("snapshot_at:T", title="Snapshot"),
                alt.Tooltip("total_volume_usd:Q", title="Volume", format=",.2f"),
            ],
        )
        .properties(height=220)
    )
    st.markdown('<div class="section-title">Volume pulse</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-copy">Volume over the same window.</div>', unsafe_allow_html=True)
    st.altair_chart(volume_chart, use_container_width=True)


def render_settings(settings, pipeline_last_error, asset_options: pd.DataFrame) -> None:
    st.markdown('<div class="section-title">Settings</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-copy">Current runtime configuration for the local MVP.</div>', unsafe_allow_html=True)

    settings_rows = [
        ("API base URL", settings.api_base_url),
        ("Tracked assets", ", ".join(settings.asset_id_list)),
        ("Ingestion interval", f"{settings.ingestion_interval_seconds}s"),
        ("Default alert move threshold", f"{settings.alert_price_move_pct:.2f}%"),
        ("Default volatility threshold", f"{settings.alert_volatility_pct:.2f}%"),
        ("Default volume spike ratio", f"{settings.alert_volume_spike_ratio:.2f}x"),
    ]
    if pipeline_last_error:
        settings_rows.append(("Last pipeline error", pipeline_last_error))

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    for label, value in settings_rows:
        st.markdown(
            f"""
            <div class="mini-row">
                <span>{label}</span>
                <span class="mono">{value}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="section-title">Alert thresholds</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-copy">Asset-specific overrides stored in PostgreSQL. Leave a field empty to remove the override and use the default.</div>', unsafe_allow_html=True)

    selected_label = st.selectbox(
        "Choose asset for alert rules",
        options=asset_options["label"].tolist(),
        key="settings_asset_rules",
    )
    selected_asset_id = asset_options.loc[asset_options["label"] == selected_label, "asset_id"].iloc[0]
    rules_payload = fetch_alert_rules(selected_asset_id)
    default_rules = rules_payload["defaults"]
    override_rules = rules_payload["overrides"]
    effective_rules = rules_payload["effective"]

    with st.form(f"alert_rules_form_{selected_asset_id}"):
        price_move_pct = st.text_input(
            "Price move threshold (%)",
            value="" if override_rules["price_move_pct"] is None else str(override_rules["price_move_pct"]),
            help=f"Default: {default_rules['price_move_pct']:.2f}%",
        )
        price_move_high_pct = st.text_input(
            "High price move threshold (%)",
            value="" if override_rules["price_move_high_pct"] is None else str(override_rules["price_move_high_pct"]),
            help=f"Default: {default_rules['price_move_high_pct']:.2f}%",
        )
        volatility_pct = st.text_input(
            "Volatility threshold (%)",
            value="" if override_rules["volatility_pct"] is None else str(override_rules["volatility_pct"]),
            help=f"Default: {default_rules['volatility_pct']:.2f}%",
        )
        volume_spike_ratio = st.text_input(
            "Volume spike ratio",
            value="" if override_rules["volume_spike_ratio"] is None else str(override_rules["volume_spike_ratio"]),
            help=f"Default: {default_rules['volume_spike_ratio']:.2f}x",
        )
        volume_spike_high_ratio = st.text_input(
            "High volume spike ratio",
            value="" if override_rules["volume_spike_high_ratio"] is None else str(override_rules["volume_spike_high_ratio"]),
            help=f"Default: {default_rules['volume_spike_high_ratio']:.2f}x",
        )
        button_cols = st.columns(2)
        with button_cols[0]:
            save_pressed = st.form_submit_button("Save alert rules", use_container_width=True)
        with button_cols[1]:
            reset_pressed = st.form_submit_button("Reset to defaults", use_container_width=True)

    if reset_pressed:
        saved_payload = save_alert_rules(
            selected_asset_id,
            payload={
                "price_move_pct": None,
                "price_move_high_pct": None,
                "volatility_pct": None,
                "volume_spike_ratio": None,
                "volume_spike_high_ratio": None,
            },
        )
        effective_rules = saved_payload["effective"]
        override_rules = saved_payload["overrides"]
        st.success("Asset alert rules reset to defaults.")
    elif save_pressed:
        try:
            saved_payload = save_alert_rules(
                selected_asset_id,
                payload={
                    "price_move_pct": float(price_move_pct) if price_move_pct.strip() else None,
                    "price_move_high_pct": float(price_move_high_pct) if price_move_high_pct.strip() else None,
                    "volatility_pct": float(volatility_pct) if volatility_pct.strip() else None,
                    "volume_spike_ratio": float(volume_spike_ratio) if volume_spike_ratio.strip() else None,
                    "volume_spike_high_ratio": float(volume_spike_high_ratio) if volume_spike_high_ratio.strip() else None,
                },
            )
            effective_rules = saved_payload["effective"]
            override_rules = saved_payload["overrides"]
            st.success("Alert rules updated.")
        except ValueError:
            st.error("Enter numeric values or leave the field empty.")

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="mini-row">
            <span>Effective move threshold</span>
            <span class="mono">{effective_rules['price_move_pct']:.2f}%</span>
        </div>
        <div class="mini-row">
            <span>Effective high move threshold</span>
            <span class="mono">{effective_rules['price_move_high_pct']:.2f}%</span>
        </div>
        <div class="mini-row">
            <span>Effective volatility threshold</span>
            <span class="mono">{effective_rules['volatility_pct']:.2f}%</span>
        </div>
        <div class="mini-row">
            <span>Effective volume spike ratio</span>
            <span class="mono">{effective_rules['volume_spike_ratio']:.2f}x</span>
        </div>
        <div class="mini-row">
            <span>Effective high volume spike ratio</span>
            <span class="mono">{effective_rules['volume_spike_high_ratio']:.2f}x</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)
