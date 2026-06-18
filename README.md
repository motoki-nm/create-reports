# Daily Report System — 日報管理システム

廃棄物処理・買取業務を行う企業向けの **ドライバー日報管理 Web アプリケーション**。
ドライバーが現場からスマートフォンで作業記録を入力し、事務所がリアルタイムで集計・確認できる業務システム。

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.13 |
| Framework | Django 6.0.5 |
| Database | SQLite 3（開発） |
| Frontend | Django Template Engine + Vanilla JS |
| Auth | Django Admin（管理者のみ） |
| Config | python-dotenv |

---

## Architecture

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
│   ├── base.html            # 共通レイアウト・グローバルCSS
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

## Data Model

### `Driver` — ドライバーマスタ

```python
class Driver(models.Model):
    name       = CharField(max_length=50, unique=True)
    created_at = DateTimeField(auto_now_add=True)
```

ドライバー名を一元管理するマスタテーブル。
`WorkRecord.driver_name` はこのテーブルから選択させることで表記揺れを防ぐ。

---

### `WorkRecord` — 作業記録

```python
class WorkRecord(models.Model):
    date          = DateField()                        # 作業日
    driver_name   = CharField(max_length=50)           # ドライバー名（Driver.name から選択）
    job_type      = CharField(choices=JobType.choices) # 処分 / 買取 / 見積 / その他
    customer_name = CharField(max_length=100)          # 顧客名
    place         = CharField(max_length=100)          # 作業地名
    amount        = PositiveIntegerField()             # 売上金額（円）
    time          = CharField(max_length=20)           # 作業時間帯（例: "09:00 ~ 11:30"）
    created_at    = DateTimeField(auto_now_add=True)
    updated_at    = DateTimeField(auto_now=True)
```

`ordering = ["-date", "driver_name"]` — 最新日付・ドライバー名昇順がデフォルト。

---

## URL Routing

| Method | URL | View | 説明 |
|---|---|---|---|
| GET / POST | `/` | `index` | 新規作業記録の入力 |
| GET | `/list/` | `record_list` | 一覧表示・日付/ドライバー絞り込み |
| GET / POST | `/edit/<pk>/` | `edit` | 既存記録の修正 |
| POST | `/delete/<pk>/` | `delete` | 記録削除（POST のみ受け付け） |
| GET | `/company/` | `company_report` | 業務日報（日付別集計） |
| GET / POST | `/drivers/` | `driver_list` | ドライバーマスタ管理 |
| POST | `/drivers/delete/<pk>/` | `driver_delete` | ドライバー削除 |
| `*` | `/admin/` | Django Admin | スーパーユーザー管理画面 |

---

## Features

### 1. 作業記録 新規入力（`/`）
- 当日日付を初期値としてセット
- ドライバー名はマスタからプルダウン選択（`Driver` モデル連動）
- 作業時間は開始・終了の2フィールドで入力 → `"HH:MM ~ HH:MM"` 形式で保存
  - `<input type="time">` を使用し、半角・フォーマット統一を強制
  - JavaScript でフォーム送信時に連結

### 2. 作業記録一覧（`/list/`）
- 日付・ドライバー名での絞り込み（GET パラメータ）
- 絞り込み適用時は件数フィードバックを表示（「全N件中M件を表示」）
- 各レコードから修正・削除へ直接遷移

### 3. 業務日報（`/company/`）
- 日付ごとにドライバー別の売上・件数を集計
- `django.db.models.Sum` / `Count` / `Q` を使ったアグリゲーション
- 仕事種類別内訳（処分・買取・見積・その他）を横断集計

```python
driver_summary = records.values("driver_name").annotate(
    total_amount = Sum("amount"),
    disposal     = Count("id", filter=Q(job_type="処分")),
    purchase     = Count("id", filter=Q(job_type="買取")),
    ...
)
```

### 4. ドライバーマスタ管理（`/drivers/`）
- ドライバーの追加・削除
- 登録された名前が入力フォーム・絞り込みドロップダウンに即時反映

---

## Setup

### 必要環境
- Python 3.11+
- pip

### インストール手順

```bash
git clone https://github.com/nmgr09072-spec/create-reports.git
cd create-reports

python3 -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# .env を編集して SECRET_KEY を設定

python3 manage.py migrate
python3 manage.py createsuperuser   # 管理画面ログイン用
python3 manage.py runserver
```

ブラウザで `http://127.0.0.1:8000/` を開く。

---

## Environment Variables

`.env.example` を `.env` にコピーして設定。

```env
SECRET_KEY=your-secret-key-here
DEBUG=True
```

| 変数 | 説明 | デフォルト |
|---|---|---|
| `SECRET_KEY` | Django シークレットキー（本番は必ず変更） | `change-me-in-production` |
| `DEBUG` | デバッグモード | `True` |

---

## Design Decisions

**SQLite を採用した理由**
現状は社内単拠点での利用を想定。スケールアップ時は `settings.py` の `DATABASES` を PostgreSQL 等に切り替えるだけで対応可能な構成にしている。

**`driver_name` を ForeignKey にしなかった理由**
過去の作業記録はドライバーが退職・削除されても履歴として残す必要がある。`CharField` で名前を直接保存することで、マスタ削除後も参照整合性の問題なく過去データを保持できる。入力時の表記揺れは `Driver` マスタからのプルダウン選択で防止している。

**削除を POST のみに制限した理由**
GET によるリソース削除は CSRF 攻撃のリスクがある。`delete` / `driver_delete` ビューはいずれも `request.method == "POST"` の場合のみ削除を実行し、GET アクセスは無効とした。

**時間フィールドを `CharField` にした理由**
`"09:00 ~ 11:30"` のような範囲表現は Django 標準の `TimeField` では表現できない。フロントエンドで2つの `<input type="time">` から構成し、保存時に文字列として結合することでシンプルな実装を実現した。

---

## Future Roadmap

- [ ] PostgreSQL への切り替え（本番対応）
- [ ] 認証機能（ドライバーごとのログイン）
- [ ] Excel / CSV エクスポート機能
- [ ] 月次・ドライバー別売上グラフ（Chart.js）
- [ ] 本番デプロイ（Gunicorn + Nginx）
