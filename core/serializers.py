"""
DRF serializers for core models.
"""
import json
from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import (
    Country,
    User,
    UserRole,
    SuperSetting,
    SiteSetting,
    SliderSlide,
    Popup,
    Promotion,
    LiveBettingSection,
    LiveBettingEvent,
    PaymentMode,
    Deposit,
    Withdraw,
    WithdrawWallet,
    BonusRequest,
    BonusRule,
    GameProvider,
    GameCategory,
    Game,
    ComingSoonEnrollment,
    GameLog,
    Transaction,
    ActivityLog,
    Message,
    Testimonial,
    CMSPage,
    PaymentMethod,
)
from .services.withdraw_eligibility import get_withdraw_eligibility


# --- Auth ---
VALID_COUNTRY_CODES = ('977', '91')


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    country_code = serializers.CharField(required=False, allow_blank=True)

    def validate_country_code(self, value):
        v = (value or '').strip()
        if v and v not in VALID_COUNTRY_CODES:
            raise serializers.ValidationError('Country code must be 977 or 91.')
        return v


class RegisterSerializer(serializers.Serializer):
    """Phone-first signup: requires signup_token (from verify-otp), phone, name, password."""
    signup_token = serializers.CharField()
    phone = serializers.CharField()
    name = serializers.CharField()
    password = serializers.CharField(write_only=True, min_length=6)
    referral_code = serializers.CharField(required=False, allow_blank=True)
    country_code = serializers.CharField(required=False, allow_blank=True)

    def validate_country_code(self, value):
        v = (value or '').strip()
        if v and v not in VALID_COUNTRY_CODES:
            raise serializers.ValidationError('Country code must be 977 or 91.')
        return v


# --- User ---
class UserMinimalSerializer(serializers.ModelSerializer):
    """For list views and nested relations."""
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'name', 'role', 'role_display',
            'main_balance', 'pl_balance', 'bonus_balance', 'exposure_balance', 'exposure_limit',
            'is_active', 'created_at',
            'phone', 'whatsapp_number', 'commission_percentage', 'parent',
        ]
        read_only_fields = fields


class ReferralSerializer(serializers.ModelSerializer):
    """Safe fields for referred-user list/detail (no balance, phone, etc.)."""

    class Meta:
        model = User
        fields = ['id', 'username', 'name', 'created_at']
        read_only_fields = fields


class UserListSerializer(serializers.ModelSerializer):
    """List with aggregated balances for super/master (masters_balance, users_balance, etc.)."""
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    parent_username = serializers.SerializerMethodField()
    no_activity_7_days = serializers.SerializerMethodField()
    masters_balance = serializers.SerializerMethodField()
    masters_pl_balance = serializers.SerializerMethodField()
    users_balance = serializers.SerializerMethodField()
    players_count = serializers.SerializerMethodField()
    masters_count = serializers.SerializerMethodField()
    total_balance = serializers.SerializerMethodField()
    total_win_loss = serializers.SerializerMethodField()
    total_bet = serializers.SerializerMethodField()
    is_default_master = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'name', 'role', 'role_display', 'parent_username', 'no_activity_7_days',
            'phone', 'whatsapp_number',
            'main_balance', 'pl_balance', 'bonus_balance', 'exposure_balance', 'exposure_limit',
            'is_active', 'created_at', 'pin',
            'masters_balance', 'masters_pl_balance', 'users_balance',
            'players_count', 'masters_count',
            'total_balance', 'total_win_loss', 'total_bet',
            'is_default_master',
        ]

    def get_no_activity_7_days(self, obj):
        if obj.role != UserRole.PLAYER:
            return False
        from django.utils import timezone
        from datetime import timedelta
        cutoff = timezone.now() - timedelta(days=7)
        last_login = getattr(obj, 'last_login', None)
        last_gl = getattr(obj, '_last_gl', None)
        last_dep = getattr(obj, '_last_dep', None)
        last_wd = getattr(obj, '_last_wd', None)
        dates = [x for x in [last_login, last_gl, last_dep, last_wd] if x is not None]
        if not dates:
            return True
        return max(dates) < cutoff

    def get_parent_username(self, obj):
        if obj.role == UserRole.PLAYER and obj.parent_id:
            return obj.parent.username if obj.parent else None
        return None

    def get_masters_balance(self, obj):
        if obj.role == UserRole.SUPER:
            return sum(c.main_balance for c in obj.children.filter(role=UserRole.MASTER))
        return None

    def get_masters_pl_balance(self, obj):
        if obj.role == UserRole.SUPER:
            return sum(c.pl_balance for c in obj.children.filter(role=UserRole.MASTER))
        return None

    def get_users_balance(self, obj):
        if obj.role == UserRole.MASTER:
            return sum(
                (u.main_balance or 0) for u in obj.children.filter(role=UserRole.PLAYER)
            )
        if obj.role == UserRole.SUPER:
            total = sum((m.main_balance or 0) for m in obj.children.filter(role=UserRole.MASTER))
            for m in obj.children.filter(role=UserRole.MASTER):
                total += sum((p.main_balance or 0) for p in m.children.filter(role=UserRole.PLAYER))
            return total
        return None

    def get_players_count(self, obj):
        if obj.role == UserRole.MASTER:
            return obj.children.filter(role=UserRole.PLAYER).count()
        if obj.role == UserRole.SUPER:
            return User.objects.filter(parent__parent=obj, role=UserRole.PLAYER).count()
        return None

    def get_masters_count(self, obj):
        if obj.role == UserRole.SUPER:
            return obj.children.filter(role=UserRole.MASTER).count()
        return None

    def get_total_balance(self, obj):
        """For players: main + bonus + exposure."""
        if obj.role != UserRole.PLAYER:
            return None
        return (obj.main_balance or 0) + (obj.bonus_balance or 0) + (obj.exposure_balance or 0)

    def get_total_win_loss(self, obj):
        """For players: from annotated _win_sum - _lose_sum (see view annotate)."""
        if obj.role != UserRole.PLAYER:
            return None
        win = getattr(obj, '_win_sum', None)
        lose = getattr(obj, '_lose_sum', None)
        if win is None and lose is None:
            return None
        return (win or 0) - (lose or 0)

    def get_total_bet(self, obj):
        """For players: from annotated _bet_sum (Sum of game_logs bet_amount)."""
        if obj.role != UserRole.PLAYER:
            return None
        return getattr(obj, '_bet_sum', None)

    def get_is_default_master(self, obj):
        """True when this user is the default master in SuperSetting."""
        if obj.role != UserRole.MASTER:
            return False
        settings = SuperSetting.get_settings()
        return settings is not None and settings.default_master_id == obj.id


class UserDetailSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'name', 'email', 'phone', 'whatsapp_number',
            'role', 'role_display', 'commission_percentage', 'parent', 'referred_by',
            'main_balance', 'pl_balance', 'bonus_balance', 'exposure_balance', 'exposure_limit',
            'is_active',
            'created_at', 'updated_at', 'pin',
        ]
        read_only_fields = ['main_balance', 'pl_balance', 'bonus_balance', 'exposure_balance']


class UserCreateUpdateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, min_length=6)
    main_balance = serializers.DecimalField(max_digits=16, decimal_places=2, required=False, min_value=0)
    bonus_balance = serializers.DecimalField(max_digits=16, decimal_places=2, required=False, min_value=0)
    exposure_balance = serializers.DecimalField(max_digits=16, decimal_places=2, required=False, min_value=0)
    exposure_limit = serializers.DecimalField(max_digits=16, decimal_places=2, required=False, min_value=0)

    class Meta:
        model = User
        fields = [
            'username', 'password', 'name', 'email', 'phone', 'whatsapp_number',
            'commission_percentage', 'parent', 'role',
            'main_balance', 'bonus_balance', 'exposure_balance', 'exposure_limit',
        ]

    def create(self, validated_data):
        for key in ('main_balance', 'bonus_balance', 'exposure_balance', 'exposure_limit'):
            validated_data.pop(key, None)
        password = validated_data.pop('password', None)
        if password:
            user = User(**validated_data)
            user.set_password(password)
            user.save()
            return user
        return User.objects.create_user(**validated_data)

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        if password:
            instance.set_password(password)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


# --- Me / Balances (for header) ---
class MeSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    # Header balances by role (computed or same fields)
    main_balance = serializers.DecimalField(max_digits=16, decimal_places=2, read_only=True)
    super_balance = serializers.SerializerMethodField()
    master_balance = serializers.SerializerMethodField()
    player_balance = serializers.SerializerMethodField()
    total_balance = serializers.SerializerMethodField()
    currency_symbol = serializers.SerializerMethodField()
    parent_whatsapp_number = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'name', 'role', 'role_display',
            'main_balance', 'bonus_balance', 'pl_balance', 'exposure_balance', 'exposure_limit',
            'super_balance', 'master_balance', 'player_balance', 'total_balance',
            'parent', 'whatsapp_number', 'parent_whatsapp_number', 'country_code', 'currency_symbol',
            'last_login',
        ]

    def get_parent_whatsapp_number(self, obj):
        """For players: parent (master) whatsapp_number; for others None."""
        if obj.role != UserRole.PLAYER or not obj.parent_id:
            return None
        parent = obj.parent
        if not parent:
            return None
        return (parent.whatsapp_number or '').strip() or None

    def get_currency_symbol(self, obj):
        code = (obj.country_code or '').strip()
        if not code:
            return '₹'
        sym = Country.objects.filter(country_code=code, is_active=True).values_list('currency_symbol', flat=True).first()
        return sym or '₹'

    def get_super_balance(self, obj):
        if obj.role == UserRole.POWERHOUSE:
            return sum(c.main_balance for c in User.objects.filter(role=UserRole.SUPER, parent=obj))
        return None

    def get_master_balance(self, obj):
        if obj.role == UserRole.POWERHOUSE:
            return sum(c.main_balance for c in User.objects.filter(role=UserRole.MASTER))
        if obj.role == UserRole.SUPER:
            return sum(c.main_balance for c in obj.children.filter(role=UserRole.MASTER))
        return None

    def get_player_balance(self, obj):
        if obj.role == UserRole.POWERHOUSE:
            return sum(c.main_balance for c in User.objects.filter(role=UserRole.PLAYER))
        if obj.role in (UserRole.SUPER, UserRole.MASTER):
            qs = User.objects.filter(role=UserRole.PLAYER)
            if obj.role == UserRole.MASTER:
                qs = qs.filter(parent=obj)
            else:
                qs = qs.filter(parent__parent=obj)
            return sum(c.main_balance for c in qs)
        return None

    def get_total_balance(self, obj):
        if obj.role == UserRole.PLAYER:
            return (obj.main_balance or 0) + (obj.bonus_balance or 0)
        main = obj.main_balance or 0
        sb = self.get_super_balance(obj) or 0
        mb = self.get_master_balance(obj) or 0
        pb = self.get_player_balance(obj) or 0
        return main + sb + mb + pb


# --- SuperSetting ---
class SuperSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SuperSetting
        fields = '__all__'


# --- Country (powerhouse CRUD) ---
class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ['id', 'name', 'country_code', 'currency_symbol', 'is_active', 'created_at', 'updated_at']


# --- PaymentMethod ---
class PaymentMethodSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = PaymentMethod
        fields = ['id', 'name', 'image', 'image_url', 'fields', 'order', 'is_active', 'created_at', 'updated_at']

    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


# --- SiteSetting ---
class SiteSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteSetting
        fields = '__all__'


# --- SliderSlide ---
class SliderSlideSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = SliderSlide
        fields = [
            'id', 'title', 'subtitle', 'image', 'image_file',
            'cta_label', 'cta_link', 'order', 'created_at', 'updated_at',
        ]

    def get_image(self, obj):
        if obj.image_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image_file.url)
            return obj.image_file.url
        return (obj.image or '').strip() or None


# --- Popup ---
class PopupSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Popup
        fields = [
            'id', 'title', 'content', 'image', 'image_file',
            'cta_label', 'cta_link', 'is_active', 'order', 'created_at', 'updated_at',
        ]

    def get_image(self, obj):
        if obj.image_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image_file.url)
            return obj.image_file.url
        return (obj.image or '').strip() or None


# --- Promotion ---
class PromotionSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Promotion
        fields = ['id', 'title', 'image', 'image_url', 'description', 'is_active', 'order', 'created_at', 'updated_at']

    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


# --- LiveBetting ---
class LiveBettingEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = LiveBettingEvent
        fields = '__all__'


class LiveBettingSectionSerializer(serializers.ModelSerializer):
    events = LiveBettingEventSerializer(many=True, read_only=True)

    class Meta:
        model = LiveBettingSection
        fields = '__all__'


# --- PaymentMode ---
class PaymentModeSerializer(serializers.ModelSerializer):
    payment_method_name = serializers.SerializerMethodField()
    payment_method_fields = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    qr_image_url = serializers.SerializerMethodField()
    user_username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = PaymentMode
        fields = [
            'id', 'user', 'user_username', 'payment_method', 'payment_method_name', 'payment_method_fields',
            'qr_image', 'qr_image_url', 'details',
            'status', 'status_display', 'reject_reason', 'action_by', 'action_at',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['reject_reason', 'action_by', 'action_at']

    def get_payment_method_name(self, obj):
        if obj.payment_method_id:
            return obj.payment_method.name
        return None

    def get_payment_method_fields(self, obj):
        if obj.payment_method_id and obj.payment_method.fields:
            return obj.payment_method.fields
        return {}

    def get_qr_image_url(self, obj):
        if not obj.qr_image:
            return None
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.qr_image.url)
        return obj.qr_image.url

    def validate(self, attrs):
        if not self.instance and not attrs.get('payment_method'):
            raise serializers.ValidationError({'payment_method': 'This field is required when creating a payment mode.'})
        details = attrs.get('details', (self.instance and self.instance.details) if self.instance else {})
        if isinstance(details, str):
            try:
                details = json.loads(details)
                attrs['details'] = details
            except (TypeError, ValueError):
                raise serializers.ValidationError({'details': 'Invalid JSON.'})
        payment_method = attrs.get('payment_method') or (self.instance and self.instance.payment_method if self.instance else None)
        if payment_method and isinstance(details, dict):
            allowed = set((payment_method.fields or {}).keys())
            if allowed and not set(details.keys()).issubset(allowed):
                extra = set(details.keys()) - allowed
                raise serializers.ValidationError({'details': f'Invalid keys: {extra}. Allowed: {list(allowed)}'})
        return attrs


# --- Deposit ---
class DepositSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    user_name = serializers.CharField(source='user.name', read_only=True)
    user_phone = serializers.CharField(source='user.phone', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_whatsapp_number = serializers.CharField(source='user.whatsapp_number', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_mode_name = serializers.SerializerMethodField()
    payment_mode_qr_image = serializers.SerializerMethodField()
    payment_mode_detail = serializers.SerializerMethodField()

    class Meta:
        model = Deposit
        fields = '__all__'

    def get_payment_mode_name(self, obj):
        if not obj.payment_mode or not obj.payment_mode.payment_method_id:
            return None
        return obj.payment_mode.payment_method.name

    def get_payment_mode_qr_image(self, obj):
        if not obj.payment_mode or not obj.payment_mode.qr_image:
            return None
        request = self.context.get('request')
        url = obj.payment_mode.qr_image.url
        if request:
            return request.build_absolute_uri(url)
        return url

    def get_payment_mode_detail(self, obj):
        if not obj.payment_mode:
            return None
        return PaymentModeSerializer(obj.payment_mode, context=self.context).data

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['payment_mode_detail'] = self.get_payment_mode_detail(instance)
        return ret


class DepositCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Deposit
        fields = ['amount', 'payment_mode', 'screenshot', 'remarks', 'reference_id']


# --- Withdraw ---
class WithdrawSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    user_name = serializers.CharField(source='user.name', read_only=True)
    user_phone = serializers.CharField(source='user.phone', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_whatsapp_number = serializers.CharField(source='user.whatsapp_number', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_mode_name = serializers.SerializerMethodField()
    payment_mode_qr_image = serializers.SerializerMethodField()
    payment_mode_detail = serializers.SerializerMethodField()

    class Meta:
        model = Withdraw
        fields = '__all__'

    def get_payment_mode_name(self, obj):
        if not obj.payment_mode or not obj.payment_mode.payment_method_id:
            return None
        return obj.payment_mode.payment_method.name

    def get_payment_mode_qr_image(self, obj):
        if not obj.payment_mode or not obj.payment_mode.qr_image:
            return None
        request = self.context.get('request')
        url = obj.payment_mode.qr_image.url
        if request:
            return request.build_absolute_uri(url)
        return url

    def get_payment_mode_detail(self, obj):
        if not obj.payment_mode:
            return None
        return PaymentModeSerializer(obj.payment_mode, context=self.context).data

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['payment_mode_detail'] = self.get_payment_mode_detail(instance)
        return ret


class WithdrawCreateSerializer(serializers.ModelSerializer):
    wallet = serializers.ChoiceField(choices=WithdrawWallet.choices, default=WithdrawWallet.MAIN, required=False)

    class Meta:
        model = Withdraw
        fields = ['amount', 'wallet', 'payment_mode', 'screenshot', 'remarks']

    def validate(self, attrs):
        request = self.context.get('request')
        if not request or not request.user:
            return attrs
        user = request.user
        amount = attrs.get('amount')
        wallet = (attrs.get('wallet') or WithdrawWallet.MAIN)
        if wallet not in (WithdrawWallet.MAIN, WithdrawWallet.BONUS):
            wallet = WithdrawWallet.MAIN
        eligibility = get_withdraw_eligibility(user)
        main_withdrawable = eligibility['main_withdrawable']
        bonus_withdrawable = eligibility['bonus_withdrawable']
        total_withdrawable = eligibility['total_withdrawable']
        can_withdraw_main = eligibility['can_withdraw_main']
        can_withdraw_bonus = eligibility['can_withdraw_bonus']
        if amount is not None and amount > total_withdrawable:
            raise serializers.ValidationError(
                {'amount': f'Amount exceeds withdrawable balance (₹{total_withdrawable}).'}
            )
        if wallet == WithdrawWallet.BONUS:
            if not can_withdraw_bonus:
                raise serializers.ValidationError(
                    {'wallet': 'Bonus is not withdrawable until bonus roll requirement is met.'}
                )
            if amount is not None and amount > bonus_withdrawable:
                raise serializers.ValidationError(
                    {'amount': f'Amount exceeds bonus withdrawable (₹{bonus_withdrawable}).'}
                )
        else:
            if not can_withdraw_main:
                raise serializers.ValidationError(
                    {'wallet': 'Main balance is not withdrawable until you have played at least one game after deposit.'}
                )
            if amount is not None and amount > main_withdrawable:
                raise serializers.ValidationError(
                    {'amount': f'Amount exceeds main withdrawable (₹{main_withdrawable}).'}
                )
        attrs['wallet'] = wallet
        return attrs


# --- BonusRequest ---
class BonusRequestSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    user_name = serializers.CharField(source='user.name', read_only=True)
    user_phone = serializers.CharField(source='user.phone', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_whatsapp_number = serializers.CharField(source='user.whatsapp_number', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    bonus_type_display = serializers.CharField(source='get_bonus_type_display', read_only=True)
    bonus_rule_name = serializers.SerializerMethodField()

    class Meta:
        model = BonusRequest
        fields = '__all__'

    def get_bonus_rule_name(self, obj):
        return obj.bonus_rule.name if obj.bonus_rule else None


class BonusRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = BonusRequest
        fields = ['amount', 'bonus_type', 'bonus_rule', 'remarks']


# --- BonusRule ---
class BonusRuleSerializer(serializers.ModelSerializer):
    bonus_type_display = serializers.CharField(source='get_bonus_type_display', read_only=True)
    reward_type_display = serializers.CharField(source='get_reward_type_display', read_only=True)

    class Meta:
        model = BonusRule
        fields = '__all__'


# --- GameProvider ---
class GameProviderSerializer(serializers.ModelSerializer):
    single_game_id = serializers.SerializerMethodField()

    class Meta:
        model = GameProvider
        fields = [
            'id', 'name', 'code', 'image', 'banner', 'api_endpoint', 'api_secret', 'api_token',
            'is_active', 'created_at', 'updated_at', 'single_game_id',
        ]

    def get_single_game_id(self, obj):
        qs = Game.objects.filter(provider=obj, is_active=True, is_coming_soon=False)
        count = qs.count()
        if count == 1:
            return qs.values_list('id', flat=True).first()
        if count > 1:
            lobby = qs.filter(is_lobby=True).first()
            return lobby.id if lobby else None
        return None


# --- GameCategory ---
class GameCategorySerializer(serializers.ModelSerializer):
    games_count = serializers.SerializerMethodField()

    class Meta:
        model = GameCategory
        fields = ['id', 'name', 'icon', 'svg', 'is_active', 'created_at', 'updated_at', 'games_count']

    def get_games_count(self, obj):
        return Game.objects.filter(category=obj, is_active=True, is_coming_soon=False).count()


# --- Game ---
class GameListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    provider_name = serializers.CharField(source='provider.name', read_only=True)
    provider_code = serializers.CharField(source='provider.code', read_only=True)

    class Meta:
        model = Game
        fields = [
            'id', 'name', 'game_uid', 'image', 'image_url', 'coming_soon_image', 'min_bet', 'max_bet', 'is_active',
            'category', 'category_name', 'provider', 'provider_name', 'provider_code',
            'is_coming_soon', 'coming_soon_launch_date', 'coming_soon_description',
            'is_top_game', 'is_popular_game', 'is_lobby', 'created_at',
        ]


class GameDetailSerializer(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(queryset=GameCategory.objects.all())
    provider = serializers.PrimaryKeyRelatedField(queryset=GameProvider.objects.all())

    class Meta:
        model = Game
        fields = [
            'id', 'name', 'game_uid', 'image', 'image_url', 'coming_soon_image', 'min_bet', 'max_bet', 'is_active',
            'category', 'provider',
            'is_coming_soon', 'coming_soon_launch_date', 'coming_soon_description',
            'is_top_game', 'is_popular_game', 'is_lobby', 'created_at', 'updated_at',
        ]


class ComingSoonGameSerializer(serializers.ModelSerializer):
    """For public coming-soon-games list: id, name, image, image_url, coming_soon_image, coming_soon_launch_date, coming_soon_description."""

    class Meta:
        model = Game
        fields = [
            'id', 'name', 'image', 'image_url', 'coming_soon_image',
            'coming_soon_launch_date', 'coming_soon_description',
        ]


# --- ComingSoonEnrollment ---
class ComingSoonEnrollmentSerializer(serializers.ModelSerializer):
    game_name = serializers.CharField(source='game.name', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = ComingSoonEnrollment
        fields = ['id', 'game', 'game_name', 'user', 'user_username', 'created_at']


# --- GameLog ---
class GameLogSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    game_name = serializers.CharField(source='game.name', read_only=True)
    category_name = serializers.CharField(source='game.category.name', read_only=True)
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    wallet_display = serializers.CharField(source='get_wallet_display', read_only=True)
    effective_bet_amount = serializers.SerializerMethodField()

    class Meta:
        model = GameLog
        fields = '__all__'

    def get_effective_bet_amount(self, obj):
        if obj.bet_amount and obj.bet_amount > 0:
            return float(obj.bet_amount)
        if obj.type == 'lose' and obj.lose_amount and obj.lose_amount > 0:
            return float(obj.lose_amount)
        return None


# --- Transaction ---
class TransactionSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    transaction_type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)
    wallet_display = serializers.CharField(source='get_wallet_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Transaction
        fields = '__all__'


# --- ActivityLog ---
class ActivityLogSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True, default=None)
    action_display = serializers.CharField(source='get_action_display', read_only=True)

    class Meta:
        model = ActivityLog
        fields = '__all__'


# --- Message ---
class MessageSerializer(serializers.ModelSerializer):
    sender_username = serializers.CharField(source='sender.username', read_only=True)
    receiver_username = serializers.CharField(source='receiver.username', read_only=True)

    class Meta:
        model = Message
        fields = '__all__'


class MessageCreateSerializer(serializers.ModelSerializer):
    message = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Message
        fields = ['receiver', 'message', 'file', 'image']

    def validate(self, attrs):
        message = (attrs.get('message') or '').strip()
        file = attrs.get('file')
        image = attrs.get('image')
        if not message and not file and not image:
            raise serializers.ValidationError(
                'Either message text or a file/image is required.'
            )
        if 'message' not in attrs:
            attrs['message'] = message or ''
        return attrs


# --- Testimonial ---
class TestimonialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Testimonial
        fields = '__all__'


# --- CMSPage ---
class CMSPageSerializer(serializers.ModelSerializer):
    class Meta:
        model = CMSPage
        fields = '__all__'
