from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import StudentRegisterForm, StudentLoginForm
from .models import Student


def student_register(request):
    if request.user.is_authenticated:
        if hasattr(request.user, 'student_profile'):
            return redirect('student:student_dashboard')
        logout(request)

    if request.method == 'POST':
        form = StudentRegisterForm(request.POST)
        if form.is_valid():
            student = form.save()
            messages.success(
                request,
                f"Registration successful for {student.user.username}! You can now sign in with your credentials."
            )
            return redirect('student:student_login')
        else:
            messages.error(request, "Registration failed. Please correct the errors in the form below.")
    else:
        form = StudentRegisterForm()

    return render(request, 'Student/register.html', {'form': form})


def student_login(request):
    if request.user.is_authenticated:
        if hasattr(request.user, 'student_profile'):
            return redirect('student:student_dashboard')
        logout(request)

    if request.method == 'POST':
        form = StudentLoginForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data.get('user')
            login(request, user)
            messages.success(request, f"Welcome back, {user.first_name or user.username}!")
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('student:student_dashboard')
        else:
            messages.error(request, "Unable to sign in. Please verify your username and password.")
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
