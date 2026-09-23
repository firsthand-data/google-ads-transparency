"""New, stopped and long-running ads per competitor for the last 7 days. Schedule weekly."""
from google_ads_transparency import Client

competitors = ["hubspot.com", "salesforce.com", "zoho.com"]
result = Client().run(domains=competitors, report_days=7, max_total_charge_usd=1.0)

for row in result.report:
    print(row)
