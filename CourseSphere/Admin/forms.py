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


from Instructor.models import Course, Instructor


class CourseForm(forms.ModelForm):
    course_title = forms.CharField(
        max_length=200,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. Master Full-Stack Web Development Bootcamp',
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
            'placeholder': '0.00 (Enter 0 for Free course)',
            'step': '0.01',
        })
    )
    description = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Detailed course overview, learning outcomes, and requirements...',
        })
    )
    course_image = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*',
        })
    )
    instructor = forms.ModelChoiceField(
        queryset=Instructor.objects.select_related('user').all(),
        required=False,
        empty_label="CourseSphere Faculty (Unassigned)",
        widget=forms.Select(attrs={
            'class': 'form-select',
        })
    )

    class Meta:
        model = Course
        fields = ['course_title', 'category', 'price', 'description', 'course_image', 'instructor']

