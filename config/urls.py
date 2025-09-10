from django.contrib import admin
from django.urls import path, include


urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("core/", include("core.urls")),
    path('finances/', include('finances.urls')),
    path('leads/', include('leads.urls')),
    path('logs/', include('logs.urls')),
    path("social/", include("allauth.urls")),
    path("store/", include("store.urls")),
    path("", include("scheduler.urls")),
]
