"""
Public API URLs: auth, site, games, bonus. No auth required for read endpoints.
"""
from django.urls import path
from core.views.public import auth_views, site_views, game_views, bonus_views, promotion_views, password_reset_views, signup_views

urlpatterns = [
    # Auth
    path('auth/login/', auth_views.login),
    path('auth/register/', auth_views.register),
    path('auth/me/', auth_views.me),
    path('auth/google/', auth_views.google_login),
    path('auth/google/complete/', auth_views.google_complete),
    # Signup (phone + OTP)
    path('auth/signup/check-phone/', signup_views.signup_check_phone),
    path('auth/signup/send-otp/', signup_views.signup_send_otp),
    path('auth/signup/verify-otp/', signup_views.signup_verify_otp),
    # Forgot password (unauthenticated)
    path('auth/forgot-password/search/', password_reset_views.forgot_password_search),
    path('auth/forgot-password/send-otp/', password_reset_views.forgot_password_send_otp),
    path('auth/forgot-password/verify-reset/', password_reset_views.forgot_password_verify_reset),
    path('auth/forgot-password/whatsapp-contact/', password_reset_views.forgot_password_whatsapp_contact),
    # Site
    path('site-setting/', site_views.site_setting),
    path('countries/', site_views.countries_list),
    path('payment-methods/', site_views.payment_methods_list),
    path('slider/', site_views.slider_list),
    path('popups/', site_views.popup_list),
    path('live-betting/', site_views.live_betting_list),
    path('second-home-sections/', site_views.second_home_sections),
    path('cms/footer/', site_views.cms_pages_footer),
    path('cms/<slug:slug>/', site_views.cms_page_by_slug),
    path('testimonials/', site_views.testimonials_list),
    # Games
    path('categories/', game_views.category_list),
    path('providers/', game_views.provider_list),
    path('providers/<int:pk>/', game_views.provider_detail),
    path('games/', game_views.game_list),
    path('coming-soon-games/', game_views.coming_soon_list),
    path('coming-soon-enroll/', game_views.coming_soon_enroll),
    path('games/<int:pk>/', game_views.game_detail),
    # Bonus
    path('bonus-rules/', bonus_views.bonus_rules_list),
    # Promotions
    path('promotions/', promotion_views.promotion_list),
]
