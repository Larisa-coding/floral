from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from products.views import home

urlpatterns = [
    path('admin/', admin.site.urls),          # Панель администратора
    path('', home, name='home'),              # Главная страница
    path('products/', include('products.urls')), # Каталог
    path('orders/', include('orders.urls')),     # Заказы
    path('users/', include('users.urls')),       # Пользователи
]

# Для работы с медиафайлами в режиме разработки
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
