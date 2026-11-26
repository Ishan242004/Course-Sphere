from types import SimpleNamespace
from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone
from Instructor.models import Course, Instructor
from Student.models import Enrollment, Order, OrderItem, Student
from Student.cart_utils import VALID_COUPONS, calculate_cart_summary


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


class _BaseAdminAccountForm(forms.Form):
    """Shared user account fields and validation for Admin Student/Instructor CRUD forms."""

    password_min_length = 8

    first_name = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter first name'})
    )
    last_name = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter last name'})
    )
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Choose a unique username'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'user@example.com'})
    )
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control password-input', 'placeholder': 'Enter password'})
    )
    confirm_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control confirm-password-input', 'placeholder': 'Confirm password'})
    )
    is_active = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    def __init__(self, *args, user_instance=None, **kwargs):
        self.user_instance = user_instance
        super().__init__(*args, **kwargs)
        if user_instance is None:
            self.fields['password'].required = True
            self.fields['confirm_password'].required = True
            self.fields['password'].widget.attrs['placeholder'] = f'At least {self.password_min_length} characters'
        else:
            self.fields['password'].widget.attrs['placeholder'] = 'Leave blank to keep current password'
            self.fields['confirm_password'].widget.attrs['placeholder'] = 'Repeat new password (if changing)'

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if len(username) < 3:
            raise forms.ValidationError("Username must be at least 3 characters long.")
        if ' ' in username:
            raise forms.ValidationError("Username cannot contain spaces.")
        qs = User.objects.filter(username__iexact=username)
        if self.user_instance:
            qs = qs.exclude(pk=self.user_instance.pk)
        if qs.exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        qs = User.objects.filter(email__iexact=email)
        if self.user_instance:
            qs = qs.exclude(pk=self.user_instance.pk)
        if qs.exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password') or ''
        confirm_password = cleaned_data.get('confirm_password') or ''

        if self.user_instance is None and not password:
            self.add_error('password', "Password is required when creating an account.")

        if password or confirm_password:
            if len(password) < self.password_min_length:
                self.add_error('password', f"Password must be at least {self.password_min_length} characters long.")
            if password != confirm_password:
                self.add_error('confirm_password', "Passwords do not match.")

        return cleaned_data

    def _save_user(self) -> User:
        password = self.cleaned_data.get('password')
        if self.user_instance is None:
            return User.objects.create_user(
                username=self.cleaned_data['username'],
                email=self.cleaned_data['email'],
                password=password,
                first_name=self.cleaned_data['first_name'],
                last_name=self.cleaned_data['last_name'],
                is_active=self.cleaned_data.get('is_active', True),
            )

        user = self.user_instance
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.username = self.cleaned_data['username']
        user.email = self.cleaned_data['email']
        user.is_active = self.cleaned_data.get('is_active', True)
        if password:
            user.set_password(password)
        user.save()
        return user


class AdminStudentForm(_BaseAdminAccountForm):
    """Admin Create/Update form managing User + Student profile fields together."""

    roll_number = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. STU-2026-001'})
    )
    phone = forms.CharField(
        max_length=15,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control phone-input',
            'placeholder': '10-digit mobile number',
            'maxlength': '10',
            'inputmode': 'numeric',
        })
    )

    def __init__(self, *args, student_instance=None, **kwargs):
        self.student_instance = student_instance
        user_instance = student_instance.user if student_instance else None
        if student_instance and 'initial' not in kwargs:
            kwargs['initial'] = {
                'first_name': user_instance.first_name,
                'last_name': user_instance.last_name,
                'username': user_instance.username,
                'email': user_instance.email,
                'is_active': user_instance.is_active,
                'roll_number': student_instance.roll_number or '',
                'phone': student_instance.phone or '',
            }
        super().__init__(*args, user_instance=user_instance, **kwargs)

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        if not phone.isdigit() or len(phone) != 10:
            raise forms.ValidationError("Phone number must be exactly 10 digits.")
        qs = Student.objects.filter(phone=phone)
        if self.student_instance:
            qs = qs.exclude(pk=self.student_instance.pk)
        if qs.exists():
            raise forms.ValidationError("This phone number is already assigned to another student.")
        return phone

    def save(self) -> Student:
        with transaction.atomic():
            user = self._save_user()
            if self.student_instance is None:
                return Student.objects.create(
                    user=user,
                    phone=self.cleaned_data['phone'],
                    roll_number=self.cleaned_data['roll_number'].strip(),
                )
            student = self.student_instance
            student.phone = self.cleaned_data['phone']
            student.roll_number = self.cleaned_data['roll_number'].strip()
            student.save()
            return student


class AdminInstructorForm(_BaseAdminAccountForm):
    """Admin Create/Update form managing User + Instructor profile fields together."""

    password_min_length = 6

    phone = forms.CharField(
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 9876543210'})
    )
    specialization = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Full-Stack Web Dev, AI'})
    )
    bio = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Teaching background, expertise, and credentials...',
        })
    )

    def __init__(self, *args, instructor_instance=None, **kwargs):
        self.instructor_instance = instructor_instance
        user_instance = instructor_instance.user if instructor_instance else None
        if instructor_instance and 'initial' not in kwargs:
            kwargs['initial'] = {
                'first_name': user_instance.first_name,
                'last_name': user_instance.last_name,
                'username': user_instance.username,
                'email': user_instance.email,
                'is_active': user_instance.is_active,
                'phone': instructor_instance.phone or '',
                'specialization': instructor_instance.specialization or '',
                'bio': instructor_instance.bio or '',
            }
        super().__init__(*args, user_instance=user_instance, **kwargs)

    def save(self) -> Instructor:
        with transaction.atomic():
            user = self._save_user()
            if self.instructor_instance is None:
                return Instructor.objects.create(
                    user=user,
                    phone=self.cleaned_data.get('phone', '').strip(),
                    specialization=self.cleaned_data['specialization'].strip(),
                    bio=self.cleaned_data.get('bio', '').strip(),
                )
            instructor = self.instructor_instance
            instructor.phone = self.cleaned_data.get('phone', '').strip()
            instructor.specialization = self.cleaned_data['specialization'].strip()
            instructor.bio = self.cleaned_data.get('bio', '').strip()
            instructor.save()
            return instructor


class AdminReceiptForm(forms.Form):
    """Admin Create/Update form for Payment Receipts (Order, OrderItems, and Enrollment sync)."""

    COUPON_CHOICES = [('', 'No Promo Code')] + [
        (code, f"{code} — {info['label']}") for code, info in VALID_COUPONS.items()
    ]

    student = forms.ModelChoiceField(
        queryset=Student.objects.select_related('user').order_by('user__username'),
        required=True,
        empty_label="Select a student...",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    courses = forms.ModelMultipleChoiceField(
        queryset=Course.objects.select_related('instructor__user').order_by('course_title'),
        required=True,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        error_messages={'required': 'Select at least one course for the payment receipt.'}
    )
    coupon_code = forms.ChoiceField(
        choices=COUPON_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    payment_method = forms.ChoiceField(
        choices=Order.PAYMENT_METHOD_CHOICES,
        initial='RAZORPAY',
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    status = forms.ChoiceField(
        choices=Order.STATUS_CHOICES,
        initial='PAID',
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    razorpay_order_id = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional e.g. order_...'})
    )
    razorpay_payment_id = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional e.g. pay_...'})
    )

    def __init__(self, *args, order_instance=None, **kwargs):
        self.order_instance = order_instance
        if order_instance and 'initial' not in kwargs:
            selected_course_ids = list(
                order_instance.items.exclude(course__isnull=True).values_list('course_id', flat=True)
            )
            kwargs['initial'] = {
                'student': order_instance.student_id,
                'courses': selected_course_ids,
                'coupon_code': order_instance.coupon_code or '',
                'payment_method': order_instance.payment_method,
                'status': order_instance.status,
                'razorpay_order_id': order_instance.razorpay_order_id,
                'razorpay_payment_id': order_instance.razorpay_payment_id,
            }
        super().__init__(*args, **kwargs)

    def save(self) -> Order:
        student = self.cleaned_data['student']
        selected_courses = list(self.cleaned_data['courses'])
        coupon_code = self.cleaned_data.get('coupon_code', '')
        pseudo_items = [SimpleNamespace(course=course) for course in selected_courses]
        summary = calculate_cart_summary(pseudo_items, coupon_code=coupon_code)

        payment_method = self.cleaned_data['payment_method']
        if summary['is_free_order']:
            payment_method = 'FREE'
        status = self.cleaned_data['status']
        rzp_order_id = self.cleaned_data.get('razorpay_order_id', '').strip()
        rzp_payment_id = self.cleaned_data.get('razorpay_payment_id', '').strip()

        with transaction.atomic():
            if self.order_instance is None:
                order = Order.objects.create(
                    student=student,
                    subtotal=summary['subtotal'],
                    discount_amount=summary['discount_amount'],
                    tax_amount=summary['tax_amount'],
                    total_amount=summary['total_amount'],
                    coupon_code=summary['coupon_code'],
                    payment_method=payment_method,
                    status=status,
                    razorpay_order_id=rzp_order_id,
                    razorpay_payment_id=rzp_payment_id,
                )
            else:
                order = self.order_instance
                order.student = student
                order.subtotal = summary['subtotal']
                order.discount_amount = summary['discount_amount']
                order.tax_amount = summary['tax_amount']
                order.total_amount = summary['total_amount']
                order.coupon_code = summary['coupon_code']
                order.payment_method = payment_method
                order.status = status
                order.razorpay_order_id = rzp_order_id
                order.razorpay_payment_id = rzp_payment_id
                order.save()
                order.items.all().delete()

            for course in selected_courses:
                OrderItem.objects.create(
                    order=order,
                    course=course,
                    course_title=course.course_title,
                    price=course.price,
                )

            selected_ids = {course.id for course in selected_courses}
            payment_ref = rzp_payment_id or order.order_id
            now = timezone.now()
            if status == 'PAID':
                Enrollment.objects.filter(order=order).exclude(course_id__in=selected_ids).delete()
                for course in selected_courses:
                    existing = Enrollment.objects.filter(student=student, course=course).first()
                    if existing and existing.status in Enrollment.ACTIVE_STATUSES and existing.order_id and existing.order_id != order.id:
                        continue
                    Enrollment.objects.update_or_create(
                        student=student,
                        course=course,
                        defaults={
                            'order': order,
                            'status': 'Active',
                            'payment_reference': payment_ref,
                            'enrolled_at': now,
                        },
                    )
            else:
                Enrollment.objects.filter(order=order).delete()

        return order
