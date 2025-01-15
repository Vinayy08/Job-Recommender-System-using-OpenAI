from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import UserProfile, Job, JobApplication


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


class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    role = forms.ChoiceField(choices=UserProfile.ROLE_CHOICES)

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already in use.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user



class EmployerRegistrationForm(forms.ModelForm):
    company_name = forms.CharField(required=True)
    company_location = forms.CharField(required=True)
    contact_number = forms.CharField(required=True)
    password = forms.CharField(widget=forms.PasswordInput, required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def clean_contact_number(self):
        """
        Ensure the contact number is unique in the UserProfile model.
        """
        contact_number = self.cleaned_data.get('contact_number')
        if UserProfile.objects.filter(contact_number=contact_number).exists():
            raise ValidationError("This contact number is already registered.")
        return contact_number

    def clean_email(self):
        """
        Ensure the email is unique.
        """
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("This email is already registered.")
        return email

    def save(self, commit=True):
        """
        Override the save method to create a UserProfile for the employer.
        """
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])

        if commit:
            user.save()

            UserProfile.objects.create(
                user=user,
                role='employer',  # Automatically set the role as 'employer'
                company_name=self.cleaned_data['company_name'],
                company_location=self.cleaned_data['company_location'],
                contact_number=self.cleaned_data['contact_number'],
                contact_email=self.cleaned_data['email'],
            )
        return user


class EmployeeRegistrationForm(forms.ModelForm):
    contact_number = forms.CharField(
        max_length=15,
        required=True,
        help_text="Enter your contact number (e.g., +123456789)."
    )
    resume = forms.FileField(
        required=True,
        help_text="Upload your resume in PDF or DOCX format."
    )
    password = forms.CharField(
        widget=forms.PasswordInput,
        help_text="Enter a secure password."
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def clean_contact_number(self):
        """
        Ensure the contact number is unique in the UserProfile model.
        """
        contact_number = self.cleaned_data.get('contact_number')
        if UserProfile.objects.filter(contact_number=contact_number).exists():
            raise ValidationError("This contact number is already registered.")
        return contact_number

    def save(self, commit=True):
        """
        Override the save method to handle the creation of the related UserProfile.
        """
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])

        if commit:
            user.save()

            # Save the UserProfile details
            UserProfile.objects.create(
                user=user,
                role='employee',
                contact_number=self.cleaned_data['contact_number'],
                resume=self.cleaned_data['resume'],
            )
        return user
    


class EmployerProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['company_name', 'company_location', 'contact_email', 'contact_number']

    def __init__(self, *args, **kwargs):
        self.user_instance = kwargs.pop('user_instance', None)
        super().__init__(*args, **kwargs)

        # Example: Modify field attributes if needed
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'

class EmployeeProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['skills', 'education', 'experience_projects', 'resume']

class LoginForm(forms.Form):
    username = forms.CharField(label="Username", max_length=150)
    password = forms.CharField(label="Password", widget=forms.PasswordInput)