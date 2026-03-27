"""
Withdrawal eligibility for players: main withdrawable (after deposit + 1 game)
and bonus withdrawable (after approved bonus + roll_required games).
"""
from decimal import Decimal

from core.models import Deposit, BonusRequest, GameLog


def get_withdraw_eligibility(user):
    """
    Compute withdrawable amounts and flags for a user (intended for players).
    Returns a dict:
      main_withdrawable: Decimal (0 or user.main_balance)
      bonus_withdrawable: Decimal (0 or user.bonus_balance)
      total_withdrawable: main_withdrawable + bonus_withdrawable
      can_withdraw_main: bool
      can_withdraw_bonus: bool
    """
    main_balance = user.main_balance or Decimal('0')
    bonus_balance = user.bonus_balance or Decimal('0')

    # Main: need at least one approved deposit and at least one game after earliest such deposit
    first_approved = (
        Deposit.objects.filter(user=user, status='approved')
        .order_by('processed_at')
        .values_list('processed_at', flat=True)
        .first()
    )
    if not first_approved:
        main_withdrawable = Decimal('0')
        can_withdraw_main = False
    else:
        has_game_after_deposit = GameLog.objects.filter(
            user=user,
            created_at__gt=first_approved,
        ).exists()
        if not has_game_after_deposit:
            main_withdrawable = Decimal('0')
            can_withdraw_main = False
        else:
            main_withdrawable = main_balance
            can_withdraw_main = True

    # Bonus: need at least one approved bonus request; for every approved request,
    # games played after its processed_at must be >= bonus_rule.roll_required
    approved_bonus_requests = list(
        BonusRequest.objects.filter(user=user, status='approved').select_related('bonus_rule')
    )
    rolls_needed = 0
    if not approved_bonus_requests:
        bonus_withdrawable = Decimal('0')
        can_withdraw_bonus = False
    else:
        all_rolls_met = True
        for req in approved_bonus_requests:
            roll_required = (req.bonus_rule.roll_required or 0) if req.bonus_rule else 0
            if not req.processed_at:
                all_rolls_met = False
                rolls_needed = max(rolls_needed, int(roll_required))
                break
            count = GameLog.objects.filter(
                user=user,
                created_at__gt=req.processed_at,
            ).count()
            remaining = max(int(roll_required) - int(count), 0)
            rolls_needed = max(rolls_needed, remaining)
            if count < roll_required:
                all_rolls_met = False
                break
        if not all_rolls_met:
            bonus_withdrawable = Decimal('0')
            can_withdraw_bonus = False
        else:
            bonus_withdrawable = bonus_balance
            can_withdraw_bonus = True

    total_withdrawable = main_withdrawable + bonus_withdrawable
    return {
        'main_withdrawable': main_withdrawable,
        'bonus_withdrawable': bonus_withdrawable,
        'total_withdrawable': total_withdrawable,
        'can_withdraw_main': can_withdraw_main,
        'can_withdraw_bonus': can_withdraw_bonus,
        'rolls_needed': rolls_needed,
    }
