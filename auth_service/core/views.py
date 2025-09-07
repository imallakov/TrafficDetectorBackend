from datetime import datetime, timezone

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import UntypedToken, RefreshToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework.views import APIView
from rest_framework import serializers as drf_serializers
import jwt
from django.conf import settings
from django.middleware.csrf import get_token
from django.core.signing import Signer, BadSignature
from django.contrib.auth.password_validation import validate_password
from drf_spectacular.utils import extend_schema, OpenApiResponse, inline_serializer

from .models import CustomUser, OTP
from .serializers import UserRegistrationSerializer, UserSerializer
from .utils import generate_otp

User = CustomUser
secure_cookie = settings.DEBUG is False


# Serializers for schema documentation
class EmailSerializer(drf_serializers.Serializer):
    email = drf_serializers.EmailField()


class EmailOTPSerializer(drf_serializers.Serializer):
    email = drf_serializers.EmailField()
    otp = drf_serializers.CharField()


class PasswordResetConfirmSerializer(drf_serializers.Serializer):
    temp_token = drf_serializers.CharField()
    password = drf_serializers.CharField()


class TokenValidationSerializer(drf_serializers.Serializer):
    token = drf_serializers.CharField()


class RegisterView(APIView):
    @extend_schema(
        request=UserRegistrationSerializer,
        responses={
            201: OpenApiResponse(
                response=inline_serializer(
                    name='RegisterSuccessResponse',
                    fields={
                        'message': drf_serializers.CharField(),
                    }
                ),
                description='User registered successfully'
            ),
            400: OpenApiResponse(
                response=UserRegistrationSerializer,
                description='Validation error'
            )
        }
    )
    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {'message': 'User registered successfully.'},
                status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CustomTokenObtainPairView(TokenObtainPairView):
    @extend_schema(
        responses={
            200: OpenApiResponse(
                response=inline_serializer(
                    name='LoginSuccessResponse',
                    fields={
                        'access': drf_serializers.CharField(),
                        'user': UserSerializer(),
                    }
                ),
                description='Login successful'
            ),
            400: OpenApiResponse(description='Invalid credentials'),
            403: OpenApiResponse(description='Account inactive')
        }
    )
    def post(self, request, *args, **kwargs):
        # Validate user credentials and generate tokens
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Get the validated user
        user = serializer.user

        # Check if the user is active
        if not user.is_active:
            raise PermissionDenied("Your account is inactive. Please contact support.")

        # Call the parent method to generate tokens
        response = super().post(request, *args, **kwargs)

        # Retrieve the refresh token from the response
        refresh_token = response.data['refresh']
        response.data.pop('refresh', None)

        # Get or generate CSRF token
        csrf_token = get_token(request)

        # Calculate cookie expiry to match token lifetime
        expiry = datetime.now(timezone.utc) + settings.SIMPLE_JWT.get('REFRESH_TOKEN_LIFETIME')

        # Set HttpOnly cookie for refresh token
        response.set_cookie(
            key='refreshToken',
            value=refresh_token,
            httponly=True,  # Set to True for security
            secure=secure_cookie,  # Use secure cookies in production
            samesite='Lax',
            expires=expiry
        )

        # Set CSRF token cookie
        response.set_cookie(
            key='csrftoken',
            value=csrf_token,
            httponly=False,  # Must be accessible by JS
            secure=secure_cookie,
            samesite='Lax'
        )

        # Serialize the user object and add to response
        user_serializer = UserSerializer(user)
        response.data['user'] = user_serializer.data
        # logger.info(f"User logged in: {user_serializer.data.email}")
        return response


class CustomTokenRefreshView(TokenRefreshView):
    @extend_schema(
        request=None,
        responses={
            200: OpenApiResponse(
                response=inline_serializer(
                    name='RefreshSuccessResponse',
                    fields={
                        'access': drf_serializers.CharField(),
                    }
                ),
                description='Token refreshed successfully'
            ),
            401: OpenApiResponse(description='Invalid refresh token')
        }
    )
    def post(self, request, *args, **kwargs):
        refresh_token = request.COOKIES.get('refreshToken')

        if not refresh_token:
            return Response({'message': 'Refresh token not found'}, status=401)

        # print('✅ Received REFRESH TOKEN:', refresh_token)

        try:
            # Ensure request data is mutable
            request._full_data = {'refresh': refresh_token}  # ✅ Correct way to override request data

            # print('✅ Request data before sending to super():', request._full_data)

            response = super().post(request, *args, **kwargs)

            # print('✅ Response data:', response.data)

            # Handle refresh token rotation if enabled
            if 'refresh' in response.data:
                expiry = datetime.now(timezone.utc) + settings.SIMPLE_JWT.get('REFRESH_TOKEN_LIFETIME')

                response.delete_cookie('refreshToken')  # Delete old token first
                response.set_cookie(
                    key='refreshToken',
                    value=response.data['refresh'],
                    httponly=True,
                    secure=secure_cookie,  # Ensure HTTPS is used
                    samesite='Lax',
                    expires=expiry
                )

                del response.data['refresh']

            csrf_token = get_token(request)
            response.set_cookie(
                key='csrftoken',
                value=csrf_token,
                httponly=False,  # ✅ Accessible by frontend
                secure=secure_cookie,
                samesite='Lax'
            )

            return response

        except Exception as e:
            # print(f"❌ Exception occurred: {e}")
            return Response({'message': 'Invalid refresh token'}, status=401)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=None,
        responses={
            200: OpenApiResponse(
                response=inline_serializer(
                    name='LogoutResponse',
                    fields={
                        'message': drf_serializers.CharField(),
                    }
                ),
                description='Successfully logged out'
            ),
            401: OpenApiResponse(description='Unauthorized')
        }
    )
    def post(self, request):
        refresh_token = request.COOKIES.get('refreshToken')

        if not refresh_token:
            return Response({'message': 'No refresh token provided.'}, status=401)

        try:
            RefreshToken(refresh_token).blacklist()

            response = Response({'message': 'Successfully logged out.'}, status=200)
            response.delete_cookie('refreshToken')
            response.delete_cookie('csrftoken')

            return response

        except Exception as e:
            return Response({'message': 'Invalid refresh token.'}, status=401)


class PasswordResetRequestView(APIView):
    @extend_schema(
        request=EmailSerializer,
        responses={
            200: OpenApiResponse(
                response=inline_serializer(
                    name='PasswordResetRequestResponse',
                    fields={
                        'message': drf_serializers.CharField(),
                    }
                ),
                description='OTP sent successfully'
            ),
            404: OpenApiResponse(description='User not found')
        }
    )
    def post(self, request):
        email = request.data.get('email')
        try:
            user = User.objects.get(email=email)
            generate_otp(user, 'password_reset')  # Implemented in your codebase
            return Response({"message": "OTP sent to your email."}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"error": "No user found with this email."}, status=status.HTTP_404_NOT_FOUND)


class PasswordResetValidateOTPView(APIView):
    @extend_schema(
        request=EmailOTPSerializer,
        responses={
            200: OpenApiResponse(
                response=inline_serializer(
                    name='PasswordResetValidateResponse',
                    fields={
                        'temp_token': drf_serializers.CharField(),
                    }
                ),
                description='OTP validated successfully'
            ),
            400: OpenApiResponse(description='Invalid OTP or email')
        }
    )
    def post(self, request):
        email = request.data.get('email')
        otp_code = request.data.get('otp')

        try:
            user = User.objects.get(email=email)
            otp = OTP.objects.get(user=user, otp=otp_code, purpose='password_reset', is_used=False)

            if not otp.is_valid():
                return Response({"error": "OTP expired or already used."}, status=status.HTTP_400_BAD_REQUEST)

            # Generate a temporary signed token
            signer = Signer()
            temp_token = signer.sign(user.id)

            # Optionally mark the OTP as used here
            otp.is_used = True
            otp.save()

            return Response({"temp_token": temp_token}, status=status.HTTP_200_OK)

        except (User.DoesNotExist, OTP.DoesNotExist):
            return Response({"error": "Invalid email or OTP."}, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetConfirmView(APIView):
    @extend_schema(
        request=PasswordResetConfirmSerializer,
        responses={
            200: OpenApiResponse(
                response=inline_serializer(
                    name='PasswordResetConfirmResponse',
                    fields={
                        'message': drf_serializers.CharField(),
                    }
                ),
                description='Password reset successfully'
            ),
            400: OpenApiResponse(description='Invalid token or validation error'),
            404: OpenApiResponse(description='User not found')
        }
    )
    def post(self, request):
        temp_token = request.data.get('temp_token')
        new_password = request.data.get('password')

        if not temp_token or not new_password:
            return Response({"error": "Token and password are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Unsigned the temporary token to get user ID
            signer = Signer()
            user_id = signer.unsign(temp_token)

            # Retrieve the user
            user = User.objects.get(id=user_id)

            # Validate the new password
            validate_password(new_password, user=user)

            # Set and save the new password
            user.set_password(new_password)
            user.save()

            return Response({"message": "Password reset successfully."}, status=status.HTTP_200_OK)

        except BadSignature:
            return Response({"error": "Invalid or expired token."}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        except ValidationError as e:
            return Response({"error": e.messages}, status=status.HTTP_400_BAD_REQUEST)


class EmailVerificationRequestView(APIView):
    permission_classes = [IsAuthenticated]
    @extend_schema(
        request=EmailSerializer,
        responses={
            200: OpenApiResponse(
                response=inline_serializer(
                    name='EmailVerificationRequestResponse',
                    fields={
                        'message': drf_serializers.CharField(),
                    }
                ),
                description='Verification email sent'
            ),
            400: OpenApiResponse(description='Email already verified'),
            404: OpenApiResponse(description='User not found')
        }
    )
    def post(self, request):
        email = request.data.get('email')
        try:
            user = User.objects.get(email=email)
            if not user.email_confirmed:
                generate_otp(user, 'email_verification')
                return Response({"message": "Verification email sent."}, status=status.HTTP_200_OK)
            else:
                return Response({"error": "Email already verified."}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)


class EmailVerificationConfirmView(APIView):
    permission_classes = [IsAuthenticated]
    @extend_schema(
        request=EmailOTPSerializer,
        responses={
            200: OpenApiResponse(
                response=inline_serializer(
                    name='EmailVerificationConfirmResponse',
                    fields={
                        'message': drf_serializers.CharField(),
                    }
                ),
                description='Email verified successfully'
            ),
            400: OpenApiResponse(description='Invalid OTP or email mismatch')
        }
    )
    def post(self, request):
        otp_code = request.data.get('otp')
        email = request.data.get('email')

        if not otp_code or not email:
            return Response({"error": "OTP and email are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Fetch the OTP instance
            otp = OTP.objects.get(otp=otp_code, purpose='email_verification', is_used=False)

            if not otp.is_valid():
                return Response({"error": "OTP expired or already used."}, status=status.HTTP_400_BAD_REQUEST)

            # Validate that the email matches the user associated with the OTP
            if otp.user.email != email:
                return Response({"error": "The provided email does not match the OTP."},
                                status=status.HTTP_400_BAD_REQUEST)

            # Mark the email as confirmed
            user = otp.user
            user.email_confirmed = True
            user.save()

            # Mark the OTP as used
            otp.is_used = True
            otp.save()

            return Response({"message": "Email verified successfully."}, status=status.HTTP_200_OK)
        except OTP.DoesNotExist:
            return Response({"error": "Invalid OTP or token."}, status=status.HTTP_400_BAD_REQUEST)


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
            'email': user.email
        })

    except (InvalidToken, TokenError):
        return Response({'valid': False, 'error': 'Invalid token'})
    except User.DoesNotExist:
        return Response({'valid': False, 'error': 'User not found'})
    except Exception as e:
        return Response({'valid': False, 'error': str(e)})
