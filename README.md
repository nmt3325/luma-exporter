# Luma Capture Exporter

A script to bulk-download all captures from your [Luma AI](https://lumalabs.ai) account.

## Features

- Fetches all captures in "Your Captures" automatically (handles pagination / "show more")
- Multiple download formats supported
- Skips existing files — safe to interrupt and resume
- Automatically skips captures that are still processing

## Supported Formats

| # | Format | Description |
|---|--------|-------------|
| 1–3  | GLTF | Full / Medium / Low poly (.glb) |
| 4–6  | USDZ | Full / Medium / Low poly (.usdz) |
| 7–9  | OBJ  | Full / Medium / Low poly (.zip) |
| 10 | PLY Point Cloud | point_cloud.ply |
| 11 | Gaussian Splat PLY | gaussian_splatting_point_cloud.ply.zip |
| 12 | Luma Field | volume_model.luma |
| 13 | 360° Preview Image | preview_360.jpg |
| 14 | Full Mesh PLY | full_mesh.ply |
| 15 | All Artifacts | Everything above |

## Setup

```bash
git clone <this-repo>
cd luma-exporter
python3 -m venv .venv
.venv/bin/pip install httpx
```

## Usage

### 1. Get cookies.txt

1. Install the Chrome extension **[Get cookies.txt LOCALLY](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)**
2. Log in to https://lumalabs.ai/dashboard/captures in your browser
3. Click the extension icon → **Export**
4. Place the downloaded `cookies.txt` in this folder

> The `accessToken` expires in **1 hour**. If you see an auth error, log in again and re-export.

### 2. Run

```bash
.venv/bin/python3 luma_exporter.py
```

A format selection menu appears on startup. Enter a number to begin downloading all your captures.

### Output structure

```
downloads/
└── GLTF_Full/
    ├── 営団8000系_3a797d97/
    │   └── 8000_textured_mesh_glb.glb
    ├── 横川駅_51905d6f/
    │   └── ...
    └── ...
```

## Notes

- Only **Your Captures** are downloaded — Featured Captures and other users' content are ignored
- `cookies.txt` contains auth credentials; do not share it
- `cookies.txt` is listed in `.gitignore` to prevent accidental commits
