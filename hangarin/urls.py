from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect
from django.urls import include, path


def home(request):
    if request.user.is_authenticated:
        return redirect("task_list")
    return redirect("login")


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("pwa.urls")),
    path("", home, name="home"),
    path("", include("taskmanager.urls")),

    # our own login route first so signed-in people skip the form
    path(
        "accounts/login/",
        auth_views.LoginView.as_view(redirect_authenticated_user=True),
        name="login",
    ),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),

    # allauth handles the Google / GitHub round trip
    # (callbacks live at /accounts/google/login/callback/ and .../github/...)
    path("accounts/", include("allauth.urls")),
]

# Only used by the dev server. On PythonAnywhere /media/ is a static mapping.
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
