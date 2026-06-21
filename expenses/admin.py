"""経費アプリの Django 管理画面設定。"""
from django.contrib import admin

from .models import Expense, ProcessingSite


@admin.register(ProcessingSite)
class ProcessingSiteAdmin(admin.ModelAdmin):
    list_display = ["name", "note", "created_at"]
    search_fields = ["name"]


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ["date", "expense_type", "site_name", "amount", "note"]
    list_filter = ["expense_type", "date"]
    search_fields = ["site_name"]
    date_hierarchy = "date"
