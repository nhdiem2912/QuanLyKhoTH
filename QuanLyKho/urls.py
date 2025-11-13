from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),

    # Tất cả route của app QuanLy
    path('', include('QuanLy.urls')),
]
