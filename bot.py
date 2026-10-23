"""UFC news bot: polls news sites, Reddit and X, pushes new stories to your
phone via ntfy, and writes docs/news.json for the GitHub Pages site.

Environment variables (all optional):
  X_BEARER_TOKEN  X API bearer token; X is skipped without it
  NTFY_TOPIC      ntfy topic to push to; notifications are skipped without it
  NTFY_SERVER     defaults to https://ntfy.sh
  PAGE_URL        your GitHub Pages URL, used as the link on summary alerts
  DRY_RUN=1       print notifications instead of sending them
"""
from __future__ import annotations

import calendar
import hashlib
import html
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import feedparser
import requests

import config

ROOT = Path(__file__).resolve().parent
STATE_FILE = ROOT / "data" / "state.json"
NEWS_FILE = ROOT / "docs" / "news.json"
USER_AGENT = "Mozilla/5.0 (compatible; UFCNewsBot/1.0; +https://github.com)"
SEEN_TTL = 14 * 24 * 3600

UFC_RE = re.compile(config.UFC_PATTERN, re.IGNORECASE)
TAG_RE = re.compile(r"<[^>]+>")


def log(msg: str) -> None:
    print(msg, flush=True)


def clean_text(s: str, limit: int = 280) -> str:
    s = html.unescape(TAG_RE.sub(" ", s or ""))
    s = re.sub(r"\s+", " ", s).strip()
    return s if len(s) <= limit else s[: limit - 1].rstrip() + "…"


def title_key(title: str) -> str:
    # Google News appends " - Outlet"; strip it so the same headline from two
    # places only alerts once.
    t = re.sub(r"\s+-\s+[^-]{2,40}$", "", title)
    return "t:" + re.sub(r"[^a-z0-9]+", "", t.lower())[:120]


def item_id(*parts: str) -> str:
    return hashlib.sha1("|".join(parts).encode()).hexdigest()[:16]


def load_state() -> dict | None:
    if not STATE_FILE.exists():
        return None
    return json.loads(STATE_FILE.read_text())


def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------- sources

def fetch_feeds() -> list[dict]:
    items = []
    cutoff = time.time() - config.MAX_AGE_HOURS * 3600
    for feed in config.FEEDS:
        try:
            resp = requests.get(feed["url"], headers={"User-Agent": USER_AGENT}, timeout=20)
            resp.raise_for_status()
            parsed = feedparser.parse(resp.content)
        except Exception as e:
            log(f"  ! {feed['name']}: {e}")
            continue
        kept = 0
        for e in parsed.entries:
            title = clean_text(e.get("title", ""), 300)
            link = e.get("link", "")
            if not title or not link:
                continue
            summary = clean_text(e.get("summary", ""))
            if not feed.get("ufc_only") and not UFC_RE.search(f"{title} {summary}"):
                continue
            ts_struct = e.get("published_parsed") or e.get("updated_parsed")
            ts = calendar.timegm(ts_struct) if ts_struct else time.time()
            if ts < cutoff:
                continue
            items.append({
                "id": item_id(feed["name"], e.get("id") or link),
                "title": title,
                "summary": summary,
                "link": link,
                "source": feed["name"],
                "kind": "reddit" if "reddit.com" in feed["url"] else "news",
                "ts": int(min(ts, time.time())),
                "notify": feed.get("notify", True),
            })
            kept += 1
        log(f"  {feed['name']}: {kept} UFC stories")
    return items


def x_query() -> str:
    ufc = " OR ".join(f"from:{a}" for a in config.X_UFC_ACCOUNTS)
    reporters = " OR ".join(f"from:{a}" for a in config.X_REPORTER_ACCOUNTS)
    parts = []
    if ufc:
        parts.append(f"({ufc})")
    if reporters:
        parts.append(f"(({reporters}) UFC)")
    return f"({' OR '.join(parts)}) -is:retweet -is:reply"


def fetch_x(state: dict) -> list[dict]:
    token = os.environ.get("X_BEARER_TOKEN")
    if not token:
        log("  X: skipped (no X_BEARER_TOKEN)")
        return []
    params = {
        "query": x_query(),
        "max_results": 100,
        "tweet.fields": "created_at,author_id",
        "expansions": "author_id",
        "user.fields": "username,name",
    }
    if state.get("x_since_id"):
        params["since_id"] = state["x_since_id"]
    try:
        resp = requests.get(
            "https://api.x.com/2/tweets/search/recent",
            headers={"Authorization": f"Bearer {token}", "User-Agent": USER_AGENT},
            params=params,
            timeout=20,
        )
    except Exception as e:
        log(f"  ! X: {e}")
        return []
    if resp.status_code != 200:
        log(f"  ! X: HTTP {resp.status_code} {resp.text[:200]}")
        return []
    body = resp.json()
    users = {u["id"]: u for u in body.get("includes", {}).get("users", [])}
    items = []
    for t in body.get("data", []):
        user = users.get(t["author_id"], {})
        handle = user.get("username", "x")
        ts = datetime.fromisoformat(t["created_at"].replace("Z", "+00:00")).timestamp()
        text = clean_text(t["text"], 500)
        items.append({
            "id": "x" + t["id"],
            "title": text,
            "summary": "",
            "link": f"https://x.com/{handle}/status/{t['id']}",
            "source": f"@{handle}",
            "kind": "x",
            "ts": int(ts),
            "notify": True,
        })
    newest = body.get("meta", {}).get("newest_id")
    if newest:
        state["x_since_id"] = newest
    log(f"  X: {len(items)} posts")
    return items


# ---------------------------------------------------------------- notify

def notify(item: dict) -> None:
    kind_tag = {"x": "bird", "reddit": "speech_balloon"}.get(item["kind"], "newspaper")
    if item["kind"] == "x":
        title, message = f"{item['source']} on X", item["title"]
    else:
        title, message = item["source"], item["title"]
    send_ntfy({"title": title, "message": message, "click": item["link"],
               "tags": ["mma", kind_tag]})


def send_ntfy(payload: dict) -> None:
    topic = os.environ.get("NTFY_TOPIC")
    if os.environ.get("DRY_RUN"):
        log(f"  [dry-run notify] {payload['title']}: {payload['message'][:90]}")
        return
    if not topic:
        return
    server = os.environ.get("NTFY_SERVER", "https://ntfy.sh").rstrip("/")
    try:
        r = requests.post(server, json={"topic": topic, **payload}, timeout=15)
        r.raise_for_status()
    except Exception as e:
        log(f"  ! ntfy: {e}")


# ---------------------------------------------------------------- main

def main() -> int:
    state = load_state()
    first_run = state is None
    state = state or {"seen": {}}
    now = int(time.time())

    log("Fetching sources…")
    items = fetch_feeds() + fetch_x(state)
    items.sort(key=lambda i: i["ts"])  # oldest first so alerts arrive in order

    seen = state["seen"]
    new_items = []
    for it in items:
        tkey = title_key(it["title"])
        if it["id"] in seen or (it["kind"] != "x" and tkey in seen):
            continue
        seen[it["id"]] = now
        if it["kind"] != "x":
            seen[tkey] = now
        new_items.append(it)

    # Prune old seen entries so the state file doesn't grow forever.
    state["seen"] = {k: v for k, v in seen.items() if now - v < SEEN_TTL}
    log(f"{len(new_items)} new stories")

    if first_run:
        log("First run: recording current stories without sending alerts.")
    else:
        to_push = [i for i in new_items if i["notify"]]
        cap = config.MAX_NOTIFICATIONS_PER_RUN
        for it in to_push[-cap:]:
            notify(it)
        if len(to_push) > cap:
            extra = len(to_push) - cap
            send_ntfy({
                "title": "UFC News",
                "message": f"+{extra} more new UFC stories",
                "click": os.environ.get("PAGE_URL", ""),
                "tags": ["mma"],
            })

    # Merge into the web page feed.
    existing = json.loads(NEWS_FILE.read_text()) if NEWS_FILE.exists() else {"items": []}
    by_id = {i["id"]: i for i in existing["items"]}
    for it in new_items:
        by_id[it["id"]] = {k: v for k, v in it.items() if k != "notify"}
    merged = sorted(by_id.values(), key=lambda i: i["ts"], reverse=True)[: config.MAX_PAGE_ITEMS]
    save_json(NEWS_FILE, {"updated": now, "items": merged})
    save_json(STATE_FILE, state)
    return 0


if __name__ == "__main__":
    sys.exit(main())
