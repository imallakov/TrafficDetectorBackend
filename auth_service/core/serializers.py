from django.utils.translation import gettext_lazy as _
from rest_framework import exceptions, serializers
from dj_rest_auth.serializers import LoginSerializer as BaseLoginSerializer
from dj_rest_auth.registration.serializers import RegisterSerializer as BaseRegisterSerializer
from allauth.account.adapter import get_adapter
from allauth.account.utils import setup_user_email


class EmailLoginSerializer(BaseLoginSerializer):
    """
    Force email+password login (no username).
    """
    username = None  # hide username field from schema
    email = serializers.EmailField(required=True)

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")

        if email and password:
            # dj-rest-auth BaseLoginSerializer has self.authenticate()
            user = self.authenticate(email=email, password=password)
            if not user:
                raise exceptions.AuthenticationFailed(_("Invalid email/password."))
        else:
            msg = _("Must include 'email' and 'password'.")
            raise exceptions.ValidationError(msg)

        attrs["user"] = user
        return attrs


class EmailRegisterSerializer(BaseRegisterSerializer):
    """
    Register with email + password only (no username).
    Works with a custom user model that uses email as USERNAME_FIELD.
    """
    username = None  # hide username field from schema
    email = serializers.EmailField(required=True)

    def get_cleaned_data(self):
        return {
            "email": self.validated_data.get("email", ""),
            "password1": self.validated_data.get("password1", ""),
            "password2": self.validated_data.get("password2", ""),
        }

    def save(self, request):
        adapter = get_adapter()
        user = adapter.new_user(request)  # creates user instance
        self.cleaned_data = self.get_cleaned_data()

        # Ensure email is set; username is not used
        user_email = self.cleaned_data.get("email")
        if user_email:
            setattr(user, "email", user_email)

        # If your custom model kept a 'username' field for legacy reasons, ensure it's empty:
        if hasattr(user, "username"):
            # Only safe if the model allows blank username; best is to remove the field completely as above.
            setattr(user, "username", "")

        adapter.save_user(request, user, self)  # sets password, etc.
        setup_user_email(request, user, [])  # allauth email setup
        return user
