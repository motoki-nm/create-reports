"""経費アプリのビュー。"""
import logging
from datetime import date, timedelta

from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ExpenseForm, ProcessingSiteForm
from .models import Expense, ProcessingSite

logger = logging.getLogger(__name__)


def _recent_dates(days: int = 7) -> list[dict]:
    """直近N日分の日付リストを返す（業務日報日付選択用）。"""
    today = date.today()
    result = []
    for i in range(days):
        d = today - timedelta(days=i)
        if i == 0:
            label = f"今日 ({d.month}/{d.day})"
        elif i == 1:
            label = f"昨日 ({d.month}/{d.day})"
        else:
            label = f"{d.month}/{d.day}（{i}日前）"
        result.append({"value": d.isoformat(), "label": label})
    return result


def expense_list(request):
    """経費一覧と登録フォームを表示する。"""
    date_str = request.GET.get("date", "")
    expenses = Expense.objects.all()

    if date_str:
        try:
            from datetime import datetime
            filter_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            expenses = expenses.filter(date=filter_date)
        except ValueError:
            pass

    form = ExpenseForm(initial={"date": date.today()})
    total = expenses.aggregate(total=Sum("amount"))["total"] or 0

    return render(request, "expenses/list.html", {
        "expenses": expenses,
        "form": form,
        "total": total,
        "date_filter": date_str,
        "preset_sites": ProcessingSite.objects.all(),
        "recent_dates": _recent_dates(7),
        "today_str": date.today().isoformat(),
    })


def expense_add(request):
    """経費を登録する（POST のみ）。"""
    if request.method == "POST":
        form = ExpenseForm(request.POST)
        if form.is_valid():
            expense = form.save()
            logger.info("経費登録: %s %s ¥%s", expense.date, expense.site_name, expense.amount)
            return redirect("expenses:list")
    return redirect("expenses:list")


def expense_delete(request, pk: int):
    """経費を削除する（POST のみ）。"""
    expense = get_object_or_404(Expense, pk=pk)
    if request.method == "POST":
        logger.info("経費削除: id=%s %s", pk, expense)
        expense.delete()
    return redirect("expenses:list")


def site_list(request):
    """処理場マスター一覧と登録フォームを表示する。"""
    if request.method == "POST":
        form = ProcessingSiteForm(request.POST)
        if form.is_valid():
            site = form.save()
            logger.info("処理場登録: %s", site.name)
            return redirect("expenses:sites")
    else:
        form = ProcessingSiteForm()

    sites = ProcessingSite.objects.all()
    return render(request, "expenses/sites.html", {"form": form, "sites": sites})


def site_delete(request, pk: int):
    """処理場マスターを削除する（POST のみ）。"""
    site = get_object_or_404(ProcessingSite, pk=pk)
    if request.method == "POST":
        logger.info("処理場削除: %s", site.name)
        site.delete()
    return redirect("expenses:sites")


def api_sites(request):
    """処理場名一覧をJSONで返す（フォームの自動補完用）。"""
    sites = list(ProcessingSite.objects.values("id", "name"))
    return JsonResponse({"sites": sites})
