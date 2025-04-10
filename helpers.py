from flask import redirect, session
from functools import wraps
import feedparser


def login_required(f):

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function

def get_court_news(court_name):
    query = court_name.replace(" ", "+") + "+court"
    url = f"https://news.google.com/rss/search?q={query}"

    feed = feedparser.parse(url)

    news_list = []
    for entry in feed.entries:
        news_list.append({
            "title": entry.title,
            "link": entry.link,
            "source": entry.source.title if 'source' in entry else "Google News",
        })
    return news_list