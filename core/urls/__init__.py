from django.urls import path, include
from core.views import callback_views

urlpatterns = [
    path('callback/', callback_views.game_callback),
    path('callback', callback_views.game_callback),
    path('public/', include('core.urls.public_urls')),
    path('powerhouse/', include('core.urls.powerhouse_urls')),
    path('super/', include('core.urls.super_urls')),
    path('master/', include('core.urls.master_urls')),
    path('player/', include('core.urls.player_urls')),
]
