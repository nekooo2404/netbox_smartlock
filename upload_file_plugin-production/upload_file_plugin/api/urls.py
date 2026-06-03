from django.urls import path
from .views import GetFileFromDBAPIView

urlpatterns = [
    path('get_data_from_database/', GetFileFromDBAPIView.as_view(), name='get_data_from_database'),
]
