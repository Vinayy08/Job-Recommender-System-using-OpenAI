# Generated by Django 5.1.3 on 2024-12-08 17:57

import main.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0008_alter_jobapplication_user_profile'),
    ]

    operations = [
        migrations.AlterField(
            model_name='jobapplication',
            name='resume',
            field=models.FileField(blank=True, null=True, upload_to=main.models.upload_to_resumes),
        ),
    ]
