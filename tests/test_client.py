import datetime as dt
from types import SimpleNamespace

import pytest

from google_ads_transparency import Client, ConfigError, build_input


class FakeApify:
    """Stands in for ApifyClient: records the call and serves canned storages."""

    def __init__(self, status="SUCCEEDED", output=None, datasets=None):
        self.calls = []
        self.status = status
        self.output = output
        self.datasets = datasets or {}

    def actor(self, actor_id):
        def call(**kw):
            self.calls.append((actor_id, kw))
            return SimpleNamespace(id="run1", status=SimpleNamespace(value=self.status),
                                   status_message="done", charged_event_counts={"ad": 0},
                                   default_dataset_id="ads-ds", default_key_value_store_id="kv")
        return SimpleNamespace(call=call)

    def run(self, run_id):
        return SimpleNamespace(get=lambda: SimpleNamespace(charged_event_counts=self.final_counts))

    final_counts = {"ad": 2}

    def dataset(self, ds_id):
        return SimpleNamespace(iterate_items=lambda: iter(self.datasets.get(ds_id, [])))

    def key_value_store(self, kv_id):
        return SimpleNamespace(get_record=lambda key: {"key": key, "value": self.output} if self.output else None)


def test_maps_python_names_to_actor_fields():
    got = build_input(domains="hubspot.com", brands=["Canva"], country="us", ad_format="video",
                      shown_after=dt.date(2026, 9, 1), details=True, ocr=True, max_details=20,
                      report_days=7, max_ads=50)
    assert got == {"domains": ["hubspot.com"], "searchQueries": ["Canva"], "country": "US",
                   "adFormat": "video", "shownAfter": "2026-09-01", "adDetails": True, "ocrTextAds": True,
                   "maxDetailsPerTarget": 20, "reportDays": 7, "maxAdsPerTarget": 50}


def test_unset_arguments_leave_actor_defaults():
    assert build_input(advertiser_ids=["AR123"]) == {"advertiserIds": ["AR123"]}


@pytest.mark.parametrize("kw", [
    {},
    {"domains": []},
    {"domains": ["a.com"], "country": "USA"},
    {"domains": ["a.com"], "ad_format": "banner"},
    {"domains": ["a.com"], "platform": "tiktok"},
    {"domains": ["a.com"], "report_days": 0},
    {"domains": ["a.com"], "workers": 17},
    {"domains": ["a.com"], "max_ads": 0},
    {"domains": ["a.com"], "shown_after": "01.09.2026"},
])
def test_bad_input_fails_before_any_run(kw):
    with pytest.raises(ConfigError):
        build_input(**kw)


def test_missing_token_is_a_clear_error(monkeypatch):
    monkeypatch.delenv("APIFY_TOKEN", raising=False)
    with pytest.raises(ConfigError, match="APIFY_TOKEN"):
        Client()


def test_run_collects_all_four_tables():
    fake = FakeApify(
        output={"tables": {"targets": {"dataset_id": "t"}, "report": {"dataset_id": "r"},
                           "messages": {"dataset_id": "m"}}},
        datasets={"ads-ds": [{"creative_id": "CR1"}, {"creative_id": "CR2"}], "t": [{"target": "a.com"}],
                  "r": [{"advertiser": "A"}], "m": [{"headline": "H"}]})
    res = Client(apify_client=fake).run(domains=["a.com"], max_total_charge_usd=0.5)
    assert res.ok and res.run_id == "run1"
    assert [a["creative_id"] for a in res.ads] == ["CR1", "CR2"]
    assert res.targets == [{"target": "a.com"}] and res.report and res.messages
    assert res.charged_events == {"ad": 2}
    actor_id, kw = fake.calls[0]
    assert actor_id == "firsthand/google-ads-transparency-report"
    assert kw["run_input"] == {"domains": ["a.com"]}
    assert str(kw["max_total_charge_usd"]) == "0.5"


def test_failed_run_still_returns_targets_with_reasons():
    fake = FakeApify(status="FAILED", output={"tables": {"targets": {"dataset_id": "t"}}},
                     datasets={"t": [{"target": "a.com", "status": "failed", "reason": "refused"}]})
    res = Client(apify_client=fake).run(domains=["a.com"])
    assert not res.ok
    assert res.ads == [] and res.targets[0]["status"] == "failed"


def test_run_without_output_record_has_empty_extra_tables():
    fake = FakeApify(output=None, datasets={"ads-ds": [{"creative_id": "CR1"}]})
    res = Client(apify_client=fake).run(domains=["a.com"])
    assert res.ads and res.targets == [] and res.report == [] and res.messages == []
