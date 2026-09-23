"""Thin Python client for the Google Ads Transparency Report Actor on Apify."""
from __future__ import annotations

import datetime as _dt
import os
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Iterable

from apify_client import ApifyClient

ACTOR_ID = "firsthand/google-ads-transparency-report"
ACTOR_URL = "https://apify.com/firsthand/google-ads-transparency-report"

AD_FORMATS = ("all", "text", "image", "video")
PLATFORMS = ("all", "search", "youtube", "shopping", "maps", "play")
EXTRA_TABLES = ("targets", "report", "messages")


class ConfigError(ValueError):
    """Bad arguments or missing token; raised before anything is started or paid for."""


@dataclass
class Result:
    """Everything one Actor run returned.

    ``status`` is the Apify run status. A run can fail and still carry useful
    rows in ``targets``: the Actor fails when none of your targets could be read,
    and ``targets`` then says why for each one. Check ``ok`` before trusting
    that an empty ``ads`` list means "no ads".
    """

    run_id: str
    status: str
    status_message: str | None
    ads: list[dict] = field(default_factory=list)
    targets: list[dict] = field(default_factory=list)
    report: list[dict] = field(default_factory=list)
    messages: list[dict] = field(default_factory=list)
    charged_events: dict[str, int] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status == "SUCCEEDED"

    @property
    def console_url(self) -> str:
        return f"https://console.apify.com/view/runs/{self.run_id}"


def _list(name: str, value: str | Iterable[str] | None) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, str):
        return [value]
    items = [str(v).strip() for v in value if str(v).strip()]
    if not items:
        raise ConfigError(f"{name} is empty")
    return items


def _date(name: str, value: str | _dt.date | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, _dt.date):
        return value.isoformat()
    try:
        return _dt.date.fromisoformat(value).isoformat()
    except ValueError:
        raise ConfigError(f"{name} must be a date like 2026-09-01, got {value!r}") from None


def build_input(
    *,
    domains: str | Iterable[str] | None = None,
    advertiser_ids: str | Iterable[str] | None = None,
    links: str | Iterable[str] | None = None,
    brands: str | Iterable[str] | None = None,
    advertisers_per_brand: int | None = None,
    country: str | None = None,
    ad_format: str | None = None,
    platform: str | None = None,
    shown_after: str | _dt.date | None = None,
    shown_before: str | _dt.date | None = None,
    fast_period_filter: bool | None = None,
    max_ads: int | None = None,
    details: bool | None = None,
    ocr: bool | None = None,
    max_details: int | None = None,
    workers: int | None = None,
    report_days: int | None = None,
    long_runner_days: int | None = None,
    proxy: dict | None = None,
) -> dict[str, Any]:
    """Map Python arguments to the Actor's input fields. Unset arguments use the Actor's defaults."""
    targets = {
        "domains": _list("domains", domains),
        "advertiserIds": _list("advertiser_ids", advertiser_ids),
        "startUrls": _list("links", links),
        "searchQueries": _list("brands", brands),
    }
    if not any(targets.values()):
        raise ConfigError("give at least one of domains, advertiser_ids, links or brands")
    if country is not None and (len(country) != 2 or not country.isalpha()):
        raise ConfigError(f"country must be a two-letter code like 'US', got {country!r}")
    if ad_format is not None and ad_format not in AD_FORMATS:
        raise ConfigError(f"ad_format must be one of {AD_FORMATS}, got {ad_format!r}")
    if platform is not None and platform not in PLATFORMS:
        raise ConfigError(f"platform must be one of {PLATFORMS}, got {platform!r}")
    if report_days is not None and not 1 <= report_days <= 365:
        raise ConfigError("report_days must be between 1 and 365")
    if workers is not None and not 1 <= workers <= 16:
        raise ConfigError("workers must be between 1 and 16")
    for name, value in (("max_ads", max_ads), ("max_details", max_details),
                        ("advertisers_per_brand", advertisers_per_brand),
                        ("long_runner_days", long_runner_days)):
        if value is not None and value < 1:
            raise ConfigError(f"{name} must be 1 or more")

    raw = {
        **targets,
        "maxAdvertisersPerQuery": advertisers_per_brand,
        "country": country.upper() if country else None,
        "adFormat": ad_format,
        "platform": platform,
        "shownAfter": _date("shown_after", shown_after),
        "shownBefore": _date("shown_before", shown_before),
        "fastPeriodFilter": fast_period_filter,
        "maxAdsPerTarget": max_ads,
        "adDetails": details,
        "ocrTextAds": ocr,
        "maxDetailsPerTarget": max_details,
        "enrichWorkers": workers,
        "reportDays": report_days,
        "longRunnerDays": long_runner_days,
        "proxyConfiguration": proxy,
    }
    return {k: v for k, v in raw.items() if v is not None}


class Client:
    """Run the Actor and collect its four tables.

    >>> from google_ads_transparency import Client
    >>> result = Client().run(domains=["hubspot.com"], country="US", details=True, ocr=True)
    >>> result.ads[0]["headline"]
    """

    def __init__(self, token: str | None = None, *, actor_id: str = ACTOR_ID, apify_client: Any = None):
        if apify_client is None:
            token = token or os.environ.get("APIFY_TOKEN")
            if not token:
                raise ConfigError(
                    "no Apify API token: pass Client(token=...) or set APIFY_TOKEN. "
                    "Get one at https://console.apify.com/settings/integrations")
            apify_client = ApifyClient(token)
        self._apify = apify_client
        self.actor_id = actor_id

    def run(
        self,
        *,
        max_total_charge_usd: float | None = None,
        memory_mbytes: int | None = None,
        timeout: _dt.timedelta | None = None,
        **params: Any,
    ) -> Result:
        """Start one Actor run, wait for it and read all its tables.

        Keyword arguments are those of :func:`build_input`. ``max_total_charge_usd``
        caps what this run may cost you; at the cap the Actor stops and marks the
        targets it did not read as ``skipped``.
        """
        run_input = build_input(**params)
        run = self._apify.actor(self.actor_id).call(
            run_input=run_input,
            max_total_charge_usd=Decimal(str(max_total_charge_usd)) if max_total_charge_usd is not None else None,
            memory_mbytes=memory_mbytes,
            run_timeout=timeout,
            logger=None,
        )
        if run is None:
            raise RuntimeError("Apify returned no run object")
        status = getattr(run.status, "value", run.status)
        result = Result(
            run_id=run.id,
            status=str(status),
            status_message=run.status_message,
            charged_events=dict(run.charged_event_counts or {}),
        )
        result.ads = list(self._apify.dataset(run.default_dataset_id).iterate_items())
        record = self._apify.key_value_store(run.default_key_value_store_id).get_record("OUTPUT")
        tables = ((record or {}).get("value") or {}).get("tables") or {}
        for name in EXTRA_TABLES:
            ds_id = (tables.get(name) or {}).get("dataset_id")
            if ds_id:
                setattr(result, name, list(self._apify.dataset(ds_id).iterate_items()))
        # The run object call() returns right at the finish carries stale
        # chargedEventCounts (seen live: ad 0 while the run had charged 5).
        final = self._apify.run(run.id).get()
        if final is not None and final.charged_event_counts:
            result.charged_events = dict(final.charged_event_counts)
        return result
