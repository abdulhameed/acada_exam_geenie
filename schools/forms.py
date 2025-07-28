from django import forms
from .models import SchoolInvite


class SchoolInviteForm(forms.ModelForm):
    class Meta:
        model = SchoolInvite
        fields = ['email', 'role']

    def __init__(self, *args, **kwargs):
        self.school = kwargs.pop('school', None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        invite = super().save(commit=False)
        invite.school = self.school
        if commit:
            invite.save()
        return invite
