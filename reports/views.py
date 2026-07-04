"""日報アプリのビュー。"""
import csv
import json
import logging
from datetime import date, datetime

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from expenses.models import Expense
from .forms import DriverForm, FilterForm, WorkRecordForm
from .models import Driver, DriverDailyLog, WorkRecord

logger = logging.getLogger(__name__)

_CHART_COLORS = [
    "#4a90d9", "#27ae60", "#e67e22", "#e74c3c",
    "#9b59b6", "#1abc9c", "#f39c12", "#34495e",
]


# ---------------------------------------------------------------------------
# 共通ヘルパー
# ---------------------------------------------------------------------------

def _build_company_layout(records_qs) -> tuple[list, list, int]:
    """業務日報用のドライバー配置リストと日計を返す。company_report/print_today で共用。"""
    driver_names = sorted(records_qs.values_list("driver_name", flat=True).distinct())
    logs = {
        log.driver_name: log
        for log in DriverDailyLog.objects.filter(
            date=records_qs.first().date if records_qs.exists() else date.today()
        )
    }

    drivers = []
    for name in driver_names:
        dr = records_qs.filter(driver_name=name)
        total = dr.aggregate(total=Sum("amount"))["total"] or 0
        count_parts = [
            f"{jt}{dr.filter(job_type=jt).count()}件"
            for jt in ["処分", "買取", "見積", "その他"]
            if dr.filter(job_type=jt).exists()
        ]
        log = logs.get(name)
        end_time = log.end_time.strftime("%H:%M") if log else ""
        drivers.append({
            "name": name,
            "total": total,
            "counts": "・".join(count_parts),
            "end_time": end_time,
            "work_hours": end_time,
        })

    def _get(i):
        return drivers[i] if i < len(drivers) else None

    upper_slots = [
        {"driver": _get(i), "r1": _get(i * 2), "r2": _get(i * 2 + 1)}
        for i in range(5)
    ]
    lower_slots = [
        {
            "driver": _get(5 + i),
            "r1_c1": _get(10 + i * 4), "r1_c2": _get(10 + i * 4 + 1),
            "r2_c1": _get(10 + i * 4 + 2), "r2_c2": _get(10 + i * 4 + 3),
        }
        for i in range(3)
    ]
    day_total = records_qs.aggregate(total=Sum("amount"))["total"] or 0
    return upper_slots, lower_slots, day_total


# ---------------------------------------------------------------------------
# 作業記録
# ---------------------------------------------------------------------------

@login_required
def index(request):
    """作業記録の入力フォーム。ログインユーザー名がドライバー名と一致すれば自動選択。"""
    if request.method == "POST":
        form = WorkRecordForm(request.POST)
        if form.is_valid():
            form.save()
            logger.info("作業記録を登録: %s %s", form.cleaned_data["driver_name"], form.cleaned_data["date"])
            return redirect("reports:index")
    else:
        initial = {"date": date.today()}
        if Driver.objects.filter(name=request.user.username).exists():
            initial["driver_name"] = request.user.username
        form = WorkRecordForm(initial=initial)

    return render(request, "reports/index.html", {"form": form})


@login_required
def record_list(request):
    """過去の作業記録一覧（日付・ドライバーで絞り込み可）。"""
    filter_form = FilterForm(request.GET or None)
    records = WorkRecord.objects.all()
    is_filtered = False

    if filter_form and filter_form.is_valid():
        if filter_form.cleaned_data.get("date"):
            records = records.filter(date=filter_form.cleaned_data["date"])
            is_filtered = True
        if filter_form.cleaned_data.get("driver_name"):
            records = records.filter(driver_name=filter_form.cleaned_data["driver_name"])
            is_filtered = True

    return render(request, "reports/list.html", {
        "records": records,
        "filter_form": filter_form or FilterForm(),
        "is_filtered": is_filtered,
        "total_count": WorkRecord.objects.count(),
    })


@login_required
def export_csv(request):
    """作業記録を CSV でダウンロード（一覧の絞り込み条件を引き継ぐ）。"""
    records = WorkRecord.objects.all()
    if request.GET.get("date"):
        records = records.filter(date=request.GET["date"])
    if request.GET.get("driver_name"):
        records = records.filter(driver_name=request.GET["driver_name"])

    response = HttpResponse(content_type="text/csv; charset=utf-8-sig")
    response["Content-Disposition"] = f'attachment; filename="records_{date.today()}.csv"'
    writer = csv.writer(response)
    writer.writerow(["日付", "ドライバー", "仕事種類", "お客様名", "地名", "金額（円）", "開始", "終了"])
    for r in records:
        writer.writerow([
            r.date, r.driver_name, r.job_type, r.customer_name, r.place, r.amount,
            r.start_time.strftime("%H:%M") if r.start_time else "",
            r.end_time.strftime("%H:%M") if r.end_time else "",
        ])
    logger.info("CSV エクスポート: %d 件", records.count())
    return response


@login_required
def edit(request, pk: int):
    """作業記録を修正する。"""
    record = get_object_or_404(WorkRecord, pk=pk)
    if request.method == "POST":
        form = WorkRecordForm(request.POST, instance=record)
        if form.is_valid():
            form.save()
            logger.info("作業記録を修正: id=%s", pk)
            return redirect("reports:list")
    else:
        form = WorkRecordForm(instance=record)
    return render(request, "reports/edit.html", {"form": form, "record": record})


@login_required
def delete(request, pk: int):
    """作業記録を削除する（POST のみ）。"""
    record = get_object_or_404(WorkRecord, pk=pk)
    if request.method == "POST":
        logger.info("作業記録を削除: id=%s %s", pk, record)
        record.delete()
    return redirect("reports:list")


# ---------------------------------------------------------------------------
# 集計・日報
# ---------------------------------------------------------------------------

@login_required
def company_report(request):
    """業務日報：日付ごとの売上・件数・勤務時間を集計。"""
    dates = WorkRecord.objects.values_list("date", flat=True).distinct().order_by("-date")

    report_data = []
    for d in dates:
        records = WorkRecord.objects.filter(date=d)
        upper_slots, lower_slots, day_total = _build_company_layout(records)
        report_data.append({
            "date": d,
            "upper_slots": upper_slots,
            "lower_slots": lower_slots,
            "day_total": day_total,
            "processing_expenses": Expense.objects.filter(date=d, expense_type="処理場"),
        })

    return render(request, "reports/company.html", {"report_data": report_data})


@login_required
def monthly_chart(request):
    """売上グラフ：月別・日別をタブで切り替え（Chart.js）。"""
    raw_monthly = (
        WorkRecord.objects
        .annotate(month=TruncMonth("date"))
        .values("month", "driver_name")
        .annotate(total=Sum("amount"))
        .order_by("month", "driver_name")
    )
    if not raw_monthly:
        return render(request, "reports/monthly_chart.html", {"has_data": False})

    # --- 月別データ ---
    months = sorted({d["month"].strftime("%Y年%m月") for d in raw_monthly})
    drivers = sorted({d["driver_name"] for d in raw_monthly})
    monthly_lookup: dict[str, dict[str, int]] = {}
    for d in raw_monthly:
        m = d["month"].strftime("%Y年%m月")
        monthly_lookup.setdefault(m, {})[d["driver_name"]] = d["total"]

    monthly_datasets = [
        {
            "label": driver,
            "data": [monthly_lookup.get(m, {}).get(driver, 0) for m in months],
            "borderColor": _CHART_COLORS[i % len(_CHART_COLORS)],
            "backgroundColor": _CHART_COLORS[i % len(_CHART_COLORS)] + "33",
            "tension": 0.3,
            "fill": False,
        }
        for i, driver in enumerate(drivers)
    ]
    monthly_rows = [
        {
            "month": m,
            "amounts": [monthly_lookup.get(m, {}).get(d, 0) for d in drivers],
            "total": sum(monthly_lookup.get(m, {}).values()),
        }
        for m in months
    ]

    # --- 日別データ ---
    available_months = sorted(
        {d["month"].strftime("%Y-%m") for d in raw_monthly}, reverse=True
    )
    selected_month_str = request.GET.get("month") or available_months[0]

    daily_chart_data = None
    daily_rows: list = []
    daily_total = 0
    try:
        sel = datetime.strptime(selected_month_str, "%Y-%m")
    except ValueError:
        sel = None

    if sel:
        raw_daily = (
            WorkRecord.objects
            .filter(date__year=sel.year, date__month=sel.month)
            .values("date", "driver_name")
            .annotate(total=Sum("amount"))
            .order_by("date", "driver_name")
        )
        days = sorted({str(d["date"]) for d in raw_daily})
        day_labels = [f"{datetime.strptime(d, '%Y-%m-%d').day}日" for d in days]
        daily_lookup: dict[str, dict[str, int]] = {}
        for d in raw_daily:
            daily_lookup.setdefault(str(d["date"]), {})[d["driver_name"]] = d["total"]

        daily_datasets = [
            {
                "label": driver,
                "data": [daily_lookup.get(day, {}).get(driver, 0) for day in days],
                "backgroundColor": _CHART_COLORS[i % len(_CHART_COLORS)] + "cc",
                "borderColor": _CHART_COLORS[i % len(_CHART_COLORS)],
                "borderWidth": 1,
            }
            for i, driver in enumerate(drivers)
        ]
        daily_chart_data = json.dumps(
            {"labels": day_labels, "datasets": daily_datasets}, ensure_ascii=False
        )
        daily_rows = [
            {
                "date": d,
                "amounts": [daily_lookup.get(d, {}).get(dr, 0) for dr in drivers],
                "total": sum(daily_lookup.get(d, {}).values()),
            }
            for d in days
        ]
        daily_total = sum(r["total"] for r in daily_rows)

    available_month_labels = [
        {"value": m, "label": datetime.strptime(m, "%Y-%m").strftime("%Y年%m月")}
        for m in available_months
    ]

    return render(request, "reports/monthly_chart.html", {
        "has_data": True,
        "chart_data": json.dumps({"labels": months, "datasets": monthly_datasets}, ensure_ascii=False),
        "monthly_rows": monthly_rows,
        "drivers": drivers,
        "available_months": available_month_labels,
        "selected_month": selected_month_str,
        "daily_chart_data": daily_chart_data,
        "daily_rows": daily_rows,
        "daily_total": daily_total,
        "selected_month_label": datetime.strptime(selected_month_str, "%Y-%m").strftime("%Y年%m月") if sel else "",
    })


@login_required
def print_today(request):
    """今日の全ドライバー作業日報＋業務日報（印刷用）。"""
    target_date = request.GET.get("date") or date.today()
    if isinstance(target_date, str):
        try:
            target_date = datetime.strptime(target_date, "%Y-%m-%d").date()
        except ValueError:
            target_date = date.today()

    drivers_with_records = (
        WorkRecord.objects.filter(date=target_date)
        .values_list("driver_name", flat=True)
        .distinct()
        .order_by("driver_name")
    )

    driver_reports = []
    for name in drivers_with_records:
        records = WorkRecord.objects.filter(date=target_date, driver_name=name).order_by("created_at")
        totals = {}
        for jt in ["処分", "買取", "見積", "その他"]:
            agg = records.filter(job_type=jt).aggregate(cnt=Count("id"), total=Sum("amount"))
            if agg["cnt"]:
                totals[jt] = {"count": agg["cnt"], "total": agg["total"] or 0}
        grand_total = records.aggregate(total=Sum("amount"))["total"] or 0
        log = DriverDailyLog.objects.filter(driver_name=name, date=target_date).first()
        driver_reports.append({
            "name": name,
            "records": records,
            "totals": totals,
            "grand_total": grand_total,
            "end_time": log.end_time.strftime("%H:%M") if log else "―",
        })

    records_all = WorkRecord.objects.filter(date=target_date)
    upper_slots, lower_slots, day_total = _build_company_layout(records_all)

    return render(request, "reports/print_today.html", {
        "target_date": target_date,
        "driver_reports": driver_reports,
        "upper_slots": upper_slots,
        "lower_slots": lower_slots,
        "day_total": day_total,
        "processing_expenses": Expense.objects.filter(date=target_date, expense_type="処理場"),
    })


# ---------------------------------------------------------------------------
# ドライバーマスター
# ---------------------------------------------------------------------------

@login_required
def driver_list(request):
    """ドライバー一覧・登録画面。"""
    if request.method == "POST":
        form = DriverForm(request.POST)
        if form.is_valid():
            form.save()
            logger.info("ドライバーを登録: %s", form.cleaned_data["name"])
            return redirect("reports:drivers")
    else:
        form = DriverForm()
    return render(request, "reports/drivers.html", {"form": form, "drivers": Driver.objects.all()})


@login_required
def driver_delete(request, pk: int):
    """ドライバーを削除する（POST のみ）。"""
    driver = get_object_or_404(Driver, pk=pk)
    if request.method == "POST":
        logger.info("ドライバーを削除: %s", driver.name)
        driver.delete()
    return redirect("reports:drivers")


# ---------------------------------------------------------------------------
# 業務終了
# ---------------------------------------------------------------------------

@login_required
def work_end(request):
    """業務終了ボタン。ドライバーが押すと現在時刻を終了時刻として記録する。"""
    today = date.today()
    logs = {log.driver_name: log for log in DriverDailyLog.objects.filter(date=today)}

    if request.method == "POST":
        driver_name = request.POST.get("driver_name", "").strip()
        if driver_name:
            now = datetime.now().time().replace(second=0, microsecond=0)
            _, created = DriverDailyLog.objects.update_or_create(
                driver_name=driver_name,
                date=today,
                defaults={"end_time": now},
            )
            logger.info("業務終了%s: %s %s %s", "登録" if created else "更新", driver_name, today, now)
        return redirect("reports:work_end")

    return render(request, "reports/work_end.html", {
        "driver_status": [{"driver": d, "log": logs.get(d.name)} for d in Driver.objects.all()],
        "logs": list(logs.values()),
        "today": today,
    })
