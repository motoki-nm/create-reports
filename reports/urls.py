"""reports アプリの URL 設定。"""
from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    path("", views.index, name="index"),
    path("list/", views.record_list, name="list"),
    path("list/export/", views.export_csv, name="export_csv"),
    path("edit/<int:pk>/", views.edit, name="edit"),
    path("delete/<int:pk>/", views.delete, name="delete"),
    path("company/", views.company_report, name="company"),
    path("monthly/", views.monthly_chart, name="monthly"),
    path("drivers/", views.driver_list, name="drivers"),
    path("drivers/delete/<int:pk>/", views.driver_delete, name="driver_delete"),
    path("work-end/", views.work_end, name="work_end"),
    path("print/today/", views.print_today, name="print_today"),
]
