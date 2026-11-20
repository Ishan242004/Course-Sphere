from django.shortcuts import render


def home(request):
    try:
        from Instructor.models import Course
        featured_courses = Course.objects.all().order_by('-created_date')[:3]
        total_courses = Course.objects.count()
    except Exception:
        featured_courses = []
        total_courses = 0

    return render(request, 'home.html', {
        'featured_courses': featured_courses,
        'total_courses': total_courses,
    })
