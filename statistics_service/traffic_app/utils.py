import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def validate_user_token(token):
    """Validates JWT token through Auth Service"""
    try:
        if token.startswith('Bearer '):
            token = token[7:]

        response = requests.post(
            f"{settings.AUTH_SERVICE_URL}/auth/validate-token/",
            json={"token": token},
            timeout=5
        )

        if response.status_code == 200:
            return response.json()
        else:
            return {"valid": False, "error": "Invalid token"}

    except requests.RequestException as e:
        logger.error(f"Cannot reach auth service: {e}")
        return {"valid": False, "error": f"Auth service unavailable: {e}"}
