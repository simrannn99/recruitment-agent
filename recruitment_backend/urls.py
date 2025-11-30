"""
URL configuration for recruitment_backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from recruitment.views import search_views, websocket_views

urlpatterns = [
    path("admin/", admin.site.urls),
    
    # Prometheus Metrics (exposed at /metrics by django_prometheus)
    path("", include("django_prometheus.urls")),
    
    # WebSocket Test Page
    path("ws-test/", websocket_views.websocket_test, name="websocket_test"),
    
    # Vector Search API Endpoints
    path("api/search/candidates/", search_views.search_candidates_for_job, name="search_candidates"),
    path("api/search/jobs/", search_views.search_jobs_for_candidate, name="search_jobs"),
    path("api/search/similar-candidates/", search_views.search_similar_candidates, name="search_similar_candidates"),
]

# Serve media and static files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)


