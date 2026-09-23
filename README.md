# google-ads-transparency

Competitor ads from the [Google Ads Transparency Center](https://adstransparency.google.com/) in Python:
every ad a domain, advertiser or brand is running, the ad copy (also read off the picture of text ads with
OCR), landing URLs and UTM tags where Google publishes them, and a new / stopped / long-running report
for any period.

This package is a thin client for the Apify Actor
[Google Ads Transparency Report](https://apify.com/firsthand/google-ads-transparency-report). The Actor
does the scraping, proxies and retries on Apify's servers; this package starts it and hands you the
tables as Python lists of dicts.

```bash
pip install google-ads-transparency
```

## Quick start

You need an Apify API token: sign up at [apify.com](https://apify.com), then copy the token from
**Console > Settings > Integrations**.

```bash
export APIFY_TOKEN=apify_api_...
```

```python
from google_ads_transparency import Client

result = Client().run(domains=["hubspot.com"], country="US", details=True, ocr=True, max_details=20)

print(result.status, len(result.ads))
for ad in result.ads[:5]:
    print(ad["format"], ad["last_shown"], ad["headline"], ad["destination_url"])
```

A run takes from a few seconds (the ad list only) to minutes (ad text for hundreds of ads).

## What you get back

`Client.run()` returns a `Result`:

| Attribute | One row per | What is in it |
|---|---|---|
| `ads` | ad creative | domain, advertiser, format, first and last shown date, days shown, image link, Transparency Center link; with `details=True`: countries, impression ranges, headline, description, visible URL, landing URL and UTM tags |
| `targets` | domain, advertiser or brand you asked for | status `ok`, `empty`, `partial`, `failed` or `skipped` and the reason |
| `report` | competitor | ads running now, new, stopped and long-running in the period (needs `report_days`) |
| `messages` | unique ad message | headline and description, how many creatives use it, formats, UTM campaigns |

Plus `status`, `status_message`, `ok`, `run_id`, `console_url` and `charged_events`.

**An empty `ads` list is not always "no ads".** Check `result.ok` and `result.targets`: a target Google
refused is `failed`, one the run did not reach (cost or time limit) is `skipped`, and only `empty` means
the Transparency Center answered and has nothing.

## Arguments

| Argument | Actor field | Meaning |
|---|---|---|
| `domains` | `domains` | competitor domains, e.g. `"hubspot.com"` |
| `advertiser_ids` | `advertiserIds` | Transparency Center advertiser ids (`AR...`) |
| `links` | `startUrls` | Transparency Center links |
| `brands` | `searchQueries` | brand names, resolved to advertisers |
| `advertisers_per_brand` | `maxAdvertisersPerQuery` | how many advertisers one brand name expands into (default 3) |
| `country` | `country` | two-letter code, one per run |
| `ad_format` | `adFormat` | `all`, `text`, `image`, `video` |
| `platform` | `platform` | `all`, `search`, `youtube`, `shopping`, `maps`, `play` |
| `shown_after`, `shown_before` | `shownAfter`, `shownBefore` | date or `"YYYY-MM-DD"` |
| `max_ads` | `maxAdsPerTarget` | cap per domain or advertiser (default 200) |
| `details` | `adDetails` | fetch ad text, countries and impressions |
| `ocr` | `ocrTextAds` | read the text off pictures of text ads |
| `max_details` | `maxDetailsPerTarget` | how many ads per target get details (cost cap) |
| `report_days`, `long_runner_days` | `reportDays`, `longRunnerDays` | competitor report period and "long-running" threshold |
| `workers` | `enrichWorkers` | ads fetched at the same time (1-16) |
| `max_total_charge_usd` | run option | hard cost cap for this run |

Unset arguments use the Actor's defaults. Bad values raise `ConfigError` before anything is started or paid for.

## Weekly competitor report

```python
result = Client().run(domains=["hubspot.com", "salesforce.com", "zoho.com"], report_days=7)
for row in result.report:
    print(row)
```

Run it on a schedule (cron, Airflow, n8n) every 7 days: the Actor reads only the recent part of each
list, so a weekly run stays cheap even for a large advertiser.

No Python? There is a ready [n8n template](n8n/) that posts this digest to Slack every Monday.

## Cost

You pay Apify per event, only for what the run returns. Prices on the free plan (lower on paid plans):

| Event | Price |
|---|---|
| Actor start | $0.0035 per run |
| Ad row | $0.0005 |
| Ad details (countries, impressions) | $0.0002 |
| Ad text from the source | $0.0026 |
| Ad text read by OCR | $0.0013 |

Current prices on all plans are on the [Actor page](https://apify.com/firsthand/google-ads-transparency-report).
Use `max_ads`, `max_details` and `max_total_charge_usd` to stay within budget.

## Migrating from `Google-Ads-Transparency-Scraper`

That package has not been updated since July 2023. The same tasks with this one:

| Old | New |
|---|---|
| `GoogleAds(region="pk", proxy=...)` | `Client()`; pass `country="PK"` to `run()`; proxies are handled by the Actor |
| `get_creative_Ids("Google LLC", 200)` | `run(brands=["Google LLC"], max_ads=200)`, ids in `ad["creative_id"]` |
| `get_detailed_ad(advertiser_id, creative_id)` | `run(advertiser_ids=[advertiser_id], details=True, ocr=True)`, one row per creative |
| `get_breif_ads(...)` | `run(...)` without `details` |
| looking up an advertiser by domain | `run(domains=["example.com"])` |
| `show_regions_list()` | any two-letter country code |

The difference in shape: the old package made one request per ad; here one `run()` returns all ads of
all your targets at once, with statuses for each target.

## Limitations

These come from what Google publishes:

- Most text ads are archived only as a picture; with `ocr=True` their text is read from it
  (`text_source == "ocr"`).
- Text ads carry no landing URL at all; video ads mostly do, image ads rarely.
- The Transparency Center searches by advertiser or domain only, not by keyword.
- One country per run.

## License

MIT. This package is not affiliated with Google.
