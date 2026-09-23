"""Builds the n8n workflow JSON for the weekly competitor Google Ads digest.

Kept as code so the template is reproducible; the file that ships is the one
exported back from n8n after a live test.
"""
import json
import sys

ACTOR = "firsthand~google-ads-transparency-report"

DIGEST_JS = r"""
// Turns the Actor's report table into one Slack message.
const rows = $input.all().map(i => i.json).filter(r => r && r.target);
const days = $('Settings').first().json.reportDays;
if (!rows.length) {
  return [{ json: { text: `Google Ads competitor digest: the run returned no report rows. Check the run in Apify Console.` } }];
}
// The report has one row per advertiser found on a domain (the brand itself,
// plus resellers and agencies); the digest sums them per competitor.
const sum = (rs, k) => rs.some(r => r[k] === null || r[k] === undefined) ? null : rs.reduce((s, r) => s + r[k], 0);
const fmt = n => n === null ? 'n/a' : n;
const byTarget = {};
for (const r of rows) (byTarget[r.target] = byTarget[r.target] || []).push(r);
const lines = [`*Google Ads competitor digest, last ${days} days*`];
for (const [target, rs] of Object.entries(byTarget)) {
  const failed = rs.filter(r => r.status === 'failed' || r.status === 'skipped');
  if (failed.length === rs.length) {
    lines.push(`\n*${target}*: not read (${failed[0].status}); ${failed[0].incomplete_reason || 'see the run in Apify Console'}`);
    continue;
  }
  const ok = rs.filter(r => !failed.includes(r));
  lines.push(`\n*${target}*: ${fmt(sum(ok, 'active_now'))} ads running now, ${fmt(sum(ok, 'new_in_period'))} new, ${fmt(sum(ok, 'stopped_in_period'))} stopped (${ok.length} advertiser${ok.length === 1 ? '' : 's'})`);
  for (const r of ok.filter(r => (r.new_in_period || 0) + (r.stopped_in_period || 0) > 0)
                    .sort((a, b) => (b.new_in_period || 0) - (a.new_in_period || 0)).slice(0, 5)) {
    lines.push(`  ${r.advertiser_name || 'unknown advertiser'}: ${r.new_in_period} new, ${r.stopped_in_period} stopped`);
    for (const ex of (r.new_examples || []).slice(0, 2)) {
      const text = ex.headline ? `"${ex.headline}"` : '(ad text not fetched)';
      lines.push(`    new ${ex.format} ${text}, first shown ${String(ex.first_shown).slice(0, 10)}`);
    }
  }
  const why = [...new Set(ok.filter(r => r.complete === false).map(r => r.incomplete_reason))];
  if (why.length) lines.push(`  _incomplete: ${why.join('; ')}_`);
}
return [{ json: { text: lines.join('\n') } }];
""".strip()

NOTE = """## Weekly competitor Google Ads digest

Every Monday, get one Slack message that tells you what your competitors changed in their Google Ads: how many ads each one runs, which ads are new this week, which were stopped, and examples of the new ones. Built for PPC managers, marketing teams and agencies who watch a set of competitors and don't want to check the Google Ads Transparency Center by hand.

### How it works
1. A schedule (Monday 8:00) or a manual run starts the workflow.
2. **Settings** holds your competitor domains, an optional country and the report period.
3. An HTTP Request runs the Google Ads Transparency Report Actor on Apify. It reads each competitor's ads from the Google Ads Transparency Center and builds a new / stopped / running report.
4. A second HTTP Request fetches that report, and a Code node turns it into one digest per competitor.
5. The digest is posted to a Slack channel.

### Setup (about 5 minutes)
1. Create an Apify account and copy your API token (Console > Settings > Integrations).
2. Add a **Header Auth** credential: name `Authorization`, value `Bearer <your token>`. Select it in both HTTP Request nodes.
3. List your competitors in **Settings**.
4. Connect Slack and choose a channel.

### Requirements
An Apify account (pay per result: about $0.0005 per ad plus $0.0035 per run on the free plan, so a weekly run on three competitors costs a few cents) and Slack.

### Customization
Turn on `fetchAdText` for headlines of new ads (up to about $0.004 per ad), change `reportDays`, or replace Slack with Gmail, Telegram or Google Sheets: the digest is in `{{ $json.text }}`.

Actor: https://apify.com/firsthand/google-ads-transparency-report"""


def node(name, type_, version, pos, params, **extra):
    return {"parameters": params, "name": name, "type": type_, "typeVersion": version,
            "position": pos, **extra}


def build(slack_disabled=False):
    auth = {"authentication": "genericCredentialType", "genericAuthType": "httpHeaderAuth"}
    nodes = [
        node("Overview", "n8n-nodes-base.stickyNote", 1, [-680, -360],
             {"content": NOTE, "height": 900, "width": 560, "color": 1}),
        node("Section: when and what", "n8n-nodes-base.stickyNote", 1, [-60, -140],
             {"content": "## 1. When and what to watch\nWeekly schedule or a manual run; your competitors in Settings.",
              "height": 460, "width": 420, "color": 7}),
        node("Section: read ads", "n8n-nodes-base.stickyNote", 1, [400, -140],
             {"content": "## 2. Read competitors' ads\nRun the Apify Actor, then fetch its weekly report.",
              "height": 460, "width": 460, "color": 7}),
        node("Section: digest", "n8n-nodes-base.stickyNote", 1, [880, -140],
             {"content": "## 3. Build and send the digest\nOne Slack message, one line per competitor.",
              "height": 460, "width": 460, "color": 7}),
        node("Every Monday 8:00", "n8n-nodes-base.scheduleTrigger", 1.2, [0, 0],
             {"rule": {"interval": [{"field": "weeks", "triggerAtDay": [1], "triggerAtHour": 8}]}}),
        node("Run now", "n8n-nodes-base.manualTrigger", 1, [0, 200], {}),
        node("Settings", "n8n-nodes-base.set", 3.4, [240, 100], {
            "assignments": {"assignments": [
                {"id": "a1", "name": "competitors", "value": "hubspot.com, salesforce.com, zoho.com", "type": "string"},
                {"id": "a2", "name": "country", "value": "", "type": "string"},
                {"id": "a3", "name": "reportDays", "value": 7, "type": "number"},
                {"id": "a4", "name": "maxAdsPerCompetitor", "value": 300, "type": "number"},
                {"id": "a5", "name": "fetchAdText", "value": False, "type": "boolean"},
            ]},
            "options": {}}),
        node("Run Google Ads Transparency Actor", "n8n-nodes-base.httpRequest", 4.2, [480, 100], {
            "method": "POST",
            "url": f"https://api.apify.com/v2/acts/{ACTOR}/run-sync?timeout=280",
            **auth,
            "sendBody": True,
            "specifyBody": "json",
            "jsonBody": "={{ JSON.stringify(Object.assign({"
                        " domains: $json.competitors.split(',').map(s => s.trim()).filter(Boolean),"
                        " reportDays: $json.reportDays, maxAdsPerTarget: $json.maxAdsPerCompetitor },"
                        " $json.country ? { country: $json.country } : {},"
                        " $json.fetchAdText ? { adDetails: true, ocrTextAds: true, maxDetailsPerTarget: 20 } : {})) }}",
            "options": {"timeout": 300000}}),
        node("Get report table", "n8n-nodes-base.httpRequest", 4.2, [720, 100], {
            "url": "=https://api.apify.com/v2/datasets/{{ $json.tables.report.dataset_id }}/items?clean=true",
            **auth,
            "options": {}}),
        node("Build digest", "n8n-nodes-base.code", 2, [960, 100], {"jsCode": DIGEST_JS}),
        node("Post to Slack", "n8n-nodes-base.slack", 2.3, [1200, 100], {
            "select": "channel",
            "channelId": {"__rl": True, "mode": "name", "value": "#competitor-ads"},
            "text": "={{ $json.text }}",
            "otherOptions": {}}, **({"disabled": True} if slack_disabled else {})),
    ]
    link = lambda to: {"main": [[{"node": to, "type": "main", "index": 0}]]}
    return {
        "name": "Send a weekly competitor Google Ads digest from Apify to Slack",
        "nodes": nodes,
        "connections": {
            "Every Monday 8:00": link("Settings"),
            "Run now": link("Settings"),
            "Settings": link("Run Google Ads Transparency Actor"),
            "Run Google Ads Transparency Actor": link("Get report table"),
            "Get report table": link("Build digest"),
            "Build digest": link("Post to Slack"),
        },
        "settings": {"executionOrder": "v1"},
        "pinData": {},
    }


if __name__ == "__main__":
    out, mode = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else "")
    json.dump(build(slack_disabled=(mode == "test")), open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("written", out)
