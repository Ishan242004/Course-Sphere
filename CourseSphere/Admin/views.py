from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import AdminLoginForm
from .models import Admin


def admin_login(request):
    if request.user.is_authenticated:
        if request.user.is_superuser or request.user.is_staff or hasattr(request.user, 'admin_profile'):
            return redirect('admin_portal:admin_dashboard')
        logout(request)

    if request.method == 'POST':
        form = AdminLoginForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data.get('user')
            login(request, user)
            messages.success(request, f"Welcome to CourseSphere Admin Cockpit, {user.username}!")
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('admin_portal:admin_dashboard')
        else:
            messages.error(request, "Unable to sign in. Please verify your admin credentials.")
    else:
        form = AdminLoginForm()

    return render(request, 'Admin/admin_login.html', {'form': form})


def admin_logout(request):
    logout(request)
    messages.info(request, "You have been logged out from the Administrator Portal.")
    return redirect('admin_portal:admin_login')


@login_required(login_url='admin_portal:admin_login')
def admin_dashboard(request):
    user = request.user
    if not (user.is_superuser or user.is_staff or hasattr(user, 'admin_profile')):
        messages.error(request, "Access denied. Only administrators can access the admin dashboard.")
        return redirect('admin_portal:admin_login')

    from Student.models import Student
    from Instructor.models import Instructor, Course

    stats = {
        'total_students': Student.objects.count(),
        'total_instructors': Instructor.objects.count(),
        'total_courses': Course.objects.count(),
        'recent_courses': Course.objects.all().order_by('-created_date')[:5],
    }
    return render(request, 'Admin/dashboard.html', {'stats': stats})
