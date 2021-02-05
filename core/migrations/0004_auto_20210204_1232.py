# Generated by Django 3.1.5 on 2021-02-04 11:32

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_auto_20210202_1250'),
    ]

    operations = [
        migrations.AddField(
            model_name='bankaccount',
            name='administrated_by',
            field=models.ManyToManyField(related_name='administrating_accounts', to='core.BankCustomer'),
        ),
        migrations.AlterField(
            model_name='bankaccount',
            name='account_owned_by',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='account_owned_by', to='core.bankcustomer', verbose_name='Inhaber'),
        ),
    ]