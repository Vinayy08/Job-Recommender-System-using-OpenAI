# Generated by Django 5.1.7 on 2025-03-26 10:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0002_employeecertification'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='testimonials',
            field=models.TextField(blank=True, null=True),
        ),
    ]
