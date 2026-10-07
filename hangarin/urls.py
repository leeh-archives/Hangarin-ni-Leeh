"""
URL configuration for hangarin project.
"""

from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", lambda request: redirect("task_list")),
    path("", include("taskmanager.urls")),
]