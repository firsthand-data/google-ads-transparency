# n8n template: weekly competitor Google Ads digest

[Send a weekly digest of competitors' Google Ads to Slack.json](Send%20a%20weekly%20digest%20of%20competitors'%20Google%20Ads%20to%20Slack.json)

Every Monday the workflow reads your competitors' ads from the Google Ads Transparency Center and posts
one message to Slack: ads running now, new and stopped ads for the week per competitor, which
advertisers changed something, and examples of new ads.

```
Every Monday 8:00 / Run now
  -> Settings (competitor domains, country, period, ad text on/off)
  -> Run Google Ads Transparency Actor   (HTTP Request, Apify API run-sync)
  -> Get report table                    (HTTP Request, Apify dataset)
  -> Build digest                        (Code)
  -> Post to Slack
```

No community nodes needed: the Actor is called with the built-in HTTP Request node.

## Setup

1. Import the JSON (Workflows > Import from file).
2. Create an Apify account and copy the API token from Console > Settings > Integrations.
3. Create a **Header Auth** credential: name `Authorization`, value `Bearer <your token>`. Restricting it
   to the domain `api.apify.com` is a good idea. Select it in both HTTP Request nodes.
4. Edit **Settings**: competitor domains (comma separated), optional two-letter country.
5. Connect Slack in the last node and pick a channel. Or replace it with Gmail, Telegram or Google Sheets:
   the digest is in `{{ $json.text }}`.

## Cost

Apify charges per result: about $0.0005 per ad row and $0.0035 per run on the free plan. With ad text off
(the default) a weekly run on three competitors costs a few cents. `fetchAdText` adds headlines for the
20 most recent ads per competitor, up to about $0.004 per ad.

## Tested

On a self-hosted n8n, 23.09.2026: live run on two competitors, 8 s without ad text and 119 s with it,
all nodes succeeded.

`build_template.py` regenerates the workflow from code; the JSON here is the version exported back from
n8n after the test.
