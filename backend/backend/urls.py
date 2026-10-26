from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from blaknot_app.views import healthz

urlpatterns = [
    path(f"{settings.ADMIN_URL}/", admin.site.urls),
    path("api/", include("blaknot_app.urls")),
    path("healthz/", healthz),
]

if settings.DEBUG:
    # Только для разработки. В проде /media/ отдаёт nginx.
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
