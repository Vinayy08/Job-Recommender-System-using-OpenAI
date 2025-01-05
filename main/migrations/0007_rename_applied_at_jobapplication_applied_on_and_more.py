# Generated by Django 5.1.3 on 2024-12-07 17:35

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0006_jobapplication'),
    ]

    operations = [
        migrations.RenameField(
            model_name='jobapplication',
            old_name='applied_at',
            new_name='applied_on',
        ),
        migrations.RenameField(
            model_name='jobapplication',
            old_name='applicant',
            new_name='user',
        ),
        migrations.AddField(
            model_name='jobapplication',
            name='resume',
            field=models.FileField(blank=True, null=True, upload_to='resumes/'),
        ),
        migrations.AddField(
            model_name='jobapplication',
            name='user_profile',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='main.userprofile'),
        ),
    ]
