from django.contrib import admin
from django.urls import path, include


urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path('finances/', include('finances.urls')),
    path("social/", include("allauth.urls")),
    path("", include("scheduler.urls")),
]
