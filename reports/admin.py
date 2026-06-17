"""Django 管理画面の設定。"""
from django.contrib import admin

from .models import WorkRecord


@admin.register(WorkRecord)
class WorkRecordAdmin(admin.ModelAdmin):
    """作業記録の管理画面。"""

    list_display = ["date", "driver_name", "job_type", "customer_name", "place", "amount", "time"]
    list_filter = ["date", "driver_name", "job_type"]
    search_fields = ["driver_name", "customer_name", "place"]
    date_hierarchy = "date"
    ordering = ["-date", "driver_name"]
