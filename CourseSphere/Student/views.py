from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import StudentRegisterForm, StudentLoginForm
from .models import Student


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
