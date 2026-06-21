"""日報アプリのビュー。"""
import logging
from datetime import date, datetime  # datetime は work_end ビューで使用

from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render

from expenses.models import Expense
from .forms import DriverForm, FilterForm, WorkRecordForm
from .models import Driver, DriverDailyLog, WorkRecord

logger = logging.getLogger(__name__)


def index(request):
    """作業記録の入力フォームを表示・保存する。"""
    if request.method == "POST":
        form = WorkRecordForm(request.POST)
        if form.is_valid():
            form.save()
            logger.info(
                "作業記録を登録: %s %s",
                form.cleaned_data["driver_name"],
                form.cleaned_data["date"],
            )
            return redirect("reports:index")
    else:
        form = WorkRecordForm(initial={"date": date.today()})

    return render(request, "reports/index.html", {"form": form})


def record_list(request):
    """過去の作業記録一覧を表示する（日付・ドライバーで絞り込み可）。"""
    filter_form = FilterForm(request.GET or None)
    records = WorkRecord.objects.all()
    is_filtered = False

    if filter_form is not None and filter_form.is_valid():
        if filter_form.cleaned_data.get("date"):
            records = records.filter(date=filter_form.cleaned_data["date"])
            is_filtered = True
        if filter_form.cleaned_data.get("driver_name"):
            records = records.filter(driver_name=filter_form.cleaned_data["driver_name"])
            is_filtered = True

    if filter_form is None:
        filter_form = FilterForm()

    return render(request, "reports/list.html", {
        "records": records,
        "filter_form": filter_form,
        "is_filtered": is_filtered,
        "total_count": WorkRecord.objects.count(),
    })


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


def delete(request, pk: int):
    """作業記録を削除する（POST のみ）。"""
    record = get_object_or_404(WorkRecord, pk=pk)
    if request.method == "POST":
        logger.info("作業記録を削除: id=%s %s", pk, record)
        record.delete()
    return redirect("reports:list")


def company_report(request):
    """業務日報：日付ごとにドライバーの売上・件数・勤務時間を集計して表示する。"""
    dates = (
        WorkRecord.objects.values_list("date", flat=True)
        .distinct()
        .order_by("-date")
    )

    report_data = []
    for d in dates:
        records = WorkRecord.objects.filter(date=d)
        driver_names = sorted(records.values_list("driver_name", flat=True).distinct())

        drivers = []
        for name in driver_names:
            dr = records.filter(driver_name=name)
            total = dr.aggregate(total=Sum("amount"))["total"] or 0

            count_parts = []
            for jt in ["処分", "買取", "見積", "その他"]:
                cnt = dr.filter(job_type=jt).count()
                if cnt:
                    count_parts.append(f"{jt}{cnt}件")
            counts_str = "・".join(count_parts)

            # 業務終了ボタンで記録された時刻のみ使う
            log = DriverDailyLog.objects.filter(driver_name=name, date=d).first()
            work_end = log.end_time.strftime("%H:%M") if log else ""
            work_hours = work_end

            drivers.append({
                "name": name,
                "total": total,
                "counts": counts_str,
                "end_time": work_end,
                "work_hours": work_hours,
            })

        day_total = records.aggregate(total=Sum("amount"))["total"] or 0
        processing_expenses = Expense.objects.filter(date=d, expense_type="処理場")

        def _get(i: int):
            return drivers[i] if i < len(drivers) else None

        # 上段: 5スロット×2行 (Excel行5〜14)
        # 左=ドライバー[0-4], 右D列=スタッフ[0,2,4,6,8]/[1,3,5,7,9]
        upper_slots = [
            {
                "driver": _get(i),
                "r1": _get(i * 2),
                "r2": _get(i * 2 + 1),
            }
            for i in range(5)
        ]

        # 下段: 3スロット×2行 (Excel行15〜20)
        # 左=ドライバー[5-7], 右=D/E列+F/G列 それぞれ2行分
        lower_slots = [
            {
                "driver": _get(5 + i),
                "r1_c1": _get(10 + i * 4),
                "r1_c2": _get(10 + i * 4 + 1),
                "r2_c1": _get(10 + i * 4 + 2),
                "r2_c2": _get(10 + i * 4 + 3),
            }
            for i in range(3)
        ]

        report_data.append({
            "date": d,
            "upper_slots": upper_slots,
            "lower_slots": lower_slots,
            "day_total": day_total,
            "processing_expenses": processing_expenses,
        })

    return render(request, "reports/company.html", {"report_data": report_data})


def work_end(request):
    """業務終了ボタン。ドライバーが押すと現在時刻を終了時刻として記録する。"""
    drivers = Driver.objects.all()
    today = date.today()
    logs = {log.driver_name: log for log in DriverDailyLog.objects.filter(date=today)}

    if request.method == "POST":
        driver_name = request.POST.get("driver_name", "").strip()
        if driver_name:
            now = datetime.now().time().replace(second=0, microsecond=0)
            obj, created = DriverDailyLog.objects.update_or_create(
                driver_name=driver_name,
                date=today,
                defaults={"end_time": now},
            )
            action = "登録" if created else "更新"
            logger.info("業務終了%s: %s %s %s", action, driver_name, today, now)
        return redirect("reports:work_end")

    driver_status = [
        {"driver": d, "log": logs.get(d.name)}
        for d in drivers
    ]

    return render(request, "reports/work_end.html", {
        "driver_status": driver_status,
        "logs": list(logs.values()),
        "today": today,
    })


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

    drivers = Driver.objects.all()
    return render(request, "reports/drivers.html", {"form": form, "drivers": drivers})


def driver_delete(request, pk: int):
    """ドライバーを削除する（POST のみ）。"""
    driver = get_object_or_404(Driver, pk=pk)
    if request.method == "POST":
        logger.info("ドライバーを削除: %s", driver.name)
        driver.delete()
    return redirect("reports:drivers")
