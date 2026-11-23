from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from .forms import AdminLoginForm, CourseForm
from .models import Admin
from Student.models import Student
from Instructor.models import Instructor, Course


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

    stats = {
        'total_students': Student.objects.count(),
        'total_instructors': Instructor.objects.count(),
        'total_courses': Course.objects.count(),
        'recent_courses': Course.objects.all().order_by('-created_date')[:15],
    }
    course_form = CourseForm()
    return render(request, 'Admin/dashboard.html', {
        'stats': stats,
        'course_form': course_form,
    })


@login_required(login_url='admin_portal:admin_login')
def course_list(request):
    user = request.user
    if not (user.is_superuser or user.is_staff or hasattr(user, 'admin_profile')):
        messages.error(request, "Access denied. Administrator privileges required.")
        return redirect('admin_portal:admin_login')

    courses = Course.objects.all().order_by('-created_date')
    search_query = request.GET.get('q', '').strip()
    selected_category = request.GET.get('category', '').strip()

    if search_query:
        courses = courses.filter(
            Q(course_title__icontains=search_query) |
            Q(category__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    if selected_category:
        courses = courses.filter(category__iexact=selected_category)

    categories = Course.objects.values_list('category', flat=True).distinct().order_by('category')
    total_courses = courses.count()

    paginator = Paginator(courses, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    query_params = request.GET.copy()
    if 'page' in query_params:
        del query_params['page']
    extra_query = query_params.urlencode()

    return render(request, 'Admin/course_list.html', {
        'courses': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'is_paginated': page_obj.has_other_pages(),
        'categories': categories,
        'search_query': search_query,
        'selected_category': selected_category,
        'total_courses': total_courses,
        'extra_query': extra_query,
    })



@login_required(login_url='admin_portal:admin_login')
def add_course(request):
    user = request.user
    if not (user.is_superuser or user.is_staff or hasattr(user, 'admin_profile')):
        messages.error(request, "Access denied. Administrator privileges required.")
        return redirect('admin_portal:admin_login')

    if request.method == 'POST':
        form = CourseForm(request.POST, request.FILES)
        if form.is_valid():
            course = form.save()
            messages.success(request, f"Course '{course.course_title}' has been successfully created!")
            return redirect('admin_portal:admin_dashboard')
        else:
            messages.error(request, "Please correct the errors in the course form below.")
    else:
        form = CourseForm()

    return render(request, 'Admin/course_form.html', {
        'form': form,
        'action_title': 'Add New Course',
        'button_text': 'Create Course',
    })


@login_required(login_url='admin_portal:admin_login')
def edit_course(request, course_id):
    user = request.user
    if not (user.is_superuser or user.is_staff or hasattr(user, 'admin_profile')):
        messages.error(request, "Access denied. Administrator privileges required.")
        return redirect('admin_portal:admin_login')

    course = get_object_or_404(Course, id=course_id)

    if request.method == 'POST':
        form = CourseForm(request.POST, request.FILES, instance=course)
        if form.is_valid():
            course = form.save()
            messages.success(request, f"Course '{course.course_title}' has been updated successfully!")
            return redirect('admin_portal:admin_dashboard')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = CourseForm(instance=course)

    return render(request, 'Admin/course_form.html', {
        'form': form,
        'course': course,
        'action_title': f"Edit Course: {course.course_title}",
        'button_text': 'Save Changes',
    })


@login_required(login_url='admin_portal:admin_login')
def delete_course(request, course_id):
    user = request.user
    if not (user.is_superuser or user.is_staff or hasattr(user, 'admin_profile')):
        messages.error(request, "Access denied. Administrator privileges required.")
        return redirect('admin_portal:admin_login')

    course = get_object_or_404(Course, id=course_id)
    if request.method == 'POST':
        title = course.course_title
        course.delete()
        messages.success(request, f"Course '{title}' has been permanently deleted.")
    return redirect('admin_portal:admin_dashboard')
