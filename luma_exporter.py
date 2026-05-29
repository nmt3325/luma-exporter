#!/usr/bin/env python3
"""Luma Capture Exporter - bulk-download all your Luma captures using cookies.txt"""

import asyncio
import http.cookiejar
import sys
from pathlib import Path

import httpx

BASE_URL = "https://webapp.engineeringlumalabs.com"

FORMAT_CHOICES = {
    "1":  ("GLTF (Full)",          ["textured_mesh_glb"]),
    "2":  ("GLTF (Medium)",        ["textured_mesh_medpoly_glb"]),
    "3":  ("GLTF (Low poly)",      ["textured_mesh_lowpoly_glb"]),
    "4":  ("USDZ (Full)",          ["textured_mesh_usdz"]),
    "5":  ("USDZ (Medium)",        ["textured_mesh_medpoly_usdz"]),
    "6":  ("USDZ (Low poly)",      ["textured_mesh_lowpoly_usdz"]),
    "7":  ("OBJ (Full)",           ["textured_mesh_obj"]),
    "8":  ("OBJ (Medium)",         ["textured_mesh_medpoly_obj"]),
    "9":  ("OBJ (Low poly)",       ["textured_mesh_lowpoly_obj"]),
    "10": ("PLY Point Cloud",      ["point_cloud"]),
    "11": ("Gaussian Splat PLY",   ["gaussian_splatting_point_cloud.ply"]),
    "12": ("Luma Field (.luma)",   ["volume_model"]),
    "13": ("360° Preview Image",   ["preview_360"]),
    "14": ("Full Mesh PLY",        ["full_mesh"]),
    "15": ("All Artifacts",        None),
}


def select_format() -> tuple[str, list[str] | None]:
    print("=" * 50)
    print("  Luma Capture Exporter")
    print("=" * 50)
    print("\nSelect download format:\n")
    for key, (name, _) in FORMAT_CHOICES.items():
        print(f"  {key:2}. {name}")
    print()
    while True:
        choice = input("Enter number: ").strip()
        if choice in FORMAT_CHOICES:
            return FORMAT_CHOICES[choice]
        print("Invalid number, please try again.")


def load_cookies(cookies_path: Path) -> tuple[str, dict]:
    """Load auth token from a Netscape-format cookies.txt file."""
    jar = http.cookiejar.MozillaCookieJar()
    try:
        jar.load(str(cookies_path), ignore_discard=True, ignore_expires=True)
    except Exception as e:
        print(f"Failed to load cookies.txt: {e}")
        sys.exit(1)

    access_token = None
    refresh_token = None
    for cookie in jar:
        if cookie.domain in ("lumalabs.ai", ".lumalabs.ai"):
            if cookie.name == "accessToken":
                access_token = cookie.value
            elif cookie.name == "refreshToken":
                refresh_token = cookie.value

    token = access_token or refresh_token
    if not token:
        print("Error: accessToken / refreshToken not found in cookies.txt.")
        print("Please export cookies while logged in to lumalabs.ai.")
        sys.exit(1)

    label = "accessToken" if access_token else "refreshToken"
    print(f"Using {label}")
    return token, {}


def api_client(token: str, **kwargs) -> httpx.AsyncClient:
    """Client for Luma API calls (Bearer token only, no cookies)."""
    return httpx.AsyncClient(
        headers={
            "authorization": f"Bearer {token}",
            "referer": "https://lumalabs.ai/",
        },
        follow_redirects=True,
        **kwargs,
    )


def cdn_client(**kwargs) -> httpx.AsyncClient:
    """Client for CDN downloads (no auth — URL hash is the credential)."""
    return httpx.AsyncClient(
        headers={"referer": "https://lumalabs.ai/"},
        follow_redirects=True,
        **kwargs,
    )


async def verify_token(token: str) -> bool:
    async with api_client(token, timeout=10) as client:
        resp = await client.post(f"{BASE_URL}/api/v2/users/auth", json={})
        if resp.status_code == 200:
            data = resp.json()
            print(f"Logged in as: {data.get('username', data.get('email', 'OK'))}")
            return True
        print(f"Token verification failed (HTTP {resp.status_code}): {resp.text[:200]}")
        return False


async def fetch_all_captures(token: str) -> list[dict]:
    captures = []
    skip = 0
    take = 20

    async with api_client(token, timeout=30) as client:
        while True:
            url = f"{BASE_URL}/api/v3/captures?take={take}&skip={skip}"
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()

            batch = data["response"]
            captures.extend(batch)
            print(f"  Fetched {len(captures)} captures...")

            if not data.get("isMoreAvailable"):
                break
            skip += take

    return captures


def safe_dirname(title: str, uuid: str) -> str:
    safe = "".join(c if c.isalnum() or c in " -_" else "_" for c in title)
    return f"{safe.strip().rstrip('.')}_{uuid[:8]}"


async def download_file(client: httpx.AsyncClient, url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        print(f"    Skip (exists): {dest.name}")
        return

    tmp = dest.with_suffix(dest.suffix + ".tmp")
    try:
        async with client.stream("GET", url) as resp:
            resp.raise_for_status()
            with open(tmp, "wb") as f:
                async for chunk in resp.aiter_bytes(65536):
                    f.write(chunk)
        tmp.rename(dest)
        print(f"    Done: {dest.name}")
    except Exception as e:
        if tmp.exists():
            tmp.unlink()
        print(f"    Error: {dest.name}: {e}")


async def main():
    cookies_path = Path("cookies.txt")
    if not cookies_path.exists():
        print("Error: cookies.txt not found.")
        print()
        print("How to get it:")
        print("  1. Install the Chrome extension 'Get cookies.txt LOCALLY'")
        print("     https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc")
        print("  2. Log in to https://lumalabs.ai/dashboard/captures")
        print("  3. Click the extension icon → Export")
        print("  4. Place the downloaded cookies.txt in this folder")
        sys.exit(1)

    token, _ = load_cookies(cookies_path)

    if not await verify_token(token):
        print()
        print("Token may be expired. Log in again and re-export cookies.txt.")
        sys.exit(1)

    format_name, artifact_types = select_format()
    safe_name = format_name.replace("/", "_").replace(" ", "_").replace("(", "").replace(")", "")
    output_dir = Path("downloads") / safe_name
    print(f"\nFormat: {format_name}")
    print(f"Output: {output_dir}\n")

    print("Fetching all captures...")
    captures = await fetch_all_captures(token)

    completed = [c for c in captures if c.get("artifacts")]
    queued    = [c for c in captures if not c.get("artifacts")]
    print(f"\nTotal: {len(captures)} ({len(completed)} complete, {len(queued)} pending)")
    if queued:
        print("Skipping (not ready):", ", ".join(c.get("title", c["uuid"]) for c in queued))

    async with cdn_client(timeout=300) as client:
        for i, capture in enumerate(completed, 1):
            title = capture.get("title") or capture["uuid"]
            capture_dir = output_dir / safe_dirname(title, capture["uuid"])
            print(f"\n[{i}/{len(completed)}] {title}")

            artifacts = capture.get("artifacts", [])
            targets = artifacts if artifact_types is None else [
                a for a in artifacts if a["type"] in artifact_types
            ]

            if not targets:
                print(f"  No artifacts of type {artifact_types}")
                continue

            for artifact in targets:
                filename = artifact["url"].split("/")[-1]
                await download_file(client, artifact["url"], capture_dir / filename)

    print("\n\nAll downloads complete!")


if __name__ == "__main__":
    asyncio.run(main())
