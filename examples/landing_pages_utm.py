"""Landing pages and UTM campaigns of a competitor's video ads (the format where Google publishes them)."""
from collections import Counter

from google_ads_transparency import Client

result = Client().run(domains=["hubspot.com"], ad_format="video", details=True,
                      max_details=50, max_total_charge_usd=0.5)

campaigns = Counter(ad.get("utm_campaign") for ad in result.ads if ad.get("utm_campaign"))
pages = Counter((ad.get("destination_url") or "").split("?")[0] for ad in result.ads if ad.get("destination_url"))
print("UTM campaigns:", campaigns.most_common(10))
print("Landing pages:", pages.most_common(10))
