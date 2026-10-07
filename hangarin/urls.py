from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("pwa.urls")),
    path("", lambda request: redirect("task_list")),
    path("", include("taskmanager.urls")),
]