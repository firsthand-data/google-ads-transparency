---
name: google-ads-competitor-research
description: Research a competitor's Google ads from the Google Ads Transparency Center - every ad a domain, advertiser or brand runs, ad copy (including text read off ad pictures), landing URLs and UTM tags, countries, and a new/stopped/long-running report for a period. Use when the user asks what ads a company runs on Google, wants competitor ad copy or messaging, landing pages or UTM campaigns of competitor ads, or a weekly competitor ad report. Needs an Apify API token (APIFY_TOKEN).
---

# Google Ads competitor research

Data comes from the public [Google Ads Transparency Center](https://adstransparency.google.com/) through
the Apify Actor `firsthand/google-ads-transparency-report`. Each run costs the user money on Apify, so
confirm scope (how many competitors, whether ad text is needed) before running anything large.

## How to run

Preferred: the Python client.

```bash
pip install google-ads-transparency
```

```python
from google_ads_transparency import Client
r = Client().run(domains=["hubspot.com"], country="US", details=True, ocr=True,
                 max_details=20, max_total_charge_usd=1.0)
```

Without Python, call the Actor over HTTP:

```bash
curl -X POST "https://api.apify.com/v2/acts/firsthand~google-ads-transparency-report/run-sync-get-dataset-items" \
  -H "Authorization: Bearer $APIFY_TOKEN" -H "Content-Type: application/json" \
  -d '{"domains": ["hubspot.com"], "maxAdsPerTarget": 50}'
```

## Choosing inputs

- Who: `domains` (best default), `advertiser_ids` (`AR...`), `links` (Transparency Center URLs) or
  `brands` (names, resolved to advertisers; `advertisers_per_brand` caps the expansion).
- Where and what: `country` (two letters, one per run), `ad_format` (`text`, `image`, `video`),
  `platform` (`search`, `youtube`, `shopping`, `maps`, `play`), `shown_after` / `shown_before`.
- Ad copy costs most. Keep `details=False` for "how many ads, since when" questions. For copy, set
  `details=True, ocr=True` and cap with `max_details` (ads per target that get text).
- Weekly monitoring: `report_days=7` and read `result.report`.
- Always pass `max_total_charge_usd` when the user has not given a budget.

## Reading results

- `result.ads`: one row per creative. Key fields: `format`, `first_shown`, `last_shown`, `days_shown`,
  `headline`, `description`, `display_url`, `destination_url`, `utm_campaign`, `regions`,
  `text_source` (`ocr` means read from the picture), `details_status`, `ocr_status`.
- `result.targets`: status per requested target. `empty` means Google has no ads for it; `failed`
  means Google refused (nothing is known, do not report "no ads"); `partial` means the list was cut
  by a limit; `skipped` means the run did not get to it.
- An empty cell has a reason in `details_status` / `ocr_status` (`off`, `skipped: ...`, `failed`).
  Report the reason, never "the ad has no text".
- `result.messages`: unique ad messages with creative counts; good for "what does the competitor say".

## Facts to state correctly

- Text ads carry no landing URL in the Transparency Center; video ads mostly do, image ads rarely.
- There is no keyword search across all advertisers; research starts from a company, domain or brand.
- Impression ranges exist only for some ads, mostly shown in the EU.
