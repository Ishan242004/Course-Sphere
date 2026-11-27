from decimal import Decimal
from functools import wraps
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Avg, Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from CourseSphere.otp_service import clear_otp_session, send_otp, verify_otp
from Student.models import Cart, Enrollment, OrderItem
from .forms import (
    ForgotPasswordEmailForm,
    InstructorCourseForm,
    InstructorLoginForm,
    InstructorProfileForm,
    InstructorRegisterForm,
    OTPVerifyForm,
    ResetPasswordForm,
)
from .models import Course, Instructor


def instructor_required(view_func):
    """Allow access strictly to authenticated users holding an Instructor profile."""
    @login_required(login_url='instructor:instructor_login')
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not hasattr(request.user, 'instructor_profile'):
            messages.error(request, "Access denied. Only instructors can access the instructor portal.")
            return redirect('instructor:instructor_login')
        return view_func(request, *args, **kwargs)
    return _wrapped


def _paginate_queryset(request, queryset, per_page=8):
    paginator = Paginator(queryset, per_page)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    query_params = request.GET.copy()
    query_params.pop('page', None)
    return page_obj, paginator, query_params.urlencode()


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


# ─── Instructor Dashboard & Owned Course Management ──────────────────────────

@instructor_required
def instructor_dashboard(request):
    """Main Instructor Dashboard showing real DB metrics, profile overview, and owned courses."""
    instructor = request.user.instructor_profile
    active_filter = Q(enrollments__status__in=Enrollment.ACTIVE_STATUSES)

    my_courses = (
        Course.objects.filter(instructor=instructor)
        .annotate(enrolled_students=Count('enrollments', filter=active_filter, distinct=True))
        .order_by('-created_date')
    )

    total_courses = my_courses.count()
    published_courses = my_courses.filter(status='Published').count()
    draft_courses = my_courses.filter(status='Draft').count()
    paid_courses = my_courses.filter(price__gt=Decimal('0.00')).count()
    free_courses = my_courses.filter(price=Decimal('0.00')).count()
    avg_price = (my_courses.aggregate(avg=Avg('price'))['avg'] or Decimal('0.00')).quantize(Decimal('0.01'))

    active_enrollments = Enrollment.objects.filter(
        course__instructor=instructor,
        status__in=Enrollment.ACTIVE_STATUSES,
    )
    total_enrollments = active_enrollments.count()
    unique_students = active_enrollments.values('student_id').distinct().count()
    recent_enrollments = active_enrollments.select_related('student__user', 'course').order_by('-enrolled_at')[:5]

    total_revenue = (
        OrderItem.objects.filter(course__instructor=instructor, order__status='PAID')
        .aggregate(total=Sum('price'))['total']
        or Decimal('0.00')
    )

    category_rows = list(
        Course.objects.filter(instructor=instructor)
        .values('category')
        .annotate(
            course_count=Count('id', distinct=True),
            enrolled_count=Count('enrollments', filter=active_filter, distinct=True),
        )
        .order_by('-course_count', 'category')
    )
    category_stats = [
        {
            'category': row['category'],
            'course_count': row['course_count'],
            'enrolled_count': row['enrolled_count'],
            'percent': round((row['course_count'] * 100) / total_courses) if total_courses else 0,
        }
        for row in category_rows
    ]

    top_course = my_courses.order_by('-enrolled_students', '-created_date').first()

    stats = {
        'total_courses': total_courses,
        'published_courses': published_courses,
        'draft_courses': draft_courses,
        'paid_courses': paid_courses,
        'free_courses': free_courses,
        'avg_price': avg_price,
        'total_enrollments': total_enrollments,
        'unique_students': unique_students,
        'total_revenue': total_revenue,
        'categories_count': len(category_stats),
        'top_course': top_course,
    }

    return render(request, 'Instructor/dashboard.html', {
        'instructor': instructor,
        'stats': stats,
        'courses': my_courses[:8],
        'category_stats': category_stats,
        'recent_enrollments': recent_enrollments,
    })


@instructor_required
def instructor_courses(request):
    """Searchable, filterable list containing strictly the logged-in instructor's courses."""
    instructor = request.user.instructor_profile
    active_filter = Q(enrollments__status__in=Enrollment.ACTIVE_STATUSES)

    courses = (
        Course.objects.filter(instructor=instructor)
        .annotate(enrolled_students=Count('enrollments', filter=active_filter, distinct=True))
        .order_by('-created_date')
    )

    search_query = request.GET.get('q', '').strip()
    selected_category = request.GET.get('category', '').strip()
    selected_status = request.GET.get('status', '').strip()

    if search_query:
        courses = courses.filter(
            Q(course_title__icontains=search_query) |
            Q(category__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    if selected_category:
        courses = courses.filter(category__iexact=selected_category)
    if selected_status in {'Published', 'Draft'}:
        courses = courses.filter(status=selected_status)

    categories = (
        Course.objects.filter(instructor=instructor)
        .values_list('category', flat=True)
        .distinct()
        .order_by('category')
    )
    total_courses = courses.count()
    page_obj, paginator, extra_query = _paginate_queryset(request, courses, per_page=8)

    return render(request, 'Instructor/course_list.html', {
        'instructor': instructor,
        'courses': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'is_paginated': page_obj.has_other_pages(),
        'categories': categories,
        'search_query': search_query,
        'selected_category': selected_category,
        'selected_status': selected_status,
        'total_courses': total_courses,
        'extra_query': extra_query,
    })


@instructor_required
def instructor_course_detail(request, course_id):
    """Course analytics & enrolled learners strictly for a course owned by this instructor."""
    instructor = request.user.instructor_profile
    course = get_object_or_404(Course, id=course_id, instructor=instructor)

    enrollments = (
        Enrollment.objects.filter(course=course, status__in=Enrollment.ACTIVE_STATUSES)
        .select_related('student__user', 'order')
        .order_by('-enrolled_at')
    )
    course_revenue = (
        OrderItem.objects.filter(course=course, order__status='PAID')
        .aggregate(total=Sum('price'))['total']
        or Decimal('0.00')
    )

    return render(request, 'Instructor/course_detail.html', {
        'instructor': instructor,
        'course': course,
        'enrollments': enrollments,
        'total_enrollments_count': course.enrollments.count(),
        'course_revenue': course_revenue,
    })


@instructor_required
def instructor_add_course(request):
    """Create a new course automatically assigned to the logged-in instructor."""
    instructor = request.user.instructor_profile
    if request.method == 'POST':
        form = InstructorCourseForm(request.POST, request.FILES)
        if form.is_valid():
            course = form.save(commit=False)
            course.instructor = instructor
            course.save()
            messages.success(request, f"Course '{course.course_title}' has been created!")
            return redirect('instructor:instructor_courses')
        messages.error(request, "Please correct the errors in the course form below.")
    else:
        form = InstructorCourseForm()

    return render(request, 'Instructor/course_form.html', {
        'instructor': instructor,
        'form': form,
        'action_title': 'Add New Course',
        'subtitle': 'Publish a new course directly under your faculty profile.',
        'button_text': 'Create Course',
    })


@instructor_required
def instructor_edit_course(request, course_id):
    """Edit an existing course strictly owned by the logged-in instructor."""
    instructor = request.user.instructor_profile
    course = get_object_or_404(Course, id=course_id, instructor=instructor)

    if request.method == 'POST':
        form = InstructorCourseForm(request.POST, request.FILES, instance=course)
        if form.is_valid():
            updated = form.save(commit=False)
            updated.instructor = instructor
            if request.POST.get('remove_course_image') and 'course_image' not in request.FILES:
                updated.course_image = None
            updated.save()
            messages.success(request, f"Course '{updated.course_title}' has been updated!")
            return redirect('instructor:instructor_courses')
        messages.error(request, "Please correct the errors in the form below.")
    else:
        form = InstructorCourseForm(instance=course)

    return render(request, 'Instructor/course_form.html', {
        'instructor': instructor,
        'course': course,
        'form': form,
        'action_title': f"Edit Course: {course.course_title}",
        'subtitle': 'Update pricing, status, category, media, or course description.',
        'button_text': 'Save Changes',
    })


@instructor_required
def instructor_delete_course(request, course_id):
    """Safely delete an owned course, or unpublish to Draft if student enrollments exist."""
    instructor = request.user.instructor_profile
    course = get_object_or_404(Course, id=course_id, instructor=instructor)
    if request.method != 'POST':
        messages.warning(request, "Please confirm course deletion using the Delete confirmation dialog.")
        return redirect('instructor:instructor_courses')

    enrollment_count = course.enrollments.count()
    if enrollment_count > 0:
        with transaction.atomic():
            if course.status != 'Draft':
                course.status = 'Draft'
                course.save(update_fields=['status'])
            Cart.objects.filter(course=course).delete()
        messages.warning(
            request,
            f"Course '{course.course_title}' has {enrollment_count} student enrollment(s) and was moved to Draft instead of deleting to protect enrollment and payment records."
        )
        return redirect('instructor:instructor_courses')

    title = course.course_title
    with transaction.atomic():
        Cart.objects.filter(course=course).delete()
        course.delete()
    messages.success(request, f"Course '{title}' has been deleted.")
    return redirect('instructor:instructor_courses')


@instructor_required
def instructor_profile(request):
    """View and update the authenticated instructor's own profile."""
    instructor = request.user.instructor_profile
    if request.method == 'POST':
        form = InstructorProfileForm(request.POST, instructor=instructor)
        if form.is_valid():
            form.save()
            messages.success(request, "Your instructor profile has been updated!")
            return redirect('instructor:instructor_profile')
        messages.error(request, "Please correct the errors in your profile form.")
    else:
        form = InstructorProfileForm(instructor=instructor)

    courses_count = Course.objects.filter(instructor=instructor).count()
    students_count = (
        Enrollment.objects.filter(course__instructor=instructor, status__in=Enrollment.ACTIVE_STATUSES)
        .values('student_id')
        .distinct()
        .count()
    )

    return render(request, 'Instructor/profile.html', {
        'instructor': instructor,
        'form': form,
        'courses_count': courses_count,
        'students_count': students_count,
    })


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
