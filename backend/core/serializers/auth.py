from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from core.models import Profile

User = get_user_model()


class AuthUserSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    email = serializers.EmailField(allow_blank=True)
    display_name = serializers.CharField(allow_blank=True)
    has_completed_intake = serializers.BooleanField()


def auth_user_payload(user) -> dict:
    profile, _ = Profile.objects.get_or_create(user=user)
    return {
        "id": user.id,
        "username": user.get_username(),
        "email": user.email,
        "display_name": profile.display_name,
        "has_completed_intake": profile.current_skin_profile is not None,
    }


def _unique_username_from_email(email: str) -> str:
    base = email.split("@", 1)[0].strip().lower() or "user"
    base = "".join(char if char.isalnum() or char in "._-" else "-" for char in base)
    base = base[:24] or "user"
    candidate = base
    counter = 1
    while User.objects.filter(username=candidate).exists():
        suffix = f"-{counter}"
        candidate = f"{base[: 30 - len(suffix)]}{suffix}"
        counter += 1
    return candidate


class SignupSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    display_name = serializers.CharField(required=False, allow_blank=True, max_length=128)

    def validate_email(self, value: str) -> str:
        email = value.strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("Unable to create an account with these credentials.")
        return email

    def validate_password(self, value: str) -> str:
        validate_password(value)
        return value

    def create(self, validated_data: dict):
        email = validated_data["email"]
        user = User.objects.create_user(
            username=_unique_username_from_email(email),
            email=email,
            password=validated_data["password"],
        )
        Profile.objects.get_or_create(
            user=user,
            defaults={"display_name": validated_data.get("display_name", "").strip()},
        )
        return user


class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs: dict) -> dict:
        identifier = attrs["identifier"].strip()
        password = attrs["password"]
        username = identifier
        if "@" in identifier:
            user = User.objects.filter(email__iexact=identifier).first()
            if user is not None:
                username = user.get_username()

        user = authenticate(
            request=self.context.get("request"),
            username=username,
            password=password,
        )
        if user is None:
            raise serializers.ValidationError("Invalid email or password.")
        attrs["user"] = user
        return attrs
