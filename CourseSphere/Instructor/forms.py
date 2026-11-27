from django import forms
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from .models import Instructor


class InstructorRegisterForm(forms.ModelForm):
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
            'placeholder': 'instructor@example.com'
        })
    )
    phone = forms.CharField(
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+1 234 567 8900'
        })
    )
    specialization = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. Full-Stack Web Dev, Machine Learning'
        })
    )
    bio = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Briefly describe your teaching background or expertise...'
        })
    )
    password = forms.CharField(
        min_length=6,
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control password-input',
            'placeholder': 'At least 6 characters'
        })
    )
    confirm_password = forms.CharField(
        min_length=6,
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control confirm-password-input',
            'placeholder': 'Re-enter your password'
        })
    )

    class Meta:
        model = Instructor
        fields = ['phone', 'specialization', 'bio']

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("This username is already taken. Please choose another.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match.")
        return cleaned_data

    def save(self, commit=True):
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            email=self.cleaned_data['email'],
            password=self.cleaned_data['password'],
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data['last_name']
        )
        instructor = Instructor.objects.create(
            user=user,
            phone=self.cleaned_data.get('phone', ''),
            specialization=self.cleaned_data.get('specialization', ''),
            bio=self.cleaned_data.get('bio', '')
        )
        return instructor


class InstructorLoginForm(forms.Form):
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

            # Verify role is Instructor
            if not hasattr(user, 'instructor_profile'):
                if hasattr(user, 'student_profile'):
                    raise forms.ValidationError(
                        "This account is registered as a Student. Please log in via the Student Portal."
                    )
                else:
                    raise forms.ValidationError("No Instructor profile found for this user account.")

            cleaned_data['user'] = user

        return cleaned_data


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
        if not User.objects.filter(email__iexact=email, instructor_profile__isnull=False).exists():
            raise forms.ValidationError("No Instructor account found with this email address.")
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
        min_length=6,
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control password-input',
            'placeholder': 'New password (at least 6 characters)',
            'autofocus': True,
        })
    )
    confirm_password = forms.CharField(
        min_length=6,
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control confirm-password-input',
            'placeholder': 'Re-enter new password',
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match.")
        return cleaned_data


from .models import Course


class InstructorCourseForm(forms.ModelForm):
    """Form allowing an instructor to create or update only their own courses."""

    course_title = forms.CharField(
        max_length=200,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. Modern Python & Django Engineering',
        })
    )
    category = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. Programming, Design, Business, AI',
        })
    )
    price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=True,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '0.00 (Enter 0 for Free)',
            'step': '0.01',
        })
    )
    status = forms.ChoiceField(
        choices=Course.STATUS_CHOICES,
        initial='Published',
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    description = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Course syllabus, key outcomes, and target audience (min 10 chars)...',
        })
    )
    course_image = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*',
        })
    )

    class Meta:
        model = Course
        fields = ['course_title', 'category', 'price', 'status', 'description', 'course_image']

    def clean_course_title(self):
        title = (self.cleaned_data.get('course_title') or '').strip()
        if len(title) < 3:
            raise forms.ValidationError("Course title must be at least 3 characters long.")
        return title

    def clean_category(self):
        category = (self.cleaned_data.get('category') or '').strip()
        if len(category) < 2:
            raise forms.ValidationError("Category must be at least 2 characters long.")
        return category

    def clean_description(self):
        desc = (self.cleaned_data.get('description') or '').strip()
        if len(desc) < 10:
            raise forms.ValidationError("Description must be at least 10 characters long.")
        return desc


class InstructorProfileForm(forms.Form):
    """Profile update form for the authenticated Instructor."""

    first_name = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First name'})
    )
    last_name = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last name'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'instructor@example.com'})
    )
    phone = forms.CharField(
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+91 9876543210'})
    )
    specialization = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Full-Stack Web Dev'})
    )
    bio = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Share your expertise and teaching philosophy...',
        })
    )

    def __init__(self, *args, instructor=None, **kwargs):
        self.instructor = instructor
        if instructor and 'initial' not in kwargs:
            kwargs['initial'] = {
                'first_name': instructor.user.first_name,
                'last_name': instructor.user.last_name,
                'email': instructor.user.email,
                'phone': instructor.phone or '',
                'specialization': instructor.specialization or '',
                'bio': instructor.bio or '',
            }
        super().__init__(*args, **kwargs)

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        qs = User.objects.filter(email__iexact=email)
        if self.instructor:
            qs = qs.exclude(pk=self.instructor.user_id)
        if qs.exists():
            raise forms.ValidationError("Another account already uses this email address.")
        return email

    def save(self) -> Instructor:
        user = self.instructor.user
        user.first_name = self.cleaned_data['first_name'].strip()
        user.last_name = self.cleaned_data['last_name'].strip()
        user.email = self.cleaned_data['email']
        user.save(update_fields=['first_name', 'last_name', 'email'])

        self.instructor.phone = self.cleaned_data.get('phone', '').strip()
        self.instructor.specialization = self.cleaned_data['specialization'].strip()
        self.instructor.bio = self.cleaned_data.get('bio', '').strip()
        self.instructor.save(update_fields=['phone', 'specialization', 'bio'])
        return self.instructor
