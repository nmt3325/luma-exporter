# Luma Capture Exporter

[Luma AI](https://lumalabs.ai) の「Your Captures」を一括ダウンロードするスクリプトです。

## 機能

- Your Captures の全キャプチャを自動取得（「show more」相当を自動繰り返し）
- 複数のダウンロード形式に対応
- 既存ファイルはスキップ（中断・再開可能）
- 処理待ち・処理中のキャプチャは自動スキップ

## 対応ダウンロード形式

| 番号 | 形式 | 説明 |
|------|------|------|
| 1–3  | GLTF | フル / 中 / 低ポリゴン (.glb) |
| 4–6  | USDZ | フル / 中 / 低ポリゴン (.usdz) |
| 7–9  | OBJ  | フル / 中 / 低ポリゴン (.zip) |
| 10   | PLY ポイントクラウド | point_cloud.ply |
| 11   | Gaussian Splat PLY | gaussian_splatting_point_cloud.ply.zip |
| 12   | Luma Field | volume_model.luma |
| 13   | 360° プレビュー画像 | preview_360.jpg |
| 14   | フルメッシュ PLY | full_mesh.ply |
| 15   | 全アーティファクト | 上記すべて |

## セットアップ

```bash
git clone <this-repo>
cd luma-exporter
python3 -m venv .venv
.venv/bin/pip install httpx
```

## 使い方

### 1. cookies.txt を用意する

1. Chrome 拡張 **[Get cookies.txt LOCALLY](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)** をインストール
2. ブラウザで https://lumalabs.ai/dashboard/captures にログイン
3. 拡張のアイコンをクリック → **Export**
4. ダウンロードした `cookies.txt` をこのフォルダに置く

> `accessToken` の有効期限は **1時間** です。期限切れエラーが出た場合は再ログイン → 再エクスポートしてください。

### 2. 実行する

```bash
.venv/bin/python3 luma_exporter.py
```

起動するとダウンロード形式の選択メニューが表示されます。番号を入力すると、全キャプチャのダウンロードが始まります。

### 出力先

```
downloads/
└── GLTF_フル品質/
    ├── 営団8000系_3a797d97/
    │   └── 8000_textured_mesh_glb.glb
    ├── 横川駅_51905d6f/
    │   └── ...
    └── ...
```

## 注意事項

- **Featured Captures など他人のキャプチャはダウンロードしません**（Your Captures のみ対象）
- cookies.txt には認証情報が含まれるため、他人と共有しないでください
- cookies.txt は `.gitignore` に含まれており、誤ってコミットされません
