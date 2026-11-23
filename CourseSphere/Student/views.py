from decimal import Decimal, InvalidOperation
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .forms import (
    StudentRegisterForm, StudentLoginForm,
    ForgotPasswordEmailForm, OTPVerifyForm, ResetPasswordForm,
)
from .models import Student
from Instructor.models import Course
from CourseSphere.otp_service import send_otp, verify_otp, clear_otp_session


def student_register(request):
    if request.user.is_authenticated:
        if hasattr(request.user, 'student_profile'):
            return redirect('home')
        logout(request)

    if request.method == 'POST':
        form = StudentRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Registration successful! Please login.")
            return redirect('student:student_login')
        else:
            messages.error(request, "Registration failed. Please correct the errors in the form below.")
    else:
        initial_data = {}
        if 'username' in request.GET:
            initial_data['username'] = request.GET.get('username')
        if 'email' in request.GET:
            initial_data['email'] = request.GET.get('email')
        form = StudentRegisterForm(initial=initial_data)

    return render(request, 'Student/register.html', {'form': form})


def student_login(request):
    if request.user.is_authenticated:
        if hasattr(request.user, 'student_profile'):
            return redirect('home')
        logout(request)

    if request.method == 'POST':
        username_or_email = request.POST.get('username', '').strip()

        # If user does not exist, redirect directly to registration page with a simple message
        if username_or_email:
            user_exists = User.objects.filter(username__iexact=username_or_email).exists() or \
                          User.objects.filter(email__iexact=username_or_email).exists()
            if not user_exists:
                messages.info(request, "Account not found. Please register first.")
                if '@' in username_or_email:
                    return redirect(f"{reverse('student:student_register')}?email={username_or_email}")
                else:
                    return redirect(f"{reverse('student:student_register')}?username={username_or_email}")

        form = StudentLoginForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data.get('user')
            login(request, user)
            messages.success(request, "Login successful! Welcome to CourseSphere.")
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('home')
        else:
            messages.error(request, "Unable to sign in. Please verify your credentials.")
    else:
        form = StudentLoginForm()

    return render(request, 'Student/login.html', {'form': form})


def student_logout(request):
    logout(request)
    messages.info(request, "You have been logged out successfully.")
    return redirect('student:student_login')


@login_required(login_url='student:student_login')
def student_dashboard(request):
    if not hasattr(request.user, 'student_profile'):
        messages.error(request, "Access denied. Only registered students can access this area.")
        return redirect('student:student_login')

    student = request.user.student_profile
    return render(request, 'Student/dashboard.html', {'student': student})


# ─── Forgot Password Flow ────────────────────────────────────────────────────

def student_forgot_password(request):
    """Step 1: Enter email → send OTP."""
    if request.method == 'POST':
        form = ForgotPasswordEmailForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            sent = send_otp(request, email, role='Student')
            if sent:
                messages.success(
                    request,
                    f"OTP sent to {email}. Check your inbox (or the terminal if running locally)."
                )
            else:
                messages.warning(
                    request,
                    "Could not send email — OTP printed in the server terminal instead."
                )
            return redirect('student:student_verify_otp')
    else:
        form = ForgotPasswordEmailForm()
    return render(request, 'Student/forgot_password.html', {'form': form})


def student_verify_otp(request):
    """Step 2: Enter the 6-digit OTP."""
    if not request.session.get('otp_email'):
        messages.error(request, "Session expired. Please start over.")
        return redirect('student:student_forgot_password')

    if request.method == 'POST':
        # Resend OTP button
        if 'resend' in request.POST:
            email = request.session.get('otp_email')
            if email:
                send_otp(request, email, role='Student')
                messages.info(request, "A new OTP has been sent.")
            return redirect('student:student_verify_otp')

        form = OTPVerifyForm(request.POST)
        if form.is_valid():
            ok, reason = verify_otp(request, form.cleaned_data['otp'])
            if ok:
                messages.success(request, "OTP verified! Set your new password below.")
                return redirect('student:student_reset_password')
            else:
                messages.error(request, reason)
    else:
        form = OTPVerifyForm()

    email = request.session.get('otp_email', '')
    return render(request, 'Student/verify_otp.html', {'form': form, 'email': email})


def student_reset_password(request):
    """Step 3: Set new password after OTP verified."""
    if not request.session.get('otp_verified'):
        messages.error(request, "Please verify your OTP first.")
        return redirect('student:student_forgot_password')

    if request.method == 'POST':
        form = ResetPasswordForm(request.POST)
        if form.is_valid():
            email = request.session.get('otp_email')
            try:
                user = User.objects.get(email__iexact=email, student_profile__isnull=False)
                user.set_password(form.cleaned_data['password'])
                user.save()
                clear_otp_session(request)
                messages.success(request, "Password reset successful! You can now log in with your new password.")
                return redirect('student:student_login')
            except User.DoesNotExist:
                messages.error(request, "User not found. Please start over.")
                return redirect('student:student_forgot_password')
    else:
        form = ResetPasswordForm()

    return render(request, 'Student/reset_password.html', {'form': form})


# ─── Course Listing & Detail Views ──────────────────────────────────────────

def course_list(request):
    """
    Display all available courses dynamically from the database.
    Supports title and keyword search, category filtering, price filtering,
    and pagination (with query parameter preservation across page changes).
    """
    courses = Course.objects.all().order_by('-created_date')

    search_query = request.GET.get('q', '').strip()
    selected_category = request.GET.get('category', '').strip()
    selected_price = request.GET.get('price', request.GET.get('price_filter', '')).strip()
    min_price = request.GET.get('min_price', '').strip()
    max_price = request.GET.get('max_price', '').strip()

    # Search by title (and description for comprehensive discovery)
    if search_query:
        courses = courses.filter(
            Q(course_title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(category__icontains=search_query)
        )

    # Filter by category
    if selected_category:
        courses = courses.filter(category__iexact=selected_category)

    # Filter by price
    if selected_price:
        sp_lower = selected_price.lower()
        if sp_lower in ['free', '0']:
            courses = courses.filter(price=Decimal('0.00'))
        elif sp_lower == 'paid':
            courses = courses.filter(price__gt=Decimal('0.00'))
        elif sp_lower in ['under-50', '0-50', 'under_50']:
            courses = courses.filter(price__gt=Decimal('0.00'), price__lte=Decimal('50.00'))
        elif sp_lower in ['50-100', '50_100']:
            courses = courses.filter(price__gte=Decimal('50.00'), price__lte=Decimal('100.00'))
        elif sp_lower in ['over-100', '100+', '100-plus', '100_plus']:
            courses = courses.filter(price__gt=Decimal('100.00'))
        else:
            try:
                numeric_val = Decimal(selected_price)
                courses = courses.filter(price=numeric_val)
            except (InvalidOperation, ValueError):
                pass

    if min_price:
        try:
            courses = courses.filter(price__gte=Decimal(min_price))
        except (InvalidOperation, ValueError):
            pass

    if max_price:
        try:
            courses = courses.filter(price__lte=Decimal(max_price))
        except (InvalidOperation, ValueError):
            pass

    # Get distinct categories from database for filter dropdown and pills
    categories = Course.objects.values_list('category', flat=True).distinct().order_by('category')

    total_matching_courses = courses.count()

    # Pagination: 6 courses per page (configurable via per_page param)
    per_page = request.GET.get('per_page', 6)
    try:
        per_page = int(per_page)
        if per_page <= 0:
            per_page = 6
    except (ValueError, TypeError):
        per_page = 6

    paginator = Paginator(courses, per_page)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # Preserve search and filter values during pagination
    query_params = request.GET.copy()
    if 'page' in query_params:
        del query_params['page']
    extra_query = query_params.urlencode()

    context = {
        'page_obj': page_obj,
        'courses': page_obj,  # Iterable of courses on current page
        'paginator': paginator,
        'is_paginated': page_obj.has_other_pages(),
        'categories': categories,
        'search_query': search_query,
        'selected_category': selected_category,
        'selected_price': selected_price,
        'min_price': min_price,
        'max_price': max_price,
        'total_courses': total_matching_courses,
        'extra_query': extra_query,
    }
    return render(request, 'Student/course_list.html', context)


def course_detail(request, course_id):
    """
    Display detailed information for a single course.
    """
    course = get_object_or_404(Course, id=course_id)
    return render(request, 'Student/course_detail.html', {'course': course})

