from decimal import Decimal
from functools import wraps
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from Instructor.models import Course, Instructor
from Student.models import Enrollment, Order, Student
from .forms import (
    AdminInstructorForm,
    AdminLoginForm,
    AdminReceiptForm,
    AdminStudentForm,
    CourseForm,
)


def _is_admin_user(user) -> bool:
    return bool(user and (user.is_superuser or user.is_staff or hasattr(user, 'admin_profile')))


def admin_required(view_func):
    """Ensure the user is authenticated and holds CourseSphere Administrator privileges."""
    @login_required(login_url='admin_portal:admin_login')
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not _is_admin_user(request.user):
            messages.error(request, "Access denied. Administrator privileges required.")
            return redirect('admin_portal:admin_login')
        return view_func(request, *args, **kwargs)
    return _wrapped


def _paginate_queryset(request, queryset, per_page=10):
    paginator = Paginator(queryset, per_page)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    query_params = request.GET.copy()
    query_params.pop('page', None)
    return page_obj, paginator, query_params.urlencode()


def admin_login(request):
    if request.user.is_authenticated:
        if _is_admin_user(request.user):
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


@admin_required
def admin_dashboard(request):
    total_revenue = Order.objects.filter(status='PAID').aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    stats = {
        'total_students': Student.objects.count(),
        'total_instructors': Instructor.objects.count(),
        'total_courses': Course.objects.count(),
        'total_receipts': Order.objects.count(),
        'total_revenue': total_revenue,
        'recent_courses': Course.objects.select_related('instructor__user').order_by('-created_date')[:15],
    }
    return render(request, 'Admin/dashboard.html', {
        'stats': stats,
        'course_form': CourseForm(),
    })


# ─── Course CRUD ──────────────────────────────────────────────────────────────

@admin_required
def course_list(request):
    courses = Course.objects.select_related('instructor__user').order_by('-created_date')
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
    page_obj, paginator, extra_query = _paginate_queryset(request, courses, per_page=10)

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


@admin_required
def add_course(request):
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


@admin_required
def edit_course(request, course_id):
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


@admin_required
def delete_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    if request.method == 'POST':
        title = course.course_title
        course.delete()
        messages.success(request, f"Course '{title}' has been permanently deleted.")
    return redirect('admin_portal:admin_dashboard')


# ─── Student CRUD ─────────────────────────────────────────────────────────────

@admin_required
def student_list(request):
    students = (
        Student.objects.select_related('user')
        .annotate(enrollments_count=Count('enrollments', filter=Q(enrollments__status__in=Enrollment.ACTIVE_STATUSES), distinct=True))
        .order_by('-created_at')
    )
    search_query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip().lower()

    if search_query:
        students = students.filter(
            Q(user__username__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(phone__icontains=search_query) |
            Q(roll_number__icontains=search_query)
        )
    if status_filter == 'active':
        students = students.filter(user__is_active=True)
    elif status_filter == 'inactive':
        students = students.filter(user__is_active=False)

    total_students = students.count()
    page_obj, paginator, extra_query = _paginate_queryset(request, students, per_page=10)

    return render(request, 'Admin/student_list.html', {
        'students': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'is_paginated': page_obj.has_other_pages(),
        'search_query': search_query,
        'status_filter': status_filter,
        'total_students': total_students,
        'extra_query': extra_query,
    })


@admin_required
def add_student(request):
    if request.method == 'POST':
        form = AdminStudentForm(request.POST)
        if form.is_valid():
            student = form.save()
            messages.success(request, f"Student '{student.user.username}' has been created!")
            return redirect('admin_portal:student_list')
        messages.error(request, "Please correct the errors in the student form below.")
    else:
        form = AdminStudentForm()

    return render(request, 'Admin/entity_form.html', {
        'entity_type': 'student',
        'form': form,
        'is_edit': False,
        'action_title': 'Add New Student',
        'subtitle': 'Create a student login account and learner profile.',
        'button_text': 'Create Student',
        'back_url': reverse('admin_portal:student_list'),
        'back_label': 'All Students',
    })


@admin_required
def student_detail(request, student_id):
    student = get_object_or_404(Student.objects.select_related('user'), id=student_id)
    enrollments = Enrollment.objects.filter(student=student).select_related('course', 'order').order_by('-enrolled_at')
    orders = Order.objects.filter(student=student).prefetch_related('items').order_by('-created_at')
    return render(request, 'Admin/student_detail.html', {
        'student': student,
        'enrollments': enrollments,
        'orders': orders,
    })


@admin_required
def edit_student(request, student_id):
    student = get_object_or_404(Student.objects.select_related('user'), id=student_id)
    if request.method == 'POST':
        form = AdminStudentForm(request.POST, student_instance=student)
        if form.is_valid():
            student = form.save()
            messages.success(request, f"Student '{student.user.username}' has been updated!")
            return redirect('admin_portal:student_list')
        messages.error(request, "Please correct the errors below.")
    else:
        form = AdminStudentForm(student_instance=student)

    return render(request, 'Admin/entity_form.html', {
        'entity_type': 'student',
        'form': form,
        'is_edit': True,
        'target_object': student,
        'action_title': f"Edit Student: {student.user.get_full_name() or student.user.username}",
        'subtitle': 'Update student identity, roll number, contact details, or password.',
        'button_text': 'Save Student Changes',
        'back_url': reverse('admin_portal:student_list'),
        'back_label': 'All Students',
    })


@admin_required
def delete_student(request, student_id):
    student = get_object_or_404(Student.objects.select_related('user'), id=student_id)
    if request.method == 'POST':
        user = student.user
        if user == request.user:
            messages.error(request, "You cannot delete your own active account.")
        else:
            username = user.username
            user.delete()
            messages.success(request, f"Student '{username}' and associated records were permanently deleted.")
    return redirect('admin_portal:student_list')


# ─── Instructor CRUD ──────────────────────────────────────────────────────────

@admin_required
def instructor_list(request):
    instructors = (
        Instructor.objects.select_related('user')
        .annotate(courses_count=Count('courses', distinct=True))
        .order_by('-created_at')
    )
    search_query = request.GET.get('q', '').strip()
    selected_specialization = request.GET.get('specialization', '').strip()

    if search_query:
        instructors = instructors.filter(
            Q(user__username__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(phone__icontains=search_query) |
            Q(specialization__icontains=search_query)
        )
    if selected_specialization:
        instructors = instructors.filter(specialization__iexact=selected_specialization)

    specializations = (
        Instructor.objects.exclude(specialization__isnull=True)
        .exclude(specialization='')
        .values_list('specialization', flat=True)
        .distinct()
        .order_by('specialization')
    )
    total_instructors = instructors.count()
    page_obj, paginator, extra_query = _paginate_queryset(request, instructors, per_page=10)

    return render(request, 'Admin/instructor_list.html', {
        'instructors': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'is_paginated': page_obj.has_other_pages(),
        'specializations': specializations,
        'selected_specialization': selected_specialization,
        'search_query': search_query,
        'total_instructors': total_instructors,
        'extra_query': extra_query,
    })


@admin_required
def add_instructor(request):
    if request.method == 'POST':
        form = AdminInstructorForm(request.POST)
        if form.is_valid():
            instructor = form.save()
            messages.success(request, f"Instructor '{instructor.user.username}' has been created!")
            return redirect('admin_portal:instructor_list')
        messages.error(request, "Please correct the errors in the instructor form below.")
    else:
        form = AdminInstructorForm()

    return render(request, 'Admin/entity_form.html', {
        'entity_type': 'instructor',
        'form': form,
        'is_edit': False,
        'action_title': 'Add New Instructor',
        'subtitle': 'Onboard a faculty account with teaching specialization and bio.',
        'button_text': 'Create Instructor',
        'back_url': reverse('admin_portal:instructor_list'),
        'back_label': 'All Instructors',
    })


@admin_required
def instructor_detail(request, instructor_id):
    instructor = get_object_or_404(Instructor.objects.select_related('user'), id=instructor_id)
    courses = Course.objects.filter(instructor=instructor).annotate(
        enrollments_count=Count('enrollments', filter=Q(enrollments__status__in=Enrollment.ACTIVE_STATUSES), distinct=True)
    ).order_by('-created_date')
    return render(request, 'Admin/instructor_detail.html', {
        'instructor': instructor,
        'courses': courses,
    })


@admin_required
def edit_instructor(request, instructor_id):
    instructor = get_object_or_404(Instructor.objects.select_related('user'), id=instructor_id)
    if request.method == 'POST':
        form = AdminInstructorForm(request.POST, instructor_instance=instructor)
        if form.is_valid():
            instructor = form.save()
            messages.success(request, f"Instructor '{instructor.user.username}' has been updated!")
            return redirect('admin_portal:instructor_list')
        messages.error(request, "Please correct the errors below.")
    else:
        form = AdminInstructorForm(instructor_instance=instructor)

    return render(request, 'Admin/entity_form.html', {
        'entity_type': 'instructor',
        'form': form,
        'is_edit': True,
        'target_object': instructor,
        'action_title': f"Edit Instructor: {instructor.user.get_full_name() or instructor.user.username}",
        'subtitle': 'Update instructor credentials, specialization, bio, or password.',
        'button_text': 'Save Instructor Changes',
        'back_url': reverse('admin_portal:instructor_list'),
        'back_label': 'All Instructors',
    })


@admin_required
def delete_instructor(request, instructor_id):
    instructor = get_object_or_404(Instructor.objects.select_related('user'), id=instructor_id)
    if request.method == 'POST':
        user = instructor.user
        if user == request.user:
            messages.error(request, "You cannot delete your own active account.")
        else:
            username = user.username
            user.delete()
            messages.success(request, f"Instructor '{username}' and associated courses were permanently deleted.")
    return redirect('admin_portal:instructor_list')


# ─── Payment Receipt (Order) CRUD ─────────────────────────────────────────────

@admin_required
def receipt_list(request):
    receipts = (
        Order.objects.select_related('student__user')
        .prefetch_related('items')
        .order_by('-created_at')
    )
    search_query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip().upper()
    method_filter = request.GET.get('payment_method', '').strip().upper()

    if search_query:
        receipts = receipts.filter(
            Q(order_id__icontains=search_query) |
            Q(student__user__username__icontains=search_query) |
            Q(student__user__first_name__icontains=search_query) |
            Q(student__user__last_name__icontains=search_query) |
            Q(student__user__email__icontains=search_query) |
            Q(razorpay_order_id__icontains=search_query) |
            Q(razorpay_payment_id__icontains=search_query) |
            Q(coupon_code__icontains=search_query)
        )
    if status_filter in {'PAID', 'PENDING', 'FAILED'}:
        receipts = receipts.filter(status=status_filter)
    if method_filter in {choice[0] for choice in Order.PAYMENT_METHOD_CHOICES}:
        receipts = receipts.filter(payment_method=method_filter)

    total_receipts = receipts.count()
    paid_revenue = Order.objects.filter(status='PAID').aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    paid_count = Order.objects.filter(status='PAID').count()
    page_obj, paginator, extra_query = _paginate_queryset(request, receipts, per_page=10)

    return render(request, 'Admin/receipt_list.html', {
        'receipts': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'is_paginated': page_obj.has_other_pages(),
        'search_query': search_query,
        'status_filter': status_filter,
        'method_filter': method_filter,
        'status_choices': Order.STATUS_CHOICES,
        'payment_method_choices': Order.PAYMENT_METHOD_CHOICES,
        'total_receipts': total_receipts,
        'paid_revenue': paid_revenue,
        'paid_count': paid_count,
        'extra_query': extra_query,
    })


@admin_required
def add_receipt(request):
    if request.method == 'POST':
        form = AdminReceiptForm(request.POST)
        if form.is_valid():
            order = form.save()
            messages.success(request, f"Payment receipt '{order.order_id}' created for ₹{order.total_amount}!")
            return redirect('admin_portal:receipt_detail', order_id=order.order_id)
        messages.error(request, "Please correct the errors in the payment receipt form below.")
    else:
        form = AdminReceiptForm()

    return render(request, 'Admin/entity_form.html', {
        'entity_type': 'receipt',
        'form': form,
        'is_edit': False,
        'action_title': 'Create Payment Receipt',
        'subtitle': 'Issue an itemized receipt and automatically calculate GST & student enrollments.',
        'button_text': 'Create Receipt',
        'back_url': reverse('admin_portal:receipt_list'),
        'back_label': 'Payment Receipts',
    })


@admin_required
def receipt_detail(request, order_id):
    order = get_object_or_404(
        Order.objects.select_related('student__user').prefetch_related('items__course'),
        order_id=order_id,
    )
    return render(request, 'Admin/receipt_detail.html', {'order': order})


@admin_required
def edit_receipt(request, order_id):
    order = get_object_or_404(Order.objects.select_related('student__user').prefetch_related('items'), order_id=order_id)
    if request.method == 'POST':
        form = AdminReceiptForm(request.POST, order_instance=order)
        if form.is_valid():
            order = form.save()
            messages.success(request, f"Payment receipt '{order.order_id}' updated successfully!")
            return redirect('admin_portal:receipt_detail', order_id=order.order_id)
        messages.error(request, "Please correct the errors below.")
    else:
        form = AdminReceiptForm(order_instance=order)

    return render(request, 'Admin/entity_form.html', {
        'entity_type': 'receipt',
        'form': form,
        'is_edit': True,
        'target_object': order,
        'action_title': f"Edit Receipt: {order.order_id}",
        'subtitle': 'Update included courses, promo discount, payment status, or Razorpay reference IDs.',
        'button_text': 'Save Receipt Changes',
        'back_url': reverse('admin_portal:receipt_detail', args=[order.order_id]),
        'back_label': 'View Receipt',
    })


@admin_required
def delete_receipt(request, order_id):
    order = get_object_or_404(Order, order_id=order_id)
    if request.method == 'POST':
        receipt_code = order.order_id
        with transaction.atomic():
            Enrollment.objects.filter(order=order).delete()
            order.delete()
        messages.success(request, f"Payment receipt '{receipt_code}' has been permanently deleted.")
    return redirect('admin_portal:receipt_list')
