def to_float(value: object) -> float:
    if value is None:
        return 0.0
    return float(value)


def format_currency(value: object) -> str:
    return f"${to_float(value):,.2f}"


def format_compact_currency(value: object) -> str:
    numeric = abs(to_float(value))
    sign = "-" if to_float(value) < 0 else ""
    if numeric >= 1_000_000_000_000:
        return f"{sign}${numeric / 1_000_000_000_000:,.2f}T"
    if numeric >= 1_000_000_000:
        return f"{sign}${numeric / 1_000_000_000:,.2f}B"
    if numeric >= 1_000_000:
        return f"{sign}${numeric / 1_000_000:,.2f}M"
    if numeric >= 1_000:
        return f"{sign}${numeric / 1_000:,.2f}K"
    return f"{sign}${numeric:,.2f}"


def format_percent(value: object) -> str:
    return f"{to_float(value):.2f}%"


def status_chip(age_seconds: float, ingestion_interval_seconds: int) -> tuple[str, str]:
    if age_seconds <= ingestion_interval_seconds * 2:
        return "Live", "chip chip-live"
    return "Delayed", "chip chip-delayed"
