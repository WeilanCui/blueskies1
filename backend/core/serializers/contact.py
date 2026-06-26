from rest_framework import serializers

from core.models import ContactSubmission


class ContactSubmissionSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True, allow_blank=False)

    class Meta:
        model = ContactSubmission
        fields = ["id", "name", "email", "feedback", "source", "created_at"]
        read_only_fields = ["id", "created_at"]
        extra_kwargs = {
            "source": {"required": False, "allow_blank": True},
        }

    def validate_name(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Name is required.")
        return value

    def validate_email(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Email is required.")
        return value

    def validate_feedback(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Feedback is required.")
        return value
