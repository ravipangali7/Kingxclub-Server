from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model

from .models import (
    Country,
    SuperSetting,
    User,
    PaymentMode,
    Deposit,
    Withdraw,
    BonusRule,
    GameProvider,
    GameCategory,
    Game,
    GameLog,
    Transaction,
    ActivityLog,
    Message,
    Testimonial,
    CMSPage,
    SiteSetting,
    SliderSlide,
    Popup,
    Promotion,
    LiveBettingSection,
    LiveBettingEvent,
    SignupOTP,
    SignupSession,
    PaymentMethod,
)

UserModel = get_user_model()

# Unregister default User admin (auth registers AUTH_USER_MODEL) so we can use CustomUserAdmin
try:
    admin.site.unregister(UserModel)
except admin.sites.NotRegistered:
    pass


# --- Inline ---

class PaymentModeInline(admin.TabularInline):
    model = PaymentMode
    fk_name = 'user'
    extra = 0
    fields = ('payment_method', 'details', 'qr_image', 'status')


# --- User Admin (replace default) ---

@admin.register(UserModel)
class CustomUserAdmin(BaseUserAdmin):
    list_display = (
        'username',
        'name',
        'email',
        'phone',
        'role',
        'main_balance',
        'pl_balance',
        'bonus_balance',
        'exposure_balance',
        'exposure_limit',
        'is_active',
        'parent',
        'created_at',
    )
    list_filter = ('role', 'is_active')
    search_fields = ('username', 'name', 'phone', 'email')
    ordering = ('-created_at',)
    filter_horizontal = ()
    inlines = (PaymentModeInline,)

    # Define fieldsets from scratch: User model has first_name/last_name = None and uses 'name'
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Profile', {'fields': ('name', 'email', 'phone', 'whatsapp_number')}),
        ('Role & Hierarchy', {'fields': ('role', 'parent', 'referred_by', 'commission_percentage')}),
        ('Security', {'fields': ('pin',)}),
        (
            'Balances',
            {
                'fields': (
                    'main_balance',
                    'pl_balance',
                    'bonus_balance',
                    'exposure_balance',
                    'exposure_limit',
                ),
            },
        ),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )
    readonly_fields = ('created_at', 'updated_at')
    add_fieldsets = (
        (None, {'fields': ('username', 'password1', 'password2')}),
        ('Profile', {'fields': ('name', 'email', 'phone', 'whatsapp_number')}),
        ('Role & Hierarchy', {'fields': ('role', 'parent', 'referred_by', 'commission_percentage')}),
        ('Security', {'fields': ('pin',)}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
    )


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ("name", "country_code", "currency_symbol", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "country_code")
    ordering = ("name",)


# --- Singleton-style: only one instance ---

class SingletonAdminMixin:
    def has_add_permission(self, request):
        return not self.model.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SuperSetting)
class SuperSettingAdmin(SingletonAdminMixin, admin.ModelAdmin):
    list_display = (
        'id',
        'ggr_coin',
        'min_withdraw',
        'max_withdraw',
        'min_deposit',
        'max_deposit',
        'exposure_limit',
        'default_master',
        'updated_at',
    )
    readonly_fields = ('created_at', 'updated_at')
    autocomplete_fields = ('default_master',)


@admin.register(SignupOTP)
class SignupOTPAdmin(admin.ModelAdmin):
    list_display = ('phone', 'otp', 'expires_at', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('phone',)
    readonly_fields = ('phone', 'otp', 'expires_at', 'created_at')


@admin.register(SignupSession)
class SignupSessionAdmin(admin.ModelAdmin):
    list_display = ('phone', 'token', 'expires_at', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('phone', 'token')
    readonly_fields = ('phone', 'token', 'expires_at', 'created_at')


@admin.register(PaymentMode)
class PaymentModeAdmin(admin.ModelAdmin):
    list_display = ('user', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('name', 'user__username')
    autocomplete_fields = ('user',)


@admin.register(Deposit)
class DepositAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'amount',
        'status',
        'payment_mode',
        'processed_by',
        'processed_at',
        'created_at',
    )
    list_filter = ('status',)
    search_fields = ('user__username',)
    autocomplete_fields = ('user', 'payment_mode', 'processed_by')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Withdraw)
class WithdrawAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'amount',
        'status',
        'payment_mode',
        'processed_by',
        'processed_at',
        'created_at',
    )
    list_filter = ('status',)
    search_fields = ('user__username',)
    autocomplete_fields = ('user', 'payment_mode', 'processed_by')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(BonusRule)
class BonusRuleAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'bonus_type',
        'reward_type',
        'reward_amount',
        'roll_required',
        'is_active',
        'valid_from',
        'valid_until',
        'created_at',
    )
    list_filter = ('bonus_type', 'reward_type', 'is_active')
    search_fields = ('name', 'promo_code')


@admin.register(GameProvider)
class GameProviderAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'code')
    fields = ('name', 'code', 'api_endpoint', 'api_secret', 'api_token', 'is_active')


@admin.register(GameCategory)
class GameCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name',)


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'provider',
        'category',
        'game_uid',
        'min_bet',
        'max_bet',
        'is_active',
        'is_coming_soon',
        'coming_soon_launch_date',
        'created_at',
    )
    list_filter = ('is_active', 'is_coming_soon', 'provider', 'category')
    search_fields = ('name', 'game_uid')
    autocomplete_fields = ('provider', 'category')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {'fields': ('name', 'provider', 'category', 'game_uid')}),
        ('Media', {'fields': ('image', 'image_url')}),
        ('Bet limits', {'fields': ('min_bet', 'max_bet')}),
        ('Status', {'fields': ('is_active',)}),
        (
            'Coming soon',
            {
                'fields': ('is_coming_soon', 'coming_soon_launch_date', 'coming_soon_description'),
                'description': 'Mark as coming soon and set optional launch date and description for the card.',
            },
        ),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


@admin.register(GameLog)
class GameLogAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'game',
        'provider',
        'wallet',
        'type',
        'bet_amount',
        'win_amount',
        'lose_amount',
        'before_balance',
        'after_balance',
        'created_at',
    )
    list_filter = ('wallet', 'type')
    search_fields = ('user__username', 'game__name', 'round', 'match')
    autocomplete_fields = ('user', 'game', 'provider')
    readonly_fields = ('created_at', 'updated_at', 'provider_raw_data')
    date_hierarchy = 'created_at'


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'action_type',
        'wallet',
        'transaction_type',
        'amount',
        'status',
        'from_user',
        'to_user',
        'balance_before',
        'balance_after',
        'created_at',
    )
    list_filter = ('action_type', 'wallet', 'transaction_type', 'status')
    search_fields = ('user__username', 'remarks')
    autocomplete_fields = ('user', 'from_user', 'to_user')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'ip',
        'device',
        'action',
        'action_date',
        'action_time',
        'created_at',
    )
    list_filter = ('action',)
    search_fields = ('user__username', 'ip', 'remarks')
    autocomplete_fields = ('user', 'game')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'sender', 'receiver', 'message_preview', 'created_at')
    list_filter = ()
    search_fields = ('message', 'sender__username', 'receiver__username')
    autocomplete_fields = ('sender', 'receiver')
    readonly_fields = ('created_at', 'updated_at')

    def message_preview(self, obj):
        if not obj.message:
            return '-'
        text = obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
        return text

    message_preview.short_description = 'Message'


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ('name', 'testimonial_from', 'stars', 'game_name', 'created_at')
    list_filter = ('stars',)
    search_fields = ('name', 'message', 'game_name')


@admin.register(CMSPage)
class CMSPageAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'is_active', 'is_header', 'is_footer', 'updated_at')
    list_filter = ('is_active', 'is_header', 'is_footer')
    search_fields = ('title', 'content')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('created_at', 'updated_at')


@admin.register(SiteSetting)
class SiteSettingAdmin(SingletonAdminMixin, admin.ModelAdmin):
    list_display = (
        'id',
        'name',
        'hero_title',
        'active_players',
        'games_available',
        'updated_at',
    )
    readonly_fields = ('created_at', 'updated_at')


@admin.register(SliderSlide)
class SliderSlideAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'order', 'updated_at')
    list_editable = ('order',)
    ordering = ('order', 'id')


@admin.register(Popup)
class PopupAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'is_active', 'order', 'updated_at')
    list_editable = ('is_active', 'order')
    ordering = ('order', 'id')


@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'is_active', 'order', 'updated_at')
    list_editable = ('is_active', 'order')
    list_filter = ('is_active',)
    ordering = ('order', 'id')
    readonly_fields = ('created_at', 'updated_at')


class LiveBettingEventInline(admin.TabularInline):
    model = LiveBettingEvent
    extra = 0
    ordering = ('order', 'id')


@admin.register(LiveBettingSection)
class LiveBettingSectionAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'order', 'updated_at')
    list_editable = ('order',)
    ordering = ('order', 'id')
    inlines = (LiveBettingEventInline,)


@admin.register(LiveBettingEvent)
class LiveBettingEventAdmin(admin.ModelAdmin):
    list_display = ('id', 'section', 'team1', 'team2', 'event_date', 'event_time', 'is_live', 'order')
    list_filter = ('section', 'is_live')
    ordering = ('section', 'order', 'id')


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'is_active', 'order', 'updated_at')
    list_editable = ('is_active', 'order')
    ordering = ('order', 'id')
    readonly_fields = ('created_at', 'updated_at')
