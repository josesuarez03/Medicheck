from django.contrib import admin
from django.urls import path, include
from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from django.utils import timezone


def health_view(_request):
    checks = {}
    status_code = 200

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error:{exc}"
        status_code = 503

    try:
        cache_key = "healthcheck"
        cache.set(cache_key, "ok", timeout=5)
        checks["redis"] = "ok" if cache.get(cache_key) == "ok" else "error:cache_miss"
        if checks["redis"] != "ok":
            status_code = 503
    except Exception as exc:
        checks["redis"] = f"error:{exc}"
        status_code = 503
    return JsonResponse(
        {
            "status": "ok" if status_code == 200 else "degraded",
            "checks": checks,
            "timestamp": timezone.now().isoformat(),
        },
        status=status_code,
    )

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', health_view, name='health'),
    path('', include('users.urls')),
]
