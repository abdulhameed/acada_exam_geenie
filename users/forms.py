from django import forms
from django.contrib.auth.forms import UserCreationForm
from schools.models import School
# from models import CustomUser
from django.contrib.auth.forms import AuthenticationForm

from users.models import CustomUser


class SchoolForm(forms.ModelForm):
    class Meta:
        model = School
        fields = ['name', 'domain', 'address']


class CustomUserCreationForm(UserCreationForm):
    school = forms.ModelChoiceField(
        queryset=School.objects.all(),
        required=False
        )
    new_school_name = forms.CharField(max_length=200, required=False)
    new_school_domain = forms.CharField(max_length=100, required=False)
    new_school_address = forms.CharField(widget=forms.Textarea, required=False)

    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = UserCreationForm.Meta.fields + (
            'school',
            'role',
            'department'
            )

    def clean(self):
        cleaned_data = super().clean()
        school = cleaned_data.get('school')
        new_school_name = cleaned_data.get('new_school_name')

        if not school and not new_school_name:
            raise forms.ValidationError(
                "Either select an existing school or "
                "provide details for a new school."
                )

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)

        if self.cleaned_data['school']:
            user.school = self.cleaned_data['school']
        else:
            new_school = School.objects.create(
                name=self.cleaned_data['new_school_name'],
                domain=self.cleaned_data['new_school_domain'],
                address=self.cleaned_data['new_school_address']
            )
            user.school = new_school

        if commit:
            user.save()
        return user


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
