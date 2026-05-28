from django.urls import path, include
from .views import delete_temp_file_view, upload_file_view

urlpatterns = [
    path('upload/', upload_file_view, name='upload_file'),
    path('delete_temp_file/', delete_temp_file_view, name='delete_temp_file'),
    path('api/', include('upload_file_plugin.api.urls')),
]
