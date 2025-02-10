from django.contrib import admin
from .models import User, UserProfile, Job, JobApplication

# Register your models to make them available in the Django admin interface
admin.site.register(User)
admin.site.register(UserProfile)
admin.site.register(Job)
admin.site.register(JobApplication)
