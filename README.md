# Daily Report System — 日報管理システム

> **ドライバーが現場スマートフォンから作業を記録し、事務所がリアルタイムで集計・確認できる業務 Web アプリケーション。**
> 廃棄物処理・買取業務の「手書き日報 → 手集計」という非効率を解消するために設計・実装した。

---

## 背景・課題

廃棄物処理・買取業務では、ドライバーが1日複数件の現場を回り、帰社後に紙の日報を提出するフローが一般的。
このシステムは以下の課題を解決するために作成した。

| 課題 | 解決策 |
|------|--------|
| 帰社するまで実績が把握できない | 現場からスマホでリアルタイム入力 |
| 手書き集計にミスが発生する | Django ORM の集計クエリで自動化 |
| ドライバー名の表記揺れで集計が狂う | マスタからのプルダウン選択に統一 |

---

## 技術スタック

| Layer | Technology |
|---|---|
| Language | Python 3.13 |
| Framework | Django 6.0.5 |
| Database | SQLite 3（開発） |
| Frontend | Django Template Engine + Vanilla JS |
| Auth | Django Admin（管理者のみ） |
| Config | python-dotenv |

---

## 主な機能

### 1. 作業記録 新規入力（`/`）
- 当日日付を初期値としてセット（現場での入力ストレスを最小化）
- ドライバー名はマスタからプルダウン選択（表記揺れ防止）
- 作業時間は `<input type="time">` 2フィールド → JS で `"HH:MM ~ HH:MM"` に結合して保存

### 2. 作業記録一覧・絞り込み（`/list/`）
- 日付・ドライバー名での絞り込み（GET パラメータ）
- 絞り込み件数を即時フィードバック（「全N件中M件を表示」）

### 3. 業務日報・集計ビュー（`/company/`）
- 日付別・ドライバー別の売上・件数を自動集計
- `Sum` / `Count` / `Q` を組み合わせた仕事種類別内訳の横断集計

```python
driver_summary = records.values("driver_name").annotate(
    total_amount = Sum("amount"),
    disposal     = Count("id", filter=Q(job_type="処分")),
    purchase     = Count("id", filter=Q(job_type="買取")),
)
```

### 4. ドライバーマスタ管理（`/drivers/`）
- 登録名が入力フォーム・絞り込みドロップダウンに即時反映

---

## 設計上の工夫・技術的判断

「なぜこの設計にしたか」

### `driver_name` を ForeignKey にしなかった理由
過去の作業記録はドライバーが退職・削除されても履歴として残す必要がある。
`CharField` で名前を直接保存することで、マスタ削除後も参照整合性の問題なく過去データを保持できる。
入力時の表記揺れは `Driver` マスタからのプルダウン選択で防止した。

### 削除を POST のみに制限した理由
GET によるリソース削除は CSRF 攻撃のリスクがある。
`delete` / `driver_delete` ビューはいずれも `request.method == "POST"` の場合のみ削除を実行し、
GET アクセスは無効とした。

### 時間フィールドを `CharField` にした理由
`"09:00 ~ 11:30"` のような範囲表現は Django 標準の `TimeField` では表現できない。
フロントエンドで2つの `<input type="time">` から構成し、保存時に文字列として結合することで
フォーマットを統一しつつシンプルな実装を実現した。

### SQLite を採用した理由
現状は社内単拠点での利用を想定。スケールアップ時は `settings.py` の `DATABASES` を
PostgreSQL 等に切り替えるだけで対応可能な構成にしてある。

---

## アーキテクチャ

```
daily_report/
├── config/                  # プロジェクト設定
│   ├── settings.py          # 環境変数・DB・国際化設定
│   ├── urls.py              # ルートURL設定
│   └── wsgi.py
├── reports/                 # メインアプリケーション
│   ├── models.py            # データモデル（Driver / WorkRecord）
│   ├── views.py             # ビュー関数（CRUD + 集計）
│   ├── forms.py             # フォーム定義・バリデーション
│   ├── urls.py              # URLルーティング
│   ├── admin.py             # 管理画面設定
│   └── migrations/          # DBマイグレーション履歴
├── templates/reports/       # HTMLテンプレート
│   ├── base.html            # 共通レイアウト
│   ├── index.html           # 新規入力フォーム
│   ├── list.html            # 作業記録一覧・絞り込み
│   ├── edit.html            # 記録修正フォーム
│   ├── company.html         # 業務日報（集計ビュー）
│   └── drivers.html         # ドライバーマスタ管理
├── .env.example
├── manage.py
└── requirements.txt
```

---

## データモデル

### `Driver` — ドライバーマスタ

```python
class Driver(models.Model):
    name       = CharField(max_length=50, unique=True)
    created_at = DateTimeField(auto_now_add=True)
```

### `WorkRecord` — 作業記録

```python
class WorkRecord(models.Model):
    date          = DateField()
    driver_name   = CharField(max_length=50)           # ForeignKeyにしない設計（上記参照）
    job_type      = CharField(choices=JobType.choices) # 処分 / 買取 / 見積 / その他
    customer_name = CharField(max_length=100)
    place         = CharField(max_length=100)
    amount        = PositiveIntegerField()
    time          = CharField(max_length=20)           # "09:00 ~ 11:30" 形式
    created_at    = DateTimeField(auto_now_add=True)
    updated_at    = DateTimeField(auto_now=True)
```

---

## セットアップ

```bash
git clone https://github.com/nmgr09072-spec/create-reports.git
cd create-reports

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
# .env を編集して SECRET_KEY を設定

python3 manage.py migrate
python3 manage.py createsuperuser
python3 manage.py runserver
```

ブラウザで `http://127.0.0.1:8000/` を開く。

---

## 環境変数

| 変数 | 説明 |
|------|------|
| `SECRET_KEY` | Django シークレットキー（本番は必ず変更） |
| `DEBUG` | デバッグモード（本番は `False`） |

---

## 今後の課題（Roadmap）

- [ ] PostgreSQL への切り替え（本番対応）
- [ ] ドライバーごとのログイン認証
- [ ] Excel / CSV エクスポート
- [ ] 月次・ドライバー別売上グラフ（Chart.js）
- [ ] 本番デプロイ（Render / Gunicorn + Nginx）
