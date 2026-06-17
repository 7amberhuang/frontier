#!/usr/bin/env python3
"""One-time X login for twikit. YOU run this and type your own password
(hidden). Saves a cookie file so the daily fetch never needs the password again.
Run:  uv run --with twikit python3 twikit_login.py
"""
import asyncio, getpass
from twikit import Client

async def main():
    user = input("X username (no @, e.g. jiaqihuangai): ").strip().lstrip("@")
    email = input("X email: ").strip()
    pw = getpass.getpass("X password (hidden, not stored): ")
    c = Client("en-US")
    await c.login(auth_info_1=user, auth_info_2=email, password=pw)
    c.save_cookies(".twikit_cookies.json")
    print("✓ logged in — cookies saved to .twikit_cookies.json (git-ignored).")
    print("  从现在起跑 twikit_fetch.py 就不用再输密码了。")

asyncio.run(main())
