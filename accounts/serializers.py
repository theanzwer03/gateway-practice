from django.db import transaction
from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8, required=False, trim_whitespace=False)

    class Meta:
        model = User
        fields = ["id", "username", "email", "email_verified", "first_name", "last_name", "role", "is_active", "password", "created_at", "updated_at"]
        read_only_fields = ["id", "email_verified", "created_at", "updated_at"]

    @transaction.atomic
    def create(self, validated_data):
        from .emails import send_verification_email

        password = validated_data.pop("password", None)
        user = User(**validated_data)
        if user.role == User.Role.CLIENT:
            user.email_verified = False
        user.set_password(password) if password else user.set_unusable_password()
        user.save()
        if not user.email_verified:
            send_verification_email(user)
        return user

    @transaction.atomic
    def update(self, instance, validated_data):
        from .emails import send_verification_email

        email_changed = (
            "email" in validated_data and validated_data["email"] != instance.email
            and instance.role == User.Role.CLIENT
        )
        if email_changed:
            validated_data["email_verified"] = False
        password = validated_data.pop("password", None)
        instance = super().update(instance, validated_data)
        if password:
            instance.set_password(password)
            instance.save(update_fields=["password"])
        if email_changed:
            from rest_framework.authtoken.models import Token

            Token.objects.filter(user=instance).delete()
            send_verification_email(instance)
        return instance
