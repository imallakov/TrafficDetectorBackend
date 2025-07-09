from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from django.contrib.auth.models import User
import jwt
from django.conf import settings


@api_view(['POST'])
@permission_classes([AllowAny])
def validate_token(request):
    """Internal endpoint for other microservices to validate JWT tokens"""
    token = request.data.get('token')

    if not token:
        return Response({'valid': False, 'error': 'Token missing'},
                        status=status.HTTP_400_BAD_REQUEST)

    try:
        # Remove 'Bearer ' prefix if present
        if token.startswith('Bearer '):
            token = token[7:]

        # Validate token using simplejwt
        UntypedToken(token)

        # Decode to get user info
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        user_id = payload.get('user_id')

        # Check if user exists
        user = User.objects.get(id=user_id)

        return Response({
            'valid': True,
            'user_id': user_id,
            'username': user.username,
            'email': user.email
        })

    except (InvalidToken, TokenError):
        return Response({'valid': False, 'error': 'Invalid token'})
    except User.DoesNotExist:
        return Response({'valid': False, 'error': 'User not found'})
    except Exception as e:
        return Response({'valid': False, 'error': str(e)})
