from django.contrib.auth.models import User
from django.db import models
from django.core.exceptions import ObjectDoesNotExist
from django.utils.timezone import now
from sklearn import logger


def upload_to_resumes(instance, filename):
    return f'resumes/{filename}'

class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('employer', 'Employer'),
        ('employee', 'Employee'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    company_name = models.CharField(max_length=255, blank=True, null=True)  # Only for employers
    company_location = models.CharField(max_length=255, blank=True, null=True)  # Only for employers
    contact_email = models.EmailField(unique=True, blank=True, null=True)
    contact_number = models.CharField(max_length=15, unique=True)
    resume = models.FileField(upload_to='resumes/', blank=True, null=True)  # Only for employees
    skills = models.TextField(blank=True, null=True)  # Only for employees
    links = models.TextField(blank=True, null=True)  # For employee links
    experience_years = models.IntegerField(default=0)
    experience_projects = models.TextField(blank=True, null=True)  # For experience/projects
    education = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.user.username

class Job(models.Model):
    employer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="jobs")
    company_name = models.CharField(max_length=255)
    job_description = models.TextField()
    role = models.CharField(max_length=255)
    industry_type = models.CharField(max_length=255)
    department = models.CharField(max_length=255)
    employment_type = models.CharField(max_length=255)
    role_category = models.CharField(max_length=255)
    education = models.CharField(max_length=255)
    skills = models.TextField()
    experience = models.CharField(max_length=50)  # Example: '3-5 years'
    location = models.CharField(max_length=255)
    created_at = models.DateTimeField(default=now, editable=False) 

    def __str__(self):
        return f"{self.company_name} - {self.role}"


def get_default_user_profile():
    # Provide a default UserProfile for cases where one is not linked
    try:
        return UserProfile.objects.filter(role='employee').first().id
    except ObjectDoesNotExist:
        raise Exception("No default UserProfile available. Please create an employee UserProfile first.")

class JobApplication(models.Model):
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="applications")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, default=get_default_user_profile)
    resume = models.FileField(upload_to=upload_to_resumes, blank=True, null=True)
    applied_on = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.resume and self.user.userprofile.resume:
            self.resume = self.user.userprofile.resume
        elif not self.resume:
            logger.warning("No resume provided. Using default resume fallback.")
            self.resume = 'path/to/default/resume.pdf'
        super().save(*args, **kwargs)


    def __str__(self):
        return f"{self.user.get_full_name()} - {self.job.role}"
