"""Every ad a competitor runs in one country, with ad copy for the 20 most recent."""
from google_ads_transparency import Client

result = Client().run(domains=["hubspot.com"], country="US", details=True, ocr=True,
                      max_details=20, max_total_charge_usd=0.5)

for target in result.targets:
    print(target)
print(f"{len(result.ads)} ads, run status {result.status}")
for ad in result.ads[:20]:
    print(f'{ad["format"]:5} {ad["last_shown"][:10]}  {ad.get("headline") or "(" + str(ad.get("details_status")) + ")"}')
