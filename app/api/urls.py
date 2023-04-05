from django.urls import include, re_path
from django.http import HttpResponse
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from rest_framework_nested import routers
from api.api import DataProjectViewSet, HostedFileViewSet

router = routers.SimpleRouter()
router.register(r'projects', DataProjectViewSet)

projects_router = routers.NestedSimpleRouter(router, r'projects', lookup='project')
projects_router.register(r'files', HostedFileViewSet, basename='project-files')

app_name = 'api'
urlpatterns = [
    re_path(r'^schema/?$', SpectacularAPIView.as_view(), name='schema'),
    re_path(r'^schema/redoc/', SpectacularRedocView.as_view(url_name='api:schema'), name='redoc'),
    re_path(r'^schema/swagger/?$', SpectacularSwaggerView.as_view(url_name='api:schema'), name='swagger'),
    re_path(r'^v1/', include(router.urls)),
    re_path(r'^v1/', include(projects_router.urls)),
    re_path(r'^', lambda request: HttpResponse(status=404)),
]
