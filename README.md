# UFC News Wire

A bot that checks UFC/MMA sites, general sports sites, Google News, Reddit and X
every ~10 minutes, pushes new stories to your phone, and publishes them to a web page.

- **Runs on:** GitHub Actions (free), `.github/workflows/bot.yml`
- **Phone alerts:** [ntfy](https://ntfy.sh) (free iOS/Android app, no account)
- **Web page:** GitHub Pages, served from `docs/`
- **What it watches:** edit `config.py`

## Setup (about 10 minutes)

### 1. Put it on GitHub
Create a **public** repo (GitHub Pages is free for public repos), then from this folder:

```bash
git init && git add . && git commit -m "UFC news bot" && git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/ufc-news.git
git push -u origin main
```

### 2. Phone notifications
1. Install **ntfy** from the App Store / Play Store.
2. Tap **+**, subscribe to a hard-to-guess topic name, e.g. `ufc-news-k39xq72m`.
   Anyone who knows the topic name can read it, so keep it random.
3. In GitHub: **Settings → Secrets and variables → Actions → New repository secret**
   - Name `NTFY_TOPIC`, value: your topic name.

### 3. X (Twitter)
1. Sign up at [developer.x.com](https://developer.x.com), create a project/app, and
   buy access that includes **recent search** (`GET /2/tweets/search/recent`).
2. Copy the app's **Bearer Token** and add it as a repo secret named `X_BEARER_TOKEN`.

X bills by usage. The bot only asks for posts newer than the last one it saw,
so you pay for new posts, not repeats. Watch your usage in the X developer
console, and trim the account lists in `config.py` if it gets pricey.

### 4. Web page
**Settings → Pages →** Source: *Deploy from a branch*, Branch: `main`, folder `/docs`.
Your page will be at `https://YOUR_USERNAME.github.io/ufc-news/`.
Tip: open it on your phone and use *Add to Home Screen*.

### 5. Start it
**Actions → UFC news bot → Run workflow.** The first run records current stories
without alerting you (so you don't get 200 notifications). After that it runs
every ~10 minutes on its own and alerts on anything new.

## Tweaking
All in `config.py`:
- Add/remove feeds. `"notify": False` keeps a source on the page but off your phone
  (Google News and Reddit are set this way because they're high-volume).
- `X_UFC_ACCOUNTS` posts always count; `X_REPORTER_ACCOUNTS` posts only count if they mention UFC.
- `MAX_NOTIFICATIONS_PER_RUN` caps alerts per run; extras become one "+N more" alert.

## Running locally
```bash
pip install -r requirements.txt
DRY_RUN=1 python bot.py
```
`DRY_RUN=1` prints alerts instead of sending them. Note that a local run writes
`data/state.json`; delete it (and `docs/news.json`) before pushing if you want the
cloud's first run to start fresh.

## Notes
- GitHub's scheduled runs can be delayed a few minutes at busy times.
- The bot commits `data/state.json` and `docs/news.json` each time it finds news;
  that's how it remembers what it's seen and updates the page.
- MMA Junkie and Bloody Elbow block bots, so they're reached via Google News instead.
