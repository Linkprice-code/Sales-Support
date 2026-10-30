#!/usr/bin/env python3
"""Linkprice Market Radar — public RSS headlines only. No paid API, no page scraping.

Feeds are accessed at a conservative pace; headlines/dates/sources/links are stored.
We neither crawl articles nor reproduce article bodies. This is not a market-size dataset.
"""
from __future__ import annotations

import argparse
import datetime as dt
import email.utils
import json
import os
import pathlib
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from zoneinfo import ZoneInfo

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
KST = ZoneInfo("Asia/Seoul")
NOW = dt.datetime.now(dt.timezone.utc)
TODAY = NOW.astimezone(KST).date()
MAX_AGE_DAYS = int(os.getenv("NEWS_MAX_AGE_DAYS", "35"))
MAX_CATS_PER_RUN = min(150, max(1, int(os.getenv("MAX_CATS_PER_RUN", "38"))))
MAX_ITEMS = 8
TIMEOUT = 11
USER_AGENT = "LinkpriceMarketRadar/1.0 (RSS public headlines; respect publisher links)"

# Publisher-provided RSS feeds. Publisher terms remain applicable; store metadata only.
PUBLISHER_FEEDS = [
    ("뉴시스 경제", "https://nwww.newsis.com/RSS/economy.xml"),
    ("뉴시스 산업", "https://nwww.newsis.com/RSS/industry.xml"),
    ("매일경제 경제", "https://www.mk.co.kr/rss/30100041/"),
    ("매일경제 기업", "https://www.mk.co.kr/rss/50100032/"),
    ("인더스트리뉴스", "https://www.industrynews.co.kr/rss/allArticle.xml"),
    ("KOSIS 주요 월간동향", "https://kosis.kr/rss/trend_rss.jsp"),
]


def safe_https(url: str) -> str:
    try:
        parsed = urllib.parse.urlsplit(url.strip())
        return url if parsed.scheme == "https" and parsed.netloc else ""
    except Exception:
        return ""


def fetch_xml(url: str) -> bytes:
    if not safe_https(url):
        raise ValueError("Expected HTTPS RSS URL")
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml;q=0.9",
    })
    with urllib.request.urlopen(req, timeout=TIMEOUT) as res:
        data = res.read(1_500_001)
        if len(data) > 1_500_000:
            raise ValueError("Feed exceeds max download size")
        return data


def justtext(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s or "")).strip()


def dt_iso(s: str) -> str:
    if not s:
        return ""
    try:
        t = email.utils.parsedate_to_datetime(s)
    except Exception:
        try: t = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
        except Exception: return ""
    if t.tzinfo is None:
        t = t.replace(tzinfo=dt.timezone.utc)
    return t.astimezone(KST).isoformat(timespec="seconds")


def new_enough(date_str: str) -> bool:
    if not date_str:
        return True  # Some publisher RSS omit dates; the listing itself is current.
    try:
        age = (NOW - dt.datetime.fromisoformat(date_str).astimezone(dt.timezone.utc)).total_seconds() / 86400
        return -1 <= age <= MAX_AGE_DAYS
    except Exception:
        return True


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def child_text(el: ET.Element, names: tuple[str,...]) -> str:
    for item in el:
        if local_name(item.tag) in names:
            return "".join(item.itertext()).strip()
    return ""


def parse_feed(data: bytes, default_source: str) -> list[dict]:
    root = ET.fromstring(data)
    entries = [el for el in root.iter() if local_name(el.tag) in ("item", "entry")]
    out = []
    for el in entries[:110]:
        title = justtext(child_text(el, ("title",)))
        link = child_text(el, ("link",))
        if not link:
            for k in el:
                if local_name(k.tag) == "link" and k.get("href"):
                    link = k.get("href")
                    break
        url = safe_https(link)
        if not title or not url:
            continue
        pub = dt_iso(child_text(el, ("pubdate", "published", "updated", "date")))
        if not new_enough(pub):
            continue
        source = child_text(el, ("source",)) or default_source
        source = justtext(source)[:70]
        # Google News usually adds ` - Publisher` at the end of title. Keep it as supplied.
        out.append({"title": title[:175], "url": url, "source": source,
                    "published": pub or ""})
    return out


def category_query(cat: dict, parent_name: str) -> str:
    name = cat["name"].strip()
    # Include root for ambiguous short category labels.
    phrase = f'"{name}"' if len(name) > 2 else f'"{parent_name}" "{name}"'
    return f'{phrase} (시장 OR 소비 OR 판매 OR 출시 OR 유통) when:30d'


def google_rss_url(query: str) -> str:
    return "https://news.google.com/rss/search?" + urllib.parse.urlencode({
        "q": query, "hl": "ko", "gl": "KR", "ceid": "KR:ko"
    })


def match_category(title: str, cat: dict, parent_name: str) -> bool:
    n = cat["name"].replace(" ", "").lower()
    t = title.replace(" ", "").lower()
    if len(n) >= 2:
        return n in t
    return n in t and parent_name.replace(" ", "").lower() in t


def unique_articles(articles: list[dict]) -> list[dict]:
    seen = set(); out = []
    for a in sorted(articles, key=lambda x: x.get("published", ""), reverse=True):
        if not safe_https(a.get("url", "")):
            continue
        key = re.sub(r"[^가-힣a-z0-9]", "", a["title"].lower())[:90]
        if len(key) < 8 or key in seen:
            continue
        seen.add(key)
        out.append(a)
        if len(out) >= MAX_ITEMS:
            break
    return out


def select_categories(cats: list[dict], focus_names: set[str], max_count: int, run_day: dt.date) -> list[dict]:
    roots = [c for c in cats if c["level"] == 1]
    mids = [c for c in cats if c["level"] == 2]
    focus = [c for c in mids if c["name"] in focus_names or str(c["id"]) in focus_names]
    # Sliding window: gradual coverage of the entire preview catalog (~6 days at 38 mids/day).
    start = ((run_day - dt.date(2026, 1, 1)).days * max_count) % max(1, len(mids))
    rotation = [mids[(start + i) % len(mids)] for i in range(min(max_count, len(mids)))]
    selected=[]; used=set()
    for c in [*roots, *focus[:16], *rotation]:
        if c["id"] not in used:
            selected.append(c);used.add(c["id"])
    return selected


def refresh(save: bool = True, feed_fetcher=fetch_xml, run_day: dt.date | None = None) -> dict:
    run_day = run_day or TODAY
    catalog = json.loads((DATA / "categories.json").read_text(encoding="utf-8"))
    categories = catalog["categories"]
    roots={str(c["id"]):c["name"] for c in categories if c["level"] == 1}
    focus_file=DATA / "focus_categories.txt"
    focus_names = {l.strip() for l in focus_file.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")} if focus_file.exists() else set()
    selected=select_categories(categories,focus_names,MAX_CATS_PER_RUN,run_day)
    news_file = DATA / "news.json"
    old=json.loads(news_file.read_text(encoding="utf-8")) if news_file.exists() else {"items":{}}
    prev_items=old.get("items", {})
    items=dict(prev_items)
    errors=[]; source_articles=[]; source_success=0
    for provider,url in PUBLISHER_FEEDS:
        try:
            feed_articles=parse_feed(feed_fetcher(url),provider)
            source_articles.extend(feed_articles)
            source_success+=1
            print(f"Publisher RSS {provider}: {len(feed_articles)} articles",flush=True)
        except Exception as exc:
            errors.append(f"{provider}: {type(exc).__name__} - {str(exc)[:100]}")
            print('WARN',errors[-1],file=sys.stderr)
        time.sleep(0.3)
    google_fail=0; google_success=0; successful_checks=0; new_article_count=0
    for idx,cat in enumerate(selected):
        name=cat["name"]
        parent=roots.get(str(cat.get("parent_id")),name)
        direct=[]; google_ok=False
        if google_fail < 5:
            url=google_rss_url(category_query(cat,parent))
            try:
                direct=parse_feed(feed_fetcher(url),"Google 뉴스 RSS")
                google_ok=True
                google_success+=1
                google_fail=0
            except Exception as exc:
                google_fail+=1
                if len(errors)<25:errors.append(f"{name} 구글 뉴스: {type(exc).__name__}: {str(exc)[:90]}")
        # News metadata must be category-specific. Use parent labels only for fallback display in browser.
        matched=[a for a in source_articles if match_category(a["title"],cat,parent)]
        # Google News query may include vaguely related articles; filter title relevancy.
        relevant=[a for a in direct if match_category(a["title"],cat,parent)]
        found=unique_articles(relevant+matched)
        if google_ok or source_success:
            entry={"name":name,"parent":parent,"checked_at":NOW.astimezone(KST).isoformat(timespec="seconds"),"articles":found,
                   "coverage":"google_news_rss+publisher_rss" if google_ok and source_success else "google_news_rss" if google_ok else "publisher_rss_only"}
            # On temporary no-result, keep recent previously fetched non-stale titles instead of blanking.
            if not found and cat['id'] in items:
                previous=[a for a in items[str(cat['id'])].get('articles',[]) if new_enough(a.get('published',''))]
                if previous:entry['articles']=previous;entry['coverage']+=';retained_previous'
            items[str(cat["id"])]=entry
            successful_checks+=1;new_article_count+=len(found)
        if (idx+1)%10==0:
            print(f"Category checked {idx+1}/{len(selected)}",flush=True)
        if idx<len(selected)-1 and google_fail<5:
            time.sleep(1.15)
    if successful_checks == 0:
        print('ERROR: All feeds failed. Existing news.json preserved.',file=sys.stderr)
        return {"success":False,"errors":errors,"processed":0}
    # Drop entries for categories removed from catalog to prevent unbounded growth.
    valid_ids={str(c['id']) for c in categories}
    items={k:v for k,v in items.items() if k in valid_ids}
    metadata={"source":"public_rss","updated":NOW.astimezone(KST).isoformat(timespec="seconds"),
              "description":"RSS 기사 제목·발행일·출처·링크. 네이버/오픈AI/유료 API 미사용. 기사 건수는 실제 시장규모 아님.",
              "status":"partial_success" if errors else "ok","processed_categories":successful_checks,
              "google_news_checks":google_success,"publisher_feeds_ok":source_success,"errors":errors[:20],
              "news_count_newly_matched":new_article_count,"catalog_scope":"starter_preview; not verified full NAVER catalog"}
    result={"metadata":metadata,"items":items}
    if save:
        temp=news_file.with_suffix('.tmp')
        temp.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        temp.replace(news_file)
    print(f"SAVED: {len(items)} categories, {successful_checks} checked, {google_success} Google RSS ok, {source_success} publisher RSS ok.",flush=True)
    return {"success":True,"errors":errors,"processed":successful_checks,"result":result}


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument('--dry-run',action='store_true',help='read feeds but do not write JSON')
    args=parser.parse_args()
    outcome=refresh(save=not args.dry_run)
    sys.exit(0 if outcome['success'] else 1)
