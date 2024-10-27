from django import forms
from django.contrib.auth.forms import UserCreationForm
from schools.models import School
# from models import CustomUser
from django.contrib.auth.forms import AuthenticationForm
from captcha.fields import CaptchaField
from users.models import CustomUser


class SchoolForm(forms.ModelForm):
    class Meta:
        model = School
        fields = ['name', 'domain', 'address']


class CustomUserCreationForm(UserCreationForm):
    new_school_name = forms.CharField(
        max_length=200,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='School Name'
    )
    new_school_domain = forms.CharField(
        max_length=100, 
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='School Domain'
    )
    new_school_address = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control'}),
        required=True,
        label='School Address'
    )
    captcha = CaptchaField(
        label='Security Check',
        error_messages={'invalid': 'Invalid captcha - try again'}
    )

    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = UserCreationForm.Meta.fields + (
            'email',
            'department',
            )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove the school field since we're creating a new school
        if 'school' in self.fields:
            del self.fields['school']

        # Set role field to hidden and default to school_admin
        if 'role' in self.fields:
            del self.fields['role']

        # Reorder fields by creating a new ordered dictionary
        field_order = [
            'username',
            'email',
            'department',
            'new_school_name',
            'new_school_domain',
            'new_school_address',
            'password1',
            'password2',
            'captcha'
        ]

        # Create new ordered dictionary
        new_fields = {}
        for key in field_order:
            new_fields[key] = self.fields[key]
        self.fields = new_fields

        # Add bootstrap classes to all fields
        for field in self.fields:
            if field != 'captcha':
                self.fields[field].widget.attrs.update({'class': 'form-control'})

    def clean(self):
        cleaned_data = super().clean()
        # Validate school-related fields
        if not cleaned_data.get('new_school_name'):
            raise forms.ValidationError("School name is required")
        if not cleaned_data.get('new_school_domain'):
            raise forms.ValidationError("School domain is required")
        if not cleaned_data.get('new_school_address'):
            raise forms.ValidationError("School address is required")
        return cleaned_data


class CustomLoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Username'
            }
        )
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Password'
            }
        )
    )


class StudentRegistrationForm(forms.ModelForm):
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Confirm Password', widget=forms.PasswordInput)

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'first_name', 'last_name', 'department']

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2
