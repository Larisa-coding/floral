from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from products.views import home
from users import views as users_views
from orders import views as orders_views

urlpatterns = [
    path('admin/', admin.site.urls),          # Панель администратора
    path('', home, name='home'),              # Главная страница
    path('products/', include('products.urls')), # Каталог
    path('orders/', include('orders.urls')),     # Заказы
    path('users/', include('users.urls')),       # Пользователи
    path('profile/connect-telegram/', users_views.connect_telegram, name='connect_telegram'),
    path('profile/disconnect-telegram/', users_views.disconnect_telegram, name='disconnect_telegram'),
    path('admin/orders/<int:order_id>/send-notification/', orders_views.send_telegram_notification, name='send_telegram_notification'),
]

# Для работы с медиафайлами в режиме разработки
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)