from core import models
from rest_framework import serializers

class BankCustomersSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.BankCustomer
        fields = '__all__'
        read_only_fields = (
            'name',
            'vorname',
            'created_at',
            'updated_at',
            'email',
        )

class BankAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.BankAccount
        fields = '__all__'
        read_only_fields = (
            'name',
            'vorname',
            'created_at',
            'updated_at',
            'email',
        )