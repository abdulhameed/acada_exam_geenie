from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.contrib import admin
from .models import CustomUser, RegistrationInvite

# admin.site.register(CustomUser)


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = UserCreationForm.Meta.fields + ('school', 'role', 'department')


class CustomUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = CustomUser
        fields = UserChangeForm.Meta.fields


class CustomUserAdmin(UserAdmin):
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm
    model = CustomUser
    list_display = ['username', 'email', 'school', 'role', 'is_staff']
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('school', 'role', 'department')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('school', 'role', 'department')}),
    )


class RegistrationInviteAdmin(admin.ModelAdmin):
    list_display = ['email', 'school', 'created_at', 'is_used']
    list_filter = ['school', 'is_used', 'created_at']
    search_fields = ['email', 'school__name']
    readonly_fields = ['token', 'created_at']

admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(RegistrationInvite, RegistrationInviteAdmin)
