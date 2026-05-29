#!/usr/bin/env python3
"""Luma Capture Exporter - cookies.txtを使って全キャプチャをダウンロードする"""

import asyncio
import http.cookiejar
import sys
from pathlib import Path

import httpx

BASE_URL = "https://webapp.engineeringlumalabs.com"

FORMAT_CHOICES = {
    "1":  ("GLTF (フル品質)",      ["textured_mesh_glb"]),
    "2":  ("GLTF (中品質)",        ["textured_mesh_medpoly_glb"]),
    "3":  ("GLTF (低品質)",        ["textured_mesh_lowpoly_glb"]),
    "4":  ("USDZ (フル品質)",      ["textured_mesh_usdz"]),
    "5":  ("USDZ (中品質)",        ["textured_mesh_medpoly_usdz"]),
    "6":  ("USDZ (低品質)",        ["textured_mesh_lowpoly_usdz"]),
    "7":  ("OBJ (フル品質)",       ["textured_mesh_obj"]),
    "8":  ("OBJ (中品質)",         ["textured_mesh_medpoly_obj"]),
    "9":  ("OBJ (低品質)",         ["textured_mesh_lowpoly_obj"]),
    "10": ("PLY ポイントクラウド", ["point_cloud"]),
    "11": ("Gaussian Splat PLY",  ["gaussian_splatting_point_cloud.ply"]),
    "12": ("Luma Field (.luma)",   ["volume_model"]),
    "13": ("360° プレビュー画像",  ["preview_360"]),
    "14": ("フルメッシュ PLY",     ["full_mesh"]),
    "15": ("全アーティファクト",   None),
}


def select_format() -> tuple[str, list[str] | None]:
    print("=" * 50)
    print("  Luma Capture Exporter")
    print("=" * 50)
    print("\nダウンロード形式を選択してください:\n")
    for key, (name, _) in FORMAT_CHOICES.items():
        print(f"  {key:2}. {name}")
    print()
    while True:
        choice = input("番号を入力: ").strip()
        if choice in FORMAT_CHOICES:
            return FORMAT_CHOICES[choice]
        print("無効な番号です。もう一度入力してください。")


def load_cookies(cookies_path: Path) -> tuple[str, dict]:
    """Netscape形式のcookies.txtから認証トークンを取得する"""
    jar = http.cookiejar.MozillaCookieJar()
    try:
        jar.load(str(cookies_path), ignore_discard=True, ignore_expires=True)
    except Exception as e:
        print(f"cookies.txtの読み込みに失敗: {e}")
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
        print("エラー: cookies.txt に accessToken / refreshToken が見つかりません。")
        print("lumalabs.ai にログインした状態でcookies.txtをエクスポートしてください。")
        sys.exit(1)

    label = "accessToken" if access_token else "refreshToken"
    print(f"{label} を使用します")
    return token, {}


def api_client(token: str, **kwargs) -> httpx.AsyncClient:
    """Luma API用クライアント (Bearer tokenのみ、cookieなし)"""
    return httpx.AsyncClient(
        headers={
            "authorization": f"Bearer {token}",
            "referer": "https://lumalabs.ai/",
        },
        follow_redirects=True,
        **kwargs,
    )


def cdn_client(**kwargs) -> httpx.AsyncClient:
    """CDNダウンロード用クライアント (認証不要、URLのハッシュが認証)"""
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
            print(f"ログイン確認: {data.get('username', data.get('email', 'OK'))}")
            return True
        print(f"トークンの検証に失敗 (HTTP {resp.status_code}): {resp.text[:200]}")
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
            print(f"  取得済み: {len(captures)} 件")

            if not data.get("isMoreAvailable"):
                break
            skip += take

    return captures


def safe_dirname(title: str, uuid: str) -> str:
    safe = "".join(c if c.isalnum() or c in " -_（）()。、" else "_" for c in title)
    return f"{safe.strip().rstrip('.')}_{uuid[:8]}"


async def download_file(client: httpx.AsyncClient, url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        print(f"    スキップ (既存): {dest.name}")
        return

    tmp = dest.with_suffix(dest.suffix + ".tmp")
    try:
        async with client.stream("GET", url) as resp:
            resp.raise_for_status()
            with open(tmp, "wb") as f:
                async for chunk in resp.aiter_bytes(65536):
                    f.write(chunk)
        tmp.rename(dest)
        print(f"    完了: {dest.name}")
    except Exception as e:
        if tmp.exists():
            tmp.unlink()
        print(f"    エラー: {dest.name}: {e}")


async def main():
    cookies_path = Path("cookies.txt")
    if not cookies_path.exists():
        print("エラー: cookies.txt が見つかりません。")
        print()
        print("取得方法:")
        print("  1. Chrome拡張「Get cookies.txt LOCALLY」をインストール")
        print("     https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc")
        print("  2. https://lumalabs.ai/dashboard/captures にログインした状態で")
        print("     拡張アイコンをクリック → Export (lumalabs.ai のみで可)")
        print("  3. ダウンロードした cookies.txt をこのスクリプトと同じフォルダに置く")
        sys.exit(1)

    token, _ = load_cookies(cookies_path)

    if not await verify_token(token):
        print()
        print("アクセストークンが期限切れの可能性があります。")
        print("再度ブラウザでログインし、cookies.txt をエクスポートし直してください。")
        sys.exit(1)

    format_name, artifact_types = select_format()
    safe_name = format_name.replace("/", "_").replace(" ", "_").replace("(", "").replace(")", "")
    output_dir = Path("downloads") / safe_name
    print(f"\n選択: {format_name}")
    print(f"保存先: {output_dir}\n")

    print("全キャプチャを取得中...")
    captures = await fetch_all_captures(token)

    completed = [c for c in captures if c.get("artifacts")]
    queued    = [c for c in captures if not c.get("artifacts")]
    print(f"\n合計: {len(captures)} 件 (完了: {len(completed)}, 未完了: {len(queued)})")
    if queued:
        print("スキップ (未完了):", ", ".join(c.get("title", c["uuid"]) for c in queued))

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
                print(f"  対象アーティファクトなし (types: {artifact_types})")
                continue

            for artifact in targets:
                filename = artifact["url"].split("/")[-1]
                await download_file(client, artifact["url"], capture_dir / filename)

    print("\n\n全ダウンロード完了!")


if __name__ == "__main__":
    asyncio.run(main())
