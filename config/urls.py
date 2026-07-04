"""プロジェクト全体の URL 設定。"""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from reports.views import register

urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", auth_views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(next_page="/login/"), name="logout"),
    path("register/", register, name="register"),
    path("", include("reports.urls")),
    path("expenses/", include("expenses.urls")),
]
