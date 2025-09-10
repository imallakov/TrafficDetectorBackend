from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )

    class Meta:
        model = get_user_model()
        fields = ['email', 'password', 'password_confirm']

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Password fields don't match."})
        return attrs

    def create(self, validated_data):
        # Remove password_confirm from the data
        validated_data.pop('password_confirm')

        # Create user instance
        user = get_user_model().objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
        )
        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ['id', 'first_name', 'last_name', 'email', 'email_confirmed', 'is_active']
        extra_kwargs = {
            'password': {'write_only': True},
            'email_confirmed': {'read_only': True},
            'is_active': {'read_only': True},
        }


class PasswordUpdateSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value

    def validate_new_password(self, value):
        # Add custom password validation logic here if needed
        if len(value) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters long.")
        return value

    def update(self, instance, validated_data):
        instance.set_password(validated_data['new_password'])
        instance.save()
        return instance
