"""reports アプリの URL 設定。"""
from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    path("", views.index, name="index"),
    path("list/", views.record_list, name="list"),
    path("edit/<int:pk>/", views.edit, name="edit"),
    path("delete/<int:pk>/", views.delete, name="delete"),
    path("company/", views.company_report, name="company"),
]
