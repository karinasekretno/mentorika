from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

from landing.views import index

urlpatterns = [
    path('', index, name='index'),
    path('', include('accounts.urls')),
    path('admin/', admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
