"""
Destructive bulk cleanup for Powerhouse. Deletes rows per selected model keys in FK-safe order.
Never deletes Game, GameCategory, GameProvider (defense in depth — strip from request).
SuperSetting / SiteSetting: delete all rows then recreate one row with model field defaults.
"""
import logging
from decimal import Decimal

from django.db import transaction

from core.models import (
    ActivityLog,
    BonusRequest,
    BonusRule,
    CMSPage,
    ComingSoon,
    ComingSoonEnrollment,
    Country,
    Deposit,
    Game,
    GameCategory,
    GameLog,
    GameProvider,
    LiveBettingEvent,
    LiveBettingSection,
    Message,
    PasswordResetOTP,
    PaymentMethod,
    PaymentMode,
    Popup,
    Promotion,
    SignupOTP,
    SignupSession,
    SiteSetting,
    SliderSlide,
    SuperSetting,
    Testimonial,
    Transaction,
    User,
    UserRole,
    Withdraw,
)

logger = logging.getLogger(__name__)

PROTECTED_KEYS = frozenset({"game", "gamecategory", "gameprovider"})

# Human labels for API / UI (includes protected rows for display)
MODEL_LABELS = {
    "password_reset_otp": "Password reset OTP",
    "signup_otp": "Signup OTP",
    "signup_session": "Signup session",
    "message": "Messages",
    "transaction": "Transactions",
    "game_log": "Bet history (game logs)",
    "deposit": "Deposits",
    "withdraw": "Withdrawals",
    "bonus_request": "Bonus requests",
    "payment_mode": "Payment modes",
    "coming_soon_enrollment": "Coming soon enrollments",
    "activity_log": "Activity logs",
    "bonus_rule": "Bonus rules",
    "live_betting_event": "Live betting events",
    "live_betting_section": "Live betting sections",
    "slider_slide": "Slider slides",
    "popup": "Popups",
    "promotion": "Promotions",
    "cms_page": "CMS pages",
    "testimonial": "Testimonials",
    "payment_method": "Payment methods (templates)",
    "country": "Countries",
    "coming_soon": "Coming soon",
    "super_setting": "Super settings (reset to defaults)",
    "site_setting": "Site settings (reset to defaults)",
    "user": "Users (except all Powerhouse accounts)",
    "game": "Games",
    "gamecategory": "Game categories",
    "gameprovider": "Game providers",
}

CLEANABLE_KEYS = tuple(k for k in MODEL_LABELS if k not in PROTECTED_KEYS)

# Presets: which model keys to turn on (table-based)
PRESETS = {
    "user": frozenset(
        {
            "deposit",
            "withdraw",
            "transaction",
            "game_log",
            "bonus_request",
            "coming_soon_enrollment",
        }
    ),
    "master": frozenset(
        {
            "deposit",
            "withdraw",
            "transaction",
            "game_log",
            "bonus_request",
            "coming_soon_enrollment",
            "activity_log",
            "message",
            "payment_mode",
        }
    ),
    "super": frozenset(
        {
            "deposit",
            "withdraw",
            "transaction",
            "game_log",
            "bonus_request",
            "coming_soon_enrollment",
            "activity_log",
            "message",
            "payment_mode",
            "bonus_rule",
            "coming_soon",
            "password_reset_otp",
            "signup_otp",
            "signup_session",
            "user",
        }
    ),
    "powerhouse": frozenset(k for k in MODEL_LABELS if k not in PROTECTED_KEYS),
}


def get_metadata():
    """Return model list and preset definitions for GET /clean-data/."""
    models_out = []
    for key in MODEL_LABELS:
        models_out.append(
            {
                "id": key,
                "label": MODEL_LABELS[key],
                "protected": key in PROTECTED_KEYS,
                "presets": {p: key in PRESETS[p] for p in PRESETS},
            }
        )
    return {"models": models_out, "preset_ids": list(PRESETS.keys())}


def _reset_super_setting():
    SuperSetting.objects.all().delete()
    SuperSetting.objects.create(
        ggr_coin=Decimal("0.00"),
        game_api_url="",
        game_api_secret="",
        game_api_token="",
        game_api_callback_url="",
        game_api_domain_url="",
        game_api_launch_url="",
        min_withdraw=Decimal("0.00"),
        min_deposit=Decimal("0.00"),
        max_withdraw=Decimal("0.00"),
        max_deposit=Decimal("0.00"),
        exposure_limit=Decimal("0.00"),
        sms_api_token="",
        default_master=None,
    )


def _reset_site_setting():
    SiteSetting.objects.all().delete()
    SiteSetting.objects.create()


# FK-safe order
_ORDERED_KEYS = [
    "password_reset_otp",
    "signup_otp",
    "signup_session",
    "message",
    "transaction",
    "game_log",
    "deposit",
    "withdraw",
    "bonus_request",
    "payment_mode",
    "coming_soon_enrollment",
    "activity_log",
    "bonus_rule",
    "live_betting_event",
    "live_betting_section",
    "slider_slide",
    "popup",
    "promotion",
    "cms_page",
    "testimonial",
    "payment_method",
    "country",
    "coming_soon",
    "super_setting",
    "site_setting",
    "user",
]


@transaction.atomic
def execute_clean_data(selected_keys: list[str], acting_user: User) -> dict:
    """
    Run deletions in order. `selected_keys` are model ids from MODEL_LABELS (excluding protected).
    Returns {"deleted": {key: count}}.
    """
    _ = (acting_user, Game, GameCategory, GameProvider)  # reserved; catalog never deleted here

    allowed = set(MODEL_LABELS.keys()) - PROTECTED_KEYS
    keys_set = {k for k in selected_keys if isinstance(k, str)} & allowed

    if not keys_set:
        return {"deleted": {}, "detail": "No valid models selected."}

    deleted: dict[str, int] = {}

    for key in _ORDERED_KEYS:
        if key not in keys_set:
            continue

        if key == "password_reset_otp":
            n, _ = PasswordResetOTP.objects.all().delete()
        elif key == "signup_otp":
            n, _ = SignupOTP.objects.all().delete()
        elif key == "signup_session":
            n, _ = SignupSession.objects.all().delete()
        elif key == "message":
            n, _ = Message.objects.all().delete()
        elif key == "transaction":
            n, _ = Transaction.objects.all().delete()
        elif key == "game_log":
            n, _ = GameLog.objects.all().delete()
        elif key == "deposit":
            n, _ = Deposit.objects.all().delete()
        elif key == "withdraw":
            n, _ = Withdraw.objects.all().delete()
        elif key == "bonus_request":
            n, _ = BonusRequest.objects.all().delete()
        elif key == "payment_mode":
            n, _ = PaymentMode.objects.all().delete()
        elif key == "coming_soon_enrollment":
            n, _ = ComingSoonEnrollment.objects.all().delete()
        elif key == "activity_log":
            n, _ = ActivityLog.objects.all().delete()
        elif key == "bonus_rule":
            n, _ = BonusRule.objects.all().delete()
        elif key == "live_betting_event":
            n, _ = LiveBettingEvent.objects.all().delete()
        elif key == "live_betting_section":
            n, _ = LiveBettingSection.objects.all().delete()
        elif key == "slider_slide":
            n, _ = SliderSlide.objects.all().delete()
        elif key == "popup":
            n, _ = Popup.objects.all().delete()
        elif key == "promotion":
            n, _ = Promotion.objects.all().delete()
        elif key == "cms_page":
            n, _ = CMSPage.objects.all().delete()
        elif key == "testimonial":
            n, _ = Testimonial.objects.all().delete()
        elif key == "payment_method":
            n, _ = PaymentMethod.objects.all().delete()
        elif key == "country":
            n, _ = Country.objects.all().delete()
        elif key == "coming_soon":
            n, _ = ComingSoon.objects.all().delete()
        elif key == "super_setting":
            n = SuperSetting.objects.count()
            _reset_super_setting()
        elif key == "site_setting":
            n = SiteSetting.objects.count()
            _reset_site_setting()
        elif key == "user":
            n, _ = User.objects.exclude(role=UserRole.POWERHOUSE).delete()
        else:
            continue

        deleted[key] = n

    logger.info(
        "clean_data executed by user_id=%s keys=%s deleted=%s",
        acting_user.pk,
        sorted(keys_set),
        deleted,
    )
    return {"deleted": deleted}
