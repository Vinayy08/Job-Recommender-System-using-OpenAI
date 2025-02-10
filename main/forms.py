from django import forms
from django.core.exceptions import ValidationError
from django.conf import settings
from .models import UserProfile, Job, JobApplication
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate

User = get_user_model()  # Ensuring the correct user model is used


class CSVUploadForm(forms.Form):
    csv_file = forms.FileField()


class JobApplicationForm(forms.ModelForm):
    class Meta:
        model = JobApplication
        fields = ['resume']

    def clean_resume(self):
        resume = self.cleaned_data.get('resume')
        if not resume:
            raise forms.ValidationError("Please upload your resume.")
        if not resume.name.endswith(('.pdf', '.docx')):
            raise forms.ValidationError("Resume must be in PDF or DOCX format.")
        return resume


class JobForm(forms.ModelForm):
    class Meta:
        model = Job
        fields = '__all__'
        exclude = ['employer']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'


class BaseRegistrationForm(forms.ModelForm):
    full_name = forms.CharField(
        max_length=255, required=True, help_text="Enter your full name."
    )
    contact_number = forms.CharField(
        max_length=15, required=True, help_text="Enter your contact number."
    )
    password = forms.CharField(
        widget=forms.PasswordInput, required=True, help_text="Enter a secure password."
    )
    email = forms.EmailField(required=True, help_text="Email address will be used for login.")

    class Meta:
        model = User
        fields = ['email', 'password']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
        self.fields['password'].widget.attrs.update({'class': 'form-control'})

    def clean_contact_number(self):
        contact_number = self.cleaned_data.get('contact_number')
        if UserProfile.objects.filter(contact_number=contact_number).exists():
            raise ValidationError("This contact number is already registered.")
        return contact_number

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("This email is already registered.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


class EmployerRegistrationForm(BaseRegistrationForm):
    company_name = forms.CharField(required=True)
    company_location = forms.CharField(required=True)

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    'full_name': self.cleaned_data['full_name'],
                    'role': 'employer',
                    'company_name': self.cleaned_data['company_name'],
                    'company_location': self.cleaned_data['company_location'],
                    'contact_number': self.cleaned_data['contact_number'],
                    'contact_email': self.cleaned_data['email'],
                }
            )
        return user


class EmployeeRegistrationForm(BaseRegistrationForm):
    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    'full_name': self.cleaned_data['full_name'],
                    'role': 'employee',
                    'contact_number': self.cleaned_data['contact_number'],
                }
            )
        return user


class EmployerProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['company_name', 'company_location', 'contact_email', 'contact_number']

    def __init__(self, *args, **kwargs):
        self.user_instance = kwargs.pop('user_instance', None)
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'


class EmployeeProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['skills', 'education', 'experience_projects', 'resume']



class LoginForm(forms.Form):
    email = forms.EmailField(label="Email", max_length=254)
    password = forms.CharField(label="Password", widget=forms.PasswordInput)

    def clean(self):
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')
        if email and password:
            user = authenticate(username=email, password=password)
            if user is None:
                raise forms.ValidationError("Invalid email or password.")
        return self.cleaned_data

