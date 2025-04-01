import os
import logging
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.timezone import now
from django.core.exceptions import ValidationError
from django.conf import settings

logger = logging.getLogger(__name__)


def certification_file_path(instance, filename):
    """
    Generate a unique file path for certification uploads
    """
    # File will be uploaded to MEDIA_ROOT/certifications/user_id/filename
    return f'certifications/{instance.user.id}/{filename}'

class EmployeeCertification(models.Model):
    """
    Model to store employee certifications
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='certifications'
    )
    
    certificate_name = models.CharField(
        max_length=255, 
        verbose_name='Certification Name'
    )
    
    issued_date = models.DateField(
        verbose_name='Certification Issued Date'
    )
    
    certificate_file = models.FileField(
        upload_to=certification_file_path,
        verbose_name='Certification Document',
        help_text='Upload PDF, JPG, or PNG',
        validators=[
            # You can add file type and size validators here
        ]
    )
    
    issuing_organization = models.CharField(
        max_length=255, 
        verbose_name='Issuing Organization', 
        blank=True, 
        null=True
    )
    
    description = models.TextField(
        verbose_name='Certification Description', 
        blank=True, 
        null=True
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.certificate_name} - {self.user.username}"
    
    class Meta:
        verbose_name = 'Employee Certification'
        verbose_name_plural = 'Employee Certifications'
        ordering = ['-issued_date']


# Function to upload resumes dynamically
def upload_to_resumes(instance, filename):
    return os.path.join('resumes/', f"{instance.user.id}_{now().strftime('%Y%m%d%H%M%S')}_{filename}")

# Custom User Manager
class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        """Create and return a regular user with an email."""
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and return a superuser with is_staff and is_superuser set to True."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)

# User Model (Replaces Django's default User)
class User(AbstractUser):
    username = None  # Disable username
    email = models.EmailField(unique=True)  # Use email for login

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []  # No username required

    objects = CustomUserManager()  # Use custom user manager

    def __str__(self):
        return self.email

# User Profile Model
class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('employer', 'Employer'),
        ('employee', 'Employee'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='userprofile')
    full_name = models.CharField(max_length=255, default="Unknown")
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    company_name = models.CharField(max_length=255, blank=True, null=True)
    company_location = models.CharField(max_length=255, blank=True, null=True)
    contact_email = models.EmailField(unique=True, blank=True, null=True)
    contact_number = models.CharField(max_length=15, unique=True)
    resume = models.FileField(upload_to=upload_to_resumes, blank=True, null=True)
    skills = models.TextField(blank=True, null=True)
    links = models.TextField(blank=True, null=True)
    experience_years = models.IntegerField(default=0)
    experience_projects = models.TextField(blank=True, null=True)
    education = models.TextField(blank=True, null=True)
    testimonials = models.TextField(blank=True, null=True)
    preferred_location = models.CharField(max_length=255, blank=True, null=True)
    expected_salary = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return f"{self.full_name} ({self.role})"

# Job Model
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

# Job Application Model
class JobApplication(models.Model):
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="applications")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='job_applications')
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='applications')
    resume = models.FileField(upload_to=upload_to_resumes, blank=True, null=True)
    applied_on = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        """Ensure resume is assigned if not uploaded."""
        if not self.resume and self.user.userprofile.resume:
            self.resume = self.user.userprofile.resume
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.email} - {self.job.role}"
