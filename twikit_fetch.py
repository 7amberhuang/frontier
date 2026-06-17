#!/usr/bin/env python3
"""Fetch each AI product account's top recent tweet (by engagement) via twikit.
Uses saved cookies (run twikit_login.py first). Writes product_feed.json.
Run:  uv run --with twikit python3 twikit_fetch.py
"""
import asyncio, json, pathlib
from twikit import Client

# ⚠️ 确认这些 handle 对不对（去 X 上核一下，写错会抓不到）
ACCOUNTS = ["AnthropicAI", "OpenAI", "HeyGen_Official", "AhaCreator_AI", "heyditto"]
OUT = pathlib.Path(__file__).resolve().parent / "product_feed.json"

async def main():
    c = Client("en-US")
    c.load_cookies(".twikit_cookies.json")
    items = []
    for h in ACCOUNTS:
        try:
            u = await c.get_user_by_screen_name(h)
            tweets = await u.get_tweets("Tweets", count=8)
            cand = [t for t in tweets if not t.text.startswith("RT @")]
            if not cand:
                continue
            best = max(cand, key=lambda t: (t.favorite_count or 0) + (t.retweet_count or 0))
            items.append({
                "name": u.name, "handle": h, "text": best.text[:200],
                "likes": best.favorite_count or 0, "rts": best.retweet_count or 0,
                "url": f"https://x.com/{h}/status/{best.id}",
            })
            print(f"  ✓ {h}: {best.favorite_count} likes")
        except Exception as ex:
            print(f"  ✗ {h}: {ex}")
    json.dump({"product": items}, open(OUT, "w"), ensure_ascii=False, indent=2)
    print(f"✓ wrote {OUT} — {len(items)} product accounts")

asyncio.run(main())
