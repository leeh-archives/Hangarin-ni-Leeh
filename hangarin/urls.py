from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),

    # ours goes before django-pwa so our own /offline/ page is the one that shows
    path("", include("taskmanager.urls")),
    path("", include("pwa.urls")),

    # login, sign up, logout and the Google / GitHub round trip all come from allauth
    # (callbacks live at /accounts/google/login/callback/ and .../github/...)
    path("accounts/", include("allauth.urls")),
]

# Only used by the dev server. On PythonAnywhere /media/ is a static mapping.
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
