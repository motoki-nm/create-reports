"""日報アプリのビュー。"""
import logging
from datetime import date

from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render

from .forms import DriverForm, FilterForm, WorkRecordForm
from .models import Driver, WorkRecord

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
    """業務日報：日付ごとにドライバーの売上・件数を集計して表示する。"""
    dates = (
        WorkRecord.objects.values_list("date", flat=True)
        .distinct()
        .order_by("-date")
    )

    report_data = []
    for d in dates:
        records = WorkRecord.objects.filter(date=d)

        driver_summary = (
            records.values("driver_name")
            .annotate(
                total_amount=Sum("amount"),
                total_count=Count("id"),
                disposal=Count("id", filter=Q(job_type="処分")),
                purchase=Count("id", filter=Q(job_type="買取")),
                estimate=Count("id", filter=Q(job_type="見積")),
                other=Count("id", filter=Q(job_type="その他")),
            )
            .order_by("driver_name")
        )

        day_total = records.aggregate(total=Sum("amount"))["total"] or 0

        report_data.append({
            "date": d,
            "drivers": list(driver_summary),
            "day_total": day_total,
        })

    return render(request, "reports/company.html", {"report_data": report_data})


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
