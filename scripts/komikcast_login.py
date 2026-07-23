"""Komikcast login via Camoufox v2 — longer wait for SPA render."""
import asyncio
import json
import sys
sys.path.insert(0, '/home/ubuntu/projects/nakama')


async def komikcast_login():
    from camoufox import AsyncCamoufox

    token = None
    login_url = "https://v3.komikcast.fit/login"

    async with AsyncCamoufox(headless=True, humanize=True, geoip=True, locale="en-US") as browser:
        page = await browser.new_page()

        captured_responses = []

        async def handle_response(response):
            url = response.url
            if any(x in url.lower() for x in ["appwrite", "auth", "session", "account", "be.komikcast", "token", "login", "v1/account"]):
                try:
                    body = await response.text()
                    captured_responses.append({
                        "url": url,
                        "status": response.status,
                        "body": body[:3000],
                    })
                except:
                    pass

        page.on("response", handle_response)

        print(f"1. Navigating to {login_url}...")
        await page.goto(login_url, timeout=45000, wait_until="networkidle")
        
        # Wait for SPA to hydrate
        print("2. Waiting for SPA hydration (8s)...")
        await asyncio.sleep(8)

        print(f"3. Page title: {await page.title()}")
        print(f"   URL: {page.url}")
        
        # Check page HTML for clues
        content = await page.content()
        print(f"   HTML size: {len(content)} bytes")

        # Try to find any input
        inputs = await page.query_selector_all("input")
        print(f"4. Found {len(inputs)} input elements")
        for i, inp in enumerate(inputs):
            inp_type = await inp.get_attribute("type") or "text"
            inp_name = await inp.get_attribute("name") or ""
            inp_ph = await inp.get_attribute("placeholder") or ""
            inp_id = await inp.get_attribute("id") or ""
            inp_class = await inp.get_attribute("class") or ""
            print(f"  Input {i}: type={inp_type} name={inp_name} id={inp_id} placeholder={inp_ph} class={inp_class[:60]}")

        # Try broader selectors
        print("\n5. Trying broader selectors...")
        for sel in ['input', 'form', '[role="textbox"]', '[contenteditable]', 'button', 'a[href*="login"]', 'a[href*="auth"]']:
            els = await page.query_selector_all(sel)
            if els:
                print(f"  {sel}: {len(els)} elements")
                for j, el in enumerate(els[:3]):
                    text = await el.text_content() or ""
                    href = await el.get_attribute("href") or ""
                    tag = await el.evaluate("el => el.tagName")
                    print(f"    [{j}] tag={tag} text={text[:50]} href={href}")

        # Screenshot
        await page.screenshot(path="/tmp/komikcast_login_v2.png", full_page=True)
        print("\n6. Screenshot saved to /tmp/komikcast_login_v2.png")

        # Try navigating to /login differently
        print("\n7. Trying to find login link or form...")
        # Maybe the page uses a modal or different route
        links = await page.query_selector_all("a")
        login_links = []
        for link in links:
            href = await link.get_attribute("href") or ""
            text = await link.text_content() or ""
            if any(x in href.lower() or x in text.lower() for x in ["login", "masuk", "sign in", "daftar", "register"]):
                login_links.append((href, text.strip()))
        print(f"  Login-related links: {login_links[:5]}")

        # Try clicking login link if found
        if login_links:
            for href, text in login_links:
                if "login" in href.lower() or "masuk" in text.lower():
                    print(f"  Clicking: {href} ({text})")
                    await page.goto(f"https://v3.komikcast.fit{href}" if href.startswith("/") else href, timeout=20000)
                    await asyncio.sleep(5)
                    break

        # Re-check for inputs after navigation
        inputs = await page.query_selector_all("input")
        print(f"\n8. After navigation: {len(inputs)} inputs")
        if inputs:
            for i, inp in enumerate(inputs):
                inp_type = await inp.get_attribute("type") or "text"
                inp_name = await inp.get_attribute("name") or ""
                inp_ph = await inp.get_attribute("placeholder") or ""
                print(f"  Input {i}: type={inp_type} name={inp_name} placeholder={inp_ph}")

        # If still no inputs, try the API directly
        if not inputs:
            print("\n9. No form found. Trying Appwrite API directly...")
            # Komikcast uses Appwrite — try direct API call
            import httpx
            
            # Appwrite endpoints commonly used
            api_endpoints = [
                ("https://fra.cloud.appwrite.io/v1/account/sessions/email", "POST"),
                ("https://appwrite.komikcast.cc/v1/account/sessions/email", "POST"),
                ("https://be.komikcast.cc/v1/account/sessions/email", "POST"),
                ("https://be.komikcast.cc/auth/login", "POST"),
            ]
            
            headers = {
                "Content-Type": "application/json",
                "Origin": "https://v3.komikcast.fit",
                "Referer": "https://v3.komikcast.fit/",
            }
            
            async with httpx.AsyncClient(timeout=15) as client:
                for url, method in api_endpoints:
                    try:
                        print(f"  Trying {method} {url}...")
                        if method == "POST":
                            resp = await client.post(
                                url,
                                json={"email": "shenyo1", "password": "vanilla"},
                                headers=headers,
                            )
                        print(f"    Status: {resp.status_code}")
                        body = resp.text[:500]
                        print(f"    Body: {body}")
                        
                        if resp.status_code == 201 or resp.status_code == 200:
                            data = resp.json()
                            # Look for token/secret/jwt
                            for key in ["secret", "jwt", "token", "providerToken"]:
                                if key in data:
                                    token = data[key]
                                    print(f"    TOKEN FOUND: {key}={token[:60]}...")
                                    break
                            if token:
                                break
                    except Exception as e:
                        print(f"    Error: {e}")
            
            # Also try with email format
            if not token:
                print("\n  Trying with email format...")
                async with httpx.AsyncClient(timeout=15) as client:
                    for url, method in api_endpoints:
                        try:
                            resp = await client.post(
                                url,
                                json={"email": "shenyo1@gmail.com", "password": "vanilla"},
                                headers={**headers, "X-Appwrite-Project": "komikcast"},
                            )
                            print(f"    {url} -> {resp.status_code}: {resp.text[:300]}")
                            if resp.status_code in (200, 201):
                                data = resp.json()
                                for key in ["secret", "jwt", "token"]:
                                    if key in data:
                                        token = data[key]
                                        print(f"    TOKEN: {token[:60]}...")
                                        break
                                if token:
                                    break
                        except Exception as e:
                            print(f"    Error: {e}")

        # Check localStorage regardless
        print("\n10. localStorage check...")
        local_storage = await page.evaluate("""() => {
            const items = {};
            for (let i = 0; i < localStorage.length; i++) {
                const key = localStorage.key(i);
                items[key] = localStorage.getItem(key);
            }
            return items;
        }""")
        for key, value in local_storage.items():
            print(f"  {key}: {str(value)[:200]}")
            if any(x in key.lower() for x in ["token", "jwt", "secret", "session", "auth"]):
                try:
                    parsed = json.loads(value)
                    if isinstance(parsed, dict):
                        for tk in ["secret", "jwt", "token"]:
                            if tk in parsed:
                                token = parsed[tk]
                                print(f"  >>> TOKEN: {token[:60]}...")
                except:
                    if len(value) > 30 and value.count(".") >= 2:
                        token = value

        # Check captured responses
        print(f"\n11. Captured {len(captured_responses)} responses:")
        for i, resp in enumerate(captured_responses):
            print(f"\n  [{i}] {resp['url'][:120]}")
            print(f"  Status: {resp['status']}")
            print(f"  Body: {resp['body'][:400]}")

        if token:
            print(f"\n=== SUCCESS ===")
            print(f"Token: {token[:80]}...")
        else:
            print(f"\n=== No token found ===")

        return token


if __name__ == "__main__":
    result = asyncio.run(komikcast_login())
    if result:
        with open("/tmp/komikcast_token.txt", "w") as f:
            f.write(result)
        print(f"\nToken saved to /tmp/komikcast_token.txt")
    else:
        print("\nFailed to obtain token")
