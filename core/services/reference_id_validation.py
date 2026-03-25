"""Global uniqueness for non-empty reference_id across Deposit and Withdraw (case-insensitive)."""
from core.models import Deposit, Withdraw


def validate_ref_unique(value, exclude_deposit_id=None, exclude_withdraw_id=None):
    """
    If value is non-empty after strip, ensure no other Deposit or Withdraw uses the same
    reference (case-insensitive). Returns (True, None) or (False, error_message).
    """
    stripped = (value or "").strip()
    if not stripped:
        return True, None
    dep_qs = Deposit.objects.all()
    if exclude_deposit_id is not None:
        dep_qs = dep_qs.exclude(pk=exclude_deposit_id)
    wd_qs = Withdraw.objects.all()
    if exclude_withdraw_id is not None:
        wd_qs = wd_qs.exclude(pk=exclude_withdraw_id)
    if dep_qs.filter(reference_id__iexact=stripped).exists():
        return False, "This transaction/reference id is already used."
    if wd_qs.filter(reference_id__iexact=stripped).exists():
        return False, "This transaction/reference id is already used."
    return True, None
