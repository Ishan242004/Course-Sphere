from django import forms
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from .models import Student


class StudentRegisterForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter first name'
        })
    )
    last_name = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter last name'
        })
    )
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Choose a username'
        })
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'name@example.com'
        })
    )
    phone = forms.CharField(
        max_length=10,
        min_length=10,
        required=True,
        error_messages={
            'required': 'Phone number is required.',
            'min_length': 'Phone number must be exactly 10 digits.',
            'max_length': 'Phone number must be exactly 10 digits.',
        },
        widget=forms.TextInput(attrs={
            'class': 'form-control phone-input',
            'placeholder': 'Enter 10-digit mobile number',
            'maxlength': '10',
            'minlength': '10',
            'pattern': '[0-9]{10}',
            'inputmode': 'numeric',
            'oninput': "this.value = this.value.replace(/[^0-9]/g, '').slice(0, 10);"
        })
    )
    roll_number = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. STU-2026-001'
        })
    )
    password = forms.CharField(
        min_length=8,
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control password-input',
            'placeholder': 'At least 8 characters',
            'minlength': '8'
        })
    )
    confirm_password = forms.CharField(
        min_length=8,
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control confirm-password-input',
            'placeholder': 'Re-enter your password',
            'minlength': '8'
        })
    )

    class Meta:
        model = Student
        fields = ['phone', 'roll_number']

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if not username:
            raise forms.ValidationError("Username is required.")
        if len(username) < 3:
            raise forms.ValidationError("Username must be at least 3 characters long.")
        if ' ' in username:
            raise forms.ValidationError("Username cannot contain spaces.")
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("This username is already taken. Please choose another username.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip()
        if not email:
            raise forms.ValidationError("Email address is required.")
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email.lower()

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        if not phone:
            raise forms.ValidationError("Phone number is required.")
        if not phone.isdigit():
            raise forms.ValidationError("Phone number must contain digits only.")
        if len(phone) != 10:
            raise forms.ValidationError("Phone number must be exactly 10 digits.")
        if Student.objects.filter(phone=phone).exists():
            raise forms.ValidationError("This phone number is already registered.")
        return phone

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and len(password) < 8:
            self.add_error('password', "Password must be at least 8 characters long.")

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match.")
        return cleaned_data

    def save(self, commit=True):
        user = User.objects.create_user(
            username=self.cleaned_data['username'].strip(),
            email=self.cleaned_data['email'].strip().lower(),
            password=self.cleaned_data['password'],
            first_name=self.cleaned_data['first_name'].strip(),
            last_name=self.cleaned_data['last_name'].strip()
        )
        student = Student.objects.create(
            user=user,
            phone=self.cleaned_data.get('phone', '').strip(),
            roll_number=self.cleaned_data.get('roll_number', '').strip()
        )
        return student


class ForgotPasswordEmailForm(forms.Form):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your registered email',
            'autofocus': True,
        })
    )

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip()
        if not User.objects.filter(email__iexact=email, student_profile__isnull=False).exists():
            raise forms.ValidationError("No Student account found with this email address.")
        return email.lower()


class OTPVerifyForm(forms.Form):
    otp = forms.CharField(
        max_length=6,
        min_length=6,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control text-center otp-input',
            'placeholder': '• • • • • •',
            'maxlength': '6',
            'autocomplete': 'one-time-code',
            'autofocus': True,
        })
    )

    def clean_otp(self):
        otp = self.cleaned_data.get('otp', '').strip()
        if not otp.isdigit():
            raise forms.ValidationError("OTP must contain digits only.")
        return otp


class ResetPasswordForm(forms.Form):
    password = forms.CharField(
        min_length=8,
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control password-input',
            'placeholder': 'New password (at least 8 characters)',
            'minlength': '8',
            'autofocus': True,
        })
    )
    confirm_password = forms.CharField(
        min_length=8,
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control confirm-password-input',
            'placeholder': 'Re-enter new password',
            'minlength': '8',
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        if password and len(password) < 8:
            self.add_error('password', "Password must be at least 8 characters long.")
        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match.")
        return cleaned_data


class StudentLoginForm(forms.Form):
    username = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username or Email',
            'autofocus': True
        })
    )
    password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control password-input',
            'placeholder': 'Enter your password'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        username_or_email = cleaned_data.get('username')
        password = cleaned_data.get('password')

        if username_or_email and password:
            # Allow login with either username or email
            user = authenticate(username=username_or_email, password=password)
            if user is None and '@' in username_or_email:
                try:
                    user_obj = User.objects.get(email__iexact=username_or_email)
                    user = authenticate(username=user_obj.username, password=password)
                except (User.DoesNotExist, User.MultipleObjectsReturned):
                    user = None

            if user is None:
                raise forms.ValidationError("Invalid username/email or password.")

            if not user.is_active:
                raise forms.ValidationError("This account has been deactivated.")

            # Verify role is Student
            if not hasattr(user, 'student_profile'):
                if hasattr(user, 'instructor_profile'):
                    raise forms.ValidationError(
                        "This account is registered as an Instructor. Please log in via the Instructor Portal."
                    )
                else:
                    raise forms.ValidationError("No Student profile found for this user account.")

            cleaned_data['user'] = user

        return cleaned_data
