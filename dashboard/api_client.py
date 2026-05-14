import requests
import streamlit as st

from app.core.config import get_settings

settings = get_settings()


def _fetch(url: str, params: dict | None = None) -> dict | list[dict]:
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    return response.json()


def _put(url: str, payload: dict) -> dict:
    response = requests.put(url, json=payload, timeout=10)
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=60)
def fetch_health() -> dict:
    return _fetch(f"{settings.api_base_url}/api/v1/health")  # type: ignore[return-value]


@st.cache_data(ttl=60)
def fetch_summary() -> dict:
    return _fetch(f"{settings.api_base_url}/api/v1/market/summary")  # type: ignore[return-value]


@st.cache_data(ttl=60)
def fetch_latest() -> list[dict]:
    return _fetch(f"{settings.api_base_url}/api/v1/market/latest")  # type: ignore[return-value]


@st.cache_data(ttl=60)
def fetch_alerts(asset_id: str | None = None) -> list[dict]:
    params = {"asset_id": asset_id} if asset_id else None
    return _fetch(f"{settings.api_base_url}/api/v1/market/alerts", params=params)  # type: ignore[return-value]


@st.cache_data(ttl=60)
def fetch_history(asset_id: str, limit: int) -> dict:
    return _fetch(f"{settings.api_base_url}/api/v1/market/history/{asset_id}", params={"limit": limit})  # type: ignore[return-value]


@st.cache_data(ttl=60)
def fetch_watchlist() -> dict:
    return _fetch(f"{settings.api_base_url}/api/v1/market/watchlist")  # type: ignore[return-value]


def save_watchlist(asset_ids: list[str]) -> dict:
    response = _put(f"{settings.api_base_url}/api/v1/market/watchlist", payload={"asset_ids": asset_ids})
    fetch_watchlist.clear()
    return response


@st.cache_data(ttl=60)
def fetch_alert_rules(asset_id: str) -> dict:
    return _fetch(f"{settings.api_base_url}/api/v1/market/alert-rules/{asset_id}")  # type: ignore[return-value]


def save_alert_rules(asset_id: str, payload: dict) -> dict:
    response = _put(f"{settings.api_base_url}/api/v1/market/alert-rules/{asset_id}", payload=payload)
    fetch_alert_rules.clear()
    return response
