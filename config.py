"""Edit this file to change what the bot watches."""

# RSS/Atom feeds. Set "ufc_only": True for feeds that are all UFC already
# (no keyword filter). Set "notify": False to show a source on the web page
# without pushing it to your phone (useful for high-volume sources).
FEEDS = [
    # UFC / MMA outlets
    {"name": "UFC.com", "url": "https://www.ufc.com/rss/news", "ufc_only": True},
    {"name": "MMA Fighting", "url": "https://www.mmafighting.com/rss/current.xml"},
    {"name": "MMA Mania", "url": "https://www.mmamania.com/rss/current.xml"},
    {"name": "Sherdog", "url": "https://www.sherdog.com/rss/news.xml"},
    {"name": "MMA News", "url": "https://www.mmanews.com/feed/"},
    {"name": "BJPenn.com", "url": "https://www.bjpenn.com/feed/"},
    # General sports sites
    {"name": "ESPN", "url": "https://www.espn.com/espn/rss/mma/news"},
    {"name": "CBS Sports", "url": "https://www.cbssports.com/rss/headlines/mma/"},
    {"name": "Yahoo Sports", "url": "https://sports.yahoo.com/mma/rss.xml"},
    {"name": "BBC Sport", "url": "https://feeds.bbci.co.uk/sport/mixed-martial-arts/rss.xml"},
    # Aggregators / social (page only by default - too noisy for push)
    {
        "name": "Google News",
        "url": "https://news.google.com/rss/search?q=UFC+when:1d&hl=en-US&gl=US&ceid=US:en",
        "notify": False,
    },
    {"name": "Reddit r/MMA", "url": "https://www.reddit.com/r/MMA/hot/.rss", "notify": False},
]

# X accounts whose every original post counts as UFC news.
X_UFC_ACCOUNTS = ["ufc", "UFCNews", "danawhite"]

# X accounts that post about lots of things; only posts mentioning UFC are kept.
X_REPORTER_ACCOUNTS = [
    "arielhelwani",
    "MMAFighting",
    "ESPNMMA",
    "marc_raimondi",
    "BrettOkamoto",
    "AaronBronsteter",
    "MMAjunkie",
]

# A story matches if its title or summary matches this (case-insensitive).
UFC_PATTERN = r"\bufc\d*\b|dana white|octagon"

# Ignore stories older than this many hours.
MAX_AGE_HOURS = 72

# Max phone notifications per run; extra stories get one summary alert.
MAX_NOTIFICATIONS_PER_RUN = 8

# How many stories to keep on the web page.
MAX_PAGE_ITEMS = 400
