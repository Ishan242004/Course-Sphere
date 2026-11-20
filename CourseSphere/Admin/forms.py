from django import forms
from django.contrib.auth.models import User
from django.contrib.auth import authenticate


class AdminLoginForm(forms.Form):
    username = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username or Email',
            'autofocus': True,
        })
    )
    password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control password-input',
            'placeholder': 'Enter your password',
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        username_or_email = cleaned_data.get('username', '').strip()
        password = cleaned_data.get('password')

        if username_or_email and password:
            user = authenticate(username=username_or_email, password=password)
            if user is None and '@' in username_or_email:
                try:
                    user_obj = User.objects.get(email__iexact=username_or_email)
                    user = authenticate(username=user_obj.username, password=password)
                except (User.DoesNotExist, User.MultipleObjectsReturned):
                    user = None

            if user is None:
                raise forms.ValidationError("Invalid admin username/email or password.")

            if not user.is_active:
                raise forms.ValidationError("This administrator account has been deactivated.")

            # Check if user has admin privileges
            is_admin = user.is_superuser or user.is_staff or hasattr(user, 'admin_profile')
            if not is_admin:
                if hasattr(user, 'student_profile'):
                    raise forms.ValidationError(
                        "This account is registered as a Student. Please use the Student Login portal."
                    )
                elif hasattr(user, 'instructor_profile'):
                    raise forms.ValidationError(
                        "This account is registered as an Instructor. Please use the Instructor Login portal."
                    )
                else:
                    raise forms.ValidationError("Access denied. Administrator privileges required.")

            cleaned_data['user'] = user

        return cleaned_data
