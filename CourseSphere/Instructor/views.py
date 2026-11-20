from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import (
    InstructorRegisterForm, InstructorLoginForm,
    ForgotPasswordEmailForm, OTPVerifyForm, ResetPasswordForm,
)
from .models import Instructor
from CourseSphere.otp_service import send_otp, verify_otp, clear_otp_session


def instructor_register(request):
    if request.user.is_authenticated:
        if hasattr(request.user, 'instructor_profile'):
            return redirect('home')
        logout(request)

    if request.method == 'POST':
        form = InstructorRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Registration successful! Please login.")
            return redirect('instructor:instructor_login')
        else:
            messages.error(request, "Registration failed. Please correct the errors in the form below.")
    else:
        initial_data = {}
        if 'username' in request.GET:
            initial_data['username'] = request.GET.get('username')
        if 'email' in request.GET:
            initial_data['email'] = request.GET.get('email')
        form = InstructorRegisterForm(initial=initial_data)

    return render(request, 'Instructor/register.html', {'form': form})


def instructor_login(request):
    if request.user.is_authenticated:
        if hasattr(request.user, 'instructor_profile'):
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
                    return redirect(f"{reverse('instructor:instructor_register')}?email={username_or_email}")
                else:
                    return redirect(f"{reverse('instructor:instructor_register')}?username={username_or_email}")

        form = InstructorLoginForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data.get('user')
            login(request, user)
            messages.success(request, "Login successful! Welcome to CourseSphere.")
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('home')
        else:
            messages.error(request, "Unable to sign in. Please check your credentials.")
    else:
        form = InstructorLoginForm()

    return render(request, 'Instructor/login.html', {'form': form})


def instructor_logout(request):
    logout(request)
    messages.info(request, "You have been logged out from the Instructor Portal.")
    return redirect('instructor:instructor_login')


@login_required(login_url='instructor:instructor_login')
def instructor_dashboard(request):
    if not hasattr(request.user, 'instructor_profile'):
        messages.error(request, "Access denied. Only instructors can access the instructor dashboard.")
        return redirect('instructor:instructor_login')

    instructor = request.user.instructor_profile
    return render(request, 'Instructor/dashboard.html', {'instructor': instructor})


# ─── Forgot Password Flow ────────────────────────────────────────────────────

def instructor_forgot_password(request):
    """Step 1: Enter email → send OTP."""
    if request.method == 'POST':
        form = ForgotPasswordEmailForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            sent = send_otp(request, email, role='Instructor')
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
            return redirect('instructor:instructor_verify_otp')
    else:
        form = ForgotPasswordEmailForm()
    return render(request, 'Instructor/forgot_password.html', {'form': form})


def instructor_verify_otp(request):
    """Step 2: Enter the 6-digit OTP."""
    if not request.session.get('otp_email'):
        messages.error(request, "Session expired. Please start over.")
        return redirect('instructor:instructor_forgot_password')

    if request.method == 'POST':
        # Resend OTP button
        if 'resend' in request.POST:
            email = request.session.get('otp_email')
            if email:
                send_otp(request, email, role='Instructor')
                messages.info(request, "A new OTP has been sent.")
            return redirect('instructor:instructor_verify_otp')

        form = OTPVerifyForm(request.POST)
        if form.is_valid():
            ok, reason = verify_otp(request, form.cleaned_data['otp'])
            if ok:
                messages.success(request, "OTP verified! Set your new password below.")
                return redirect('instructor:instructor_reset_password')
            else:
                messages.error(request, reason)
    else:
        form = OTPVerifyForm()

    email = request.session.get('otp_email', '')
    return render(request, 'Instructor/verify_otp.html', {'form': form, 'email': email})


def instructor_reset_password(request):
    """Step 3: Set new password after OTP verified."""
    if not request.session.get('otp_verified'):
        messages.error(request, "Please verify your OTP first.")
        return redirect('instructor:instructor_forgot_password')

    if request.method == 'POST':
        form = ResetPasswordForm(request.POST)
        if form.is_valid():
            email = request.session.get('otp_email')
            try:
                user = User.objects.get(email__iexact=email, instructor_profile__isnull=False)
                user.set_password(form.cleaned_data['password'])
                user.save()
                clear_otp_session(request)
                messages.success(request, "Password reset successful! You can now log in with your new password.")
                return redirect('instructor:instructor_login')
            except User.DoesNotExist:
                messages.error(request, "User not found. Please start over.")
                return redirect('instructor:instructor_forgot_password')
    else:
        form = ResetPasswordForm()

    return render(request, 'Instructor/reset_password.html', {'form': form})
