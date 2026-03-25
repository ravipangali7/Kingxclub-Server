from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from core.permissions import require_role
from core.models import UserRole
from core.services.clean_data_service import get_metadata, execute_clean_data


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def clean_data_metadata(request):
    err = require_role(request, [UserRole.POWERHOUSE])
    if err:
        return err
    return Response(get_metadata())


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def clean_data_execute(request):
    err = require_role(request, [UserRole.POWERHOUSE])
    if err:
        return err

    pin = request.data.get("pin")
    password = request.data.get("password")
    if pin is None or pin == "":
        return Response({"detail": "PIN required."}, status=status.HTTP_400_BAD_REQUEST)
    if not request.user.pin or request.user.pin != pin:
        return Response({"detail": "Invalid PIN."}, status=status.HTTP_400_BAD_REQUEST)
    if password is None or password == "":
        return Response({"detail": "Password required."}, status=status.HTTP_400_BAD_REQUEST)
    if not request.user.check_password(password):
        return Response({"detail": "Invalid password."}, status=status.HTTP_400_BAD_REQUEST)

    models = request.data.get("models")
    if not isinstance(models, list):
        return Response({"detail": "Invalid payload: models must be a list."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        result = execute_clean_data(models, request.user)
    except Exception as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if result.get("detail") == "No valid models selected.":
        return Response(result, status=status.HTTP_400_BAD_REQUEST)

    return Response(result)
