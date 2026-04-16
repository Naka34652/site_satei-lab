# satei-lab 引き継ぎ書

最終更新: 2026-04-16

このファイルは、`satei-lab` のテーマ改修・価格データ収集・記事量産・WordPress 下書き投稿までの一連の仕様を、別スレッドの Codex / ChatGPT や別の Mac に引き継ぐための実務用ドキュメントです。

## 1. プロジェクト概要

このリポジトリは大きく 2 系統あります。

1. WordPress 子テーマ
2. 車買取相場データから記事を量産する Python パイプライン

現在の主用途は、`車選びドットコム買取` の公開データをもとに、

- 生データ取得
- 正規化
- summary CSV 生成
- Markdown 記事生成
- 投稿用メタ情報生成
- 手動投稿パック生成
- WordPress REST API での draft 投稿

までを一気通貫で回すことです。

## 2. 現在の到達点

2026-04-16 時点で以下が完了しています。

- `active=true` の 85 車種について:
  - raw HTML 取得
  - normalized データ生成
  - summary CSV 生成
  - `2026年版` 記事生成
  - 投稿用メタ情報 CSV 生成
  - 手動投稿用 YAML パック生成
  - WordPress draft 投稿用 JSON 生成
- 3 本サンプル:
  - `プリウス`
  - `ジェイド`
  - `NSX`
  については REST API draft 投稿の最小実装まで確認済み
- REST 投稿時の本文 HTML 化問題は修正済み

## 3. ディレクトリ構成

```text
satei-lab/
├─ config.yaml
├─ data/
│  ├─ raw/
│  │  ├─ api/
│  │  └─ html/
│  ├─ normalized/
│  │  ├─ cars/
│  │  └─ reference/
│  ├─ marts/
│  │  ├─ csv/
│  │  └─ summary/
│  └─ logs/
├─ output/
│  ├─ articles/
│  ├─ metadata/
│  ├─ manual_posting/
│  └─ wordpress_drafts/
├─ scripts/
│  ├─ analysis/
│  ├─ collectors/
│  ├─ exporters/
│  ├─ generators/
│  ├─ parsers/
│  ├─ pipelines/
│  ├─ posters/
│  ├─ shared/
│  └─ transformers/
└─ theme/
   └─ cocoon-child-master/
```

## 4. WordPress テーマ側の状態

子テーマ本体:

- `theme/cocoon-child-master/style.css`
- `theme/cocoon-child-master/functions.php`

現状のポイント:

- `style.css`
  - 量産記事向け共通 UI を追加済み
  - 主なクラス:
    - `sl-box`
    - `sl-box--note`
    - `sl-box--check`
    - `sl-cta`
    - `sl-btn`
    - `sl-related-box`
    - `sl-author-box`
    - `sl-table-wrap`
- `functions.php`
  - 投稿ページ限定の本文末尾 CTA を自動挿入
  - 固定ページ・一覧ページ・管理画面では表示しない
  - CTA 文言と URL は `sateilab_get_post_cta_data()` に集約

重要:

- 記事本文の下書き生成とは別に、テーマ側で記事下 CTA を自動表示する設計です
- 記事 generator 側では CTA を本文に埋め込んでいません

## 5. データ取得元の仕様

現在の主ソースは:

- `source_slug = kurumaerabi_kaitori`

サイト:

- 車選びドットコム買取

取得単位:

- 車種トップページ
- 必要に応じて年式 / 落ち年ページ variant

`models_master.csv` の `source_model_key` は JSON 文字列です。

例:

```csv
{"root":"1/155","year_variants":{"2024":"2y"}}
```

意味:

- `root`: 車種トップ URL のキー
- `year_variants`: 特定年式で優先する追加ページ

## 6. 記事生成上の最重要ルール

### 6-1. article_year と vehicle year は別

`target_year` は常に記事年です。

例:

- `2026` = `2026年版`

これは車両年式ではありません。

そのため:

- ファイル名は常に `...-2026.md`
- タイトルも常に `【2026年版】`
- 本文では別変数として `latest_available_year` を説明

### 6-2. 低サンプル時の文面ルール

`sample_count < 3` のときは、記事文面を慎重にしています。

具体的には:

- `参考値`
- `事例ベース`
- `断定を避ける`

というニュアンスを強めます。

また、

- `price_common_min == price_common_max`

のときは、

- `644.5万円〜644.5万円`

ではなく、

- `644.5万円前後`

と表現します。

### 6-3. 高値事例の扱い

代表値は `中央値` を優先します。

ただし高値事例は必ず補助的に見せます。

記事内の考え方:

- 代表値: `price_median`
- よくあるレンジ: `price_common_min` / `price_common_max`
- 高値事例: `high_price` / `high_price_case`

## 7. 車種分類の仕様

分類ファイル:

- `data/normalized/reference/model_classification.csv`

主分類:

1. `通常車種`
2. `古い年式中心の車種`
3. `高額・スポーツ系車種`

補助分類:

- `軽自動車`
- `ミニバン`
- `商用車`
- `EV・FCV`

現在の件数:

- 通常車種: 43
- 古い年式中心の車種: 16
- 高額・スポーツ系車種: 26

分類の使い方:

- 結論サマリー
- 注意点
- FAQ
- 補足段落

だけを軽く出し分けています。

記事構成そのものはまだ大改造していません。

## 8. 主要スクリプト一覧

### 8-1. 取得・整形・出力

- `scripts/pipelines/run_single_model_pipeline.py`
  - 1 車種を `fetch -> parse -> normalize -> summary export` まで通す
- `scripts/pipelines/run_market_pipeline_batch.py`
  - `active=true` 全車種を batch 実行
- `scripts/collectors/fetch_source_data.py`
  - raw HTML 取得
- `scripts/parsers/parse_source_data.py`
  - `__NEXT_DATA__` から配列抽出
- `scripts/transformers/normalize_price_data.py`
  - 正規化
- `scripts/transformers/build_model_dataset.py`
  - summary 集計
- `scripts/exporters/export_model_csv.py`
  - marts / summary CSV 出力

### 8-2. 記事・メタ情報生成

- `scripts/analysis/generate_model_classification.py`
  - 車種分類 CSV を生成
- `scripts/generators/generate_market_article.py`
  - 1 記事生成
- `scripts/generators/generate_market_article_batch.py`
  - active=true 全車種の記事を生成
- `scripts/generators/generate_article_metadata.py`
  - 投稿用メタ情報 CSV 生成
- `scripts/generators/generate_manual_posting_pack.py`
  - 手動投稿用 YAML パック生成
- `scripts/generators/generate_wordpress_draft_payload.py`
  - REST API 投稿用 JSON 生成

### 8-3. 投稿

- `scripts/posters/post_wordpress_drafts.py`
  - WordPress REST API で draft 投稿
  - 同 slug があれば更新
  - なければ新規作成

### 8-4. 共通

- `scripts/shared/config.py`
  - `config.yaml` 読み込み
- `scripts/shared/io.py`
  - CSV / JSON / text の入出力
- `scripts/shared/logging_utils.py`
  - ログ
- `scripts/shared/markup.py`
  - Markdown -> 簡易 HTML 変換

## 9. 重要な出力ファイル

### 9-1. 記事

- `output/articles/{model_slug}-kaitori-soba-2026.md`

### 9-2. メタ情報

- `output/metadata/article_metadata_2026.csv`

### 9-3. 手動投稿用

- sample:
  - `output/manual_posting/2026_sample/`
- 全件:
  - `output/manual_posting/2026_all/`

### 9-4. WordPress draft 投稿用 JSON

- sample 3 本:
  - `output/wordpress_drafts/wordpress_draft_payload_2026_sample.json`
- active=true 全 85 本:
  - `output/wordpress_drafts/wordpress_draft_payload_2026_all.json`

### 9-5. REST 投稿結果

実行後に作られる:

- `output/wordpress_drafts/*_post_results.json`

### 9-6. ログ

- `data/logs/`

## 10. 新しい Mac でのセットアップ

### 10-1. 前提

- macOS
- `python3` が使えること
- インターネット接続があること
- WordPress REST API を使う場合は Application Password が発行済みであること

### 10-2. 依存関係

このプロジェクトは基本的に標準ライブラリのみで動くようにしています。

つまり通常は `pip install` 不要です。

### 10-3. 配置

任意の場所に `satei-lab` を置けば動きます。

例:

```bash
cd /path/to/satei-lab
```

注意:

- `config.yaml` は拡張子が `.yaml` ですが、中身は JSON 形式です
- `scripts/shared/config.py` は JSON として読みます

### 10-4. 最初に確認するもの

```bash
python3 scripts/generators/generate_market_article.py --help
python3 scripts/posters/post_wordpress_drafts.py --help
```

## 11. よく使うコマンド

以下はすべて repo root で実行する前提です。

### 11-1. 1 車種だけ取得から記事まで

```bash
python3 scripts/pipelines/run_single_model_pipeline.py
python3 scripts/generators/generate_market_article.py --model-slug toyota-prius --target-year 2026
```

### 11-2. 全 85 車種の記事再生成

```bash
python3 scripts/pipelines/run_market_pipeline_batch.py --target-year 2026
```

### 11-3. 車種分類 CSV 再生成

```bash
python3 scripts/analysis/generate_model_classification.py
```

### 11-4. 投稿用メタ情報 CSV 再生成

```bash
python3 scripts/generators/generate_article_metadata.py --target-year 2026
```

### 11-5. 手動投稿用パック

3 本 sample:

```bash
python3 scripts/generators/generate_manual_posting_pack.py \
  --target-year 2026 \
  --model-slugs toyota-prius,honda-jade,honda-nsx
```

全件:

```bash
python3 scripts/generators/generate_manual_posting_pack.py \
  --target-year 2026 \
  --all-active \
  --output-label all
```

### 11-6. WordPress draft 投稿用 JSON

3 本 sample:

```bash
python3 scripts/generators/generate_wordpress_draft_payload.py \
  --target-year 2026 \
  --model-slugs toyota-prius,honda-jade,honda-nsx
```

全件:

```bash
python3 scripts/generators/generate_wordpress_draft_payload.py \
  --target-year 2026 \
  --all-active \
  --output-label all
```

### 11-7. WordPress に draft 投稿

環境変数:

```bash
export WP_SITE_URL="https://satei-lab.com"
export WP_USERNAME="あなたのWordPressユーザー名"
export WP_APP_PASSWORD="xxxx xxxx xxxx xxxx xxxx xxxx"
```

sample 3 本:

```bash
python3 scripts/posters/post_wordpress_drafts.py \
  --input-json output/wordpress_drafts/wordpress_draft_payload_2026_sample.json
```

全件:

```bash
python3 scripts/posters/post_wordpress_drafts.py \
  --input-json output/wordpress_drafts/wordpress_draft_payload_2026_all.json
```

## 12. WordPress 投稿仕様

### 12-1. REST 投稿で送るもの

現在 `post_wordpress_drafts.py` が送っているのは次です。

- `title`
- `slug`
- `content`
- `excerpt`
- `status=draft`

### 12-2. 本文形式

重要:

- JSON は Markdown 本文を保持
- 投稿直前に `scripts/shared/markup.py` で HTML 化

変換対象:

- `##` -> `<h2>`
- `###` -> `<h3>`
- 箇条書き -> `<ul><li>`
- 表 -> `<table>`
- `**太字**` -> `<strong>`

### 12-3. slug の挙動

- 同じ slug の投稿が既にある: 更新
- slug が存在しない: 新規作成

つまり再投稿時の重複を避ける設計です。

### 12-4. 現時点で未対応のもの

まだ REST 投稿本体では扱っていないもの:

- `category_candidates`
- `meta_description`
- `eyecatch_title_candidate`

これらは JSON / YAML には残していますが、REST 投稿時に WordPress の投稿本体へはまだ入れていません。

## 13. 手動投稿仕様

手動投稿用は 1 記事 1 YAML です。

内容:

- `post_title`
- `post_name`
- `excerpt`
- `meta_description`
- `category_candidates`
- `eyecatch_title_candidate`
- `post_status`
- `post_content`

`post_content` はすでに簡易 HTML 化済みなので、WordPress 管理画面に貼りやすいです。

## 14. 運用上の注意

### 14-1. source の前提

現在の買取相場記事は `車選びドットコム買取` 前提です。

`カーセンサー販売価格` ベースの旧案は不採用です。

### 14-2. 年式ページの扱い

車種トップだけでは高値事例がズレるケースがあるため、

- `root`
- `year_variants`

の二層で持つ設計です。

### 14-3. sample_count が少ない記事

低サンプル時は文面が慎重になります。

これは仕様です。

勝手に強気な断定へ戻さない方が安全です。

### 14-4. 手動投稿パックと REST 投稿

- 手動投稿パックは YAML + HTML
- REST 投稿用 JSON は Markdown 本文を保持し、投稿時に HTML 変換

この違いを混同しないでください。

## 15. 別スレッドの Codex / ChatGPT へ渡す要約テンプレ

新しいスレッドで最初に渡すなら、以下をそのまま使えます。

```text
この repo は satei-lab の WordPress 子テーマと、車買取相場記事の量産パイプラインです。

重要ルール:
- target_year は記事年であり、車両年式ではありません
- 記事タイトルとファイル名は常に {target_year}年版 ベースです
- 本文中では latest_available_year を別で説明します
- 低サンプル(sample_count < 3)では参考値・事例ベースの文面にします
- WordPress REST 投稿時は Markdown をそのまま送らず、HTML 化して投稿します
- 同じ slug があれば更新、なければ新規 draft 作成です

主要ファイル:
- HANDOVER.md
- config.yaml
- data/normalized/reference/models_master.csv
- data/normalized/reference/model_classification.csv
- scripts/generators/generate_market_article.py
- scripts/generators/generate_article_metadata.py
- scripts/generators/generate_manual_posting_pack.py
- scripts/generators/generate_wordpress_draft_payload.py
- scripts/posters/post_wordpress_drafts.py
- scripts/shared/markup.py

主な出力:
- output/articles/
- output/metadata/article_metadata_2026.csv
- output/manual_posting/2026_all/
- output/wordpress_drafts/wordpress_draft_payload_2026_all.json
```

## 16. ChatGPT に操作を教わるときのおすすめ依頼文

### 16-1. 記事再生成したいとき

```text
HANDOVER.md を前提に、2026年版の全85車種記事を再生成したいです。run_market_pipeline_batch.py を使う前提で、実行前チェックとコマンドを教えてください。
```

### 16-2. WordPress 下書き投稿したいとき

```text
HANDOVER.md を前提に、wordpress_draft_payload_2026_all.json を使って WordPress に draft 投稿したいです。post_wordpress_drafts.py の実行コマンドと確認手順を教えてください。
```

### 16-3. 1 車種だけ直したいとき

```text
HANDOVER.md を前提に、toyota-prius だけ記事とメタ情報を再生成したいです。必要なコマンドを順番に教えてください。
```

## 17. 最後に

このリポジトリは、すでに「取得 -> 記事生成 -> 投稿用整形 -> WordPress draft 投稿」まで通る状態です。

今後の作業では、まずこのファイルを基準にして、

- 何を再生成したいのか
- 手動投稿したいのか
- REST 投稿したいのか
- テーマ側を触りたいのか

を切り分けると、Codex / ChatGPT の指示精度がかなり上がります。
