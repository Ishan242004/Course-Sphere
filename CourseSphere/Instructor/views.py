from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import InstructorRegisterForm, InstructorLoginForm
from .models import Instructor


def instructor_register(request):
    if request.user.is_authenticated:
        if hasattr(request.user, 'instructor_profile'):
            return redirect('instructor:instructor_dashboard')
        logout(request)

    if request.method == 'POST':
        form = InstructorRegisterForm(request.POST)
        if form.is_valid():
            instructor = form.save()
            messages.success(
                request,
                f"Welcome Professor/Instructor {instructor.user.username}! Your account has been created. Please sign in."
            )
            return redirect('instructor:instructor_login')
        else:
            messages.error(request, "Registration failed. Please correct the errors in the form below.")
    else:
        form = InstructorRegisterForm()

    return render(request, 'Instructor/register.html', {'form': form})


def instructor_login(request):
    if request.user.is_authenticated:
        if hasattr(request.user, 'instructor_profile'):
            return redirect('instructor:instructor_dashboard')
        logout(request)

    if request.method == 'POST':
        form = InstructorLoginForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data.get('user')
            login(request, user)
            messages.success(request, f"Welcome back, Instructor {user.first_name or user.username}!")
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('instructor:instructor_dashboard')
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
