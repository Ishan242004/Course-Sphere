from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from decimal import Decimal
from Admin.models import Admin
from Student.models import Student
from Instructor.models import Instructor, Course


class AdminAuthTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.login_url = reverse('admin_portal:admin_login')
        self.logout_url = reverse('admin_portal:admin_logout')
        self.dashboard_url = reverse('admin_portal:admin_dashboard')

        # Create an admin user with Admin profile
        self.admin_user = User.objects.create_user(
            username='sys_admin',
            email='admin@coursesphere.com',
            password='AdminPassword123'
        )
        self.admin_profile = Admin.objects.create(user=self.admin_user, phone='1234567890')

    def test_admin_login_page_status_code(self):
        """Admin login page returns 200 and uses Admin/admin_login.html template."""
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'Admin/admin_login.html')
        self.assertContains(response, "Administrator Login")

    def test_admin_login_success(self):
        """Valid admin credentials log in successfully and redirect to admin dashboard."""
        response = self.client.post(self.login_url, {
            'username': 'sys_admin',
            'password': 'AdminPassword123'
        }, follow=True)
        self.assertRedirects(response, self.dashboard_url)
        self.assertContains(response, "Welcome to CourseSphere Admin Cockpit")

    def test_student_blocked_from_admin_login(self):
        """Student accounts cannot log into the Admin portal."""
        student_user = User.objects.create_user(
            username='student_user',
            email='student@example.com',
            password='Password123'
        )
        Student.objects.create(user=student_user, roll_number='STU-001')

        response = self.client.post(self.login_url, {
            'username': 'student_user',
            'password': 'Password123'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This account is registered as a Student")

    def test_instructor_blocked_from_admin_login(self):
        """Instructor accounts cannot log into the Admin portal."""
        instructor_user = User.objects.create_user(
            username='prof_user',
            email='prof@example.com',
            password='Password123'
        )
        Instructor.objects.create(user=instructor_user, specialization='Physics')

        response = self.client.post(self.login_url, {
            'username': 'prof_user',
            'password': 'Password123'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This account is registered as an Instructor")

    def test_admin_logout(self):
        """Admin logout redirects to admin login page."""
        self.client.login(username='sys_admin', password='AdminPassword123')
        response = self.client.get(self.logout_url)
        self.assertRedirects(response, self.login_url)

    def test_student_login_footer_has_admin_login_link(self):
        """Student login footer has link to Admin login."""
        response = self.client.get(reverse('student:student_login'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.login_url)
        self.assertContains(response, "Admin Login")

    def test_instructor_login_footer_has_admin_login_link(self):
        """Instructor login footer has link to Admin login."""
        response = self.client.get(reverse('instructor:instructor_login'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.login_url)
        self.assertContains(response, "Admin Login")


class AdminCourseManagementTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.dashboard_url = reverse('admin_portal:admin_dashboard')
        self.add_course_url = reverse('admin_portal:add_course')

        self.admin_user = User.objects.create_user(
            username='course_admin',
            email='cadmin@coursesphere.com',
            password='AdminPassword123'
        )
        self.admin_profile = Admin.objects.create(user=self.admin_user, phone='1234567890')
        self.client.login(username='course_admin', password='AdminPassword123')

    def test_dashboard_does_not_contain_django_admin_site_link(self):
        """The Django Admin Site link is removed, sidebar is present, and redundant items are removed."""
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Django Admin Site")
        self.assertNotContains(response, reverse('admin:index'))
        self.assertContains(response, "glass-admin-sidebar")
        self.assertContains(response, "Add Course")
        self.assertContains(response, reverse('admin_portal:course_list'))
        self.assertNotContains(response, "Add Course (Full Page)")
        self.assertNotContains(response, "Student Catalog")
        self.assertNotContains(response, "Home Page")

    def test_admin_course_list_page(self):
        """Admin course list page returns 200, uses Admin/course_list.html, and renders courses."""
        course = Course.objects.create(
            course_title="Python Data Science Bootcamp",
            category="Data Science",
            price=Decimal("49.99"),
            description="Complete data science and machine learning course."
        )
        url = reverse('admin_portal:course_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'Admin/course_list.html')
        self.assertContains(response, "Course Management Catalog")
        self.assertContains(response, "Python Data Science Bootcamp")
        self.assertContains(response, "glass-breadcrumb")
        self.assertContains(response, "All Courses")

    def test_admin_course_list_search_and_filter(self):
        """Course list page filters courses by title search query and category."""
        Course.objects.create(course_title="React Fundamentals", category="Frontend", price=Decimal("15.00"), description="Intro to React")
        Course.objects.create(course_title="Django Advanced", category="Backend", price=Decimal("25.00"), description="Deep dive into Django")

        url = reverse('admin_portal:course_list')
        # Search for React
        response = self.client.get(url, {'q': 'React'})
        self.assertContains(response, "React Fundamentals")
        self.assertNotContains(response, "Django Advanced")

        # Filter by Backend category
        response = self.client.get(url, {'category': 'Backend'})
        self.assertContains(response, "Django Advanced")
        self.assertNotContains(response, "React Fundamentals")

    def test_admin_can_add_course_with_all_details(self):
        """Admin can successfully add a new course with all required and optional details."""
        data = {
            'course_title': 'Full-Stack Django and React Masterclass',
            'category': 'Web Development',
            'price': '79.99',
            'description': 'Master both backend and frontend development from scratch.',
        }
        response = self.client.post(self.add_course_url, data, follow=True)
        self.assertRedirects(response, self.dashboard_url)
        self.assertContains(response, "Full-Stack Django and React Masterclass")
        self.assertTrue(Course.objects.filter(course_title='Full-Stack Django and React Masterclass').exists())

        # Verify it automatically appears on student course browsing page
        student_catalog_url = reverse('student:course_list')
        student_res = self.client.get(student_catalog_url)
        self.assertContains(student_res, "Full-Stack Django and React Masterclass")
        self.assertContains(student_res, "₹79.99")

    def test_admin_can_edit_course(self):
        """Admin can update existing course details."""
        course = Course.objects.create(
            course_title="Initial Course Title",
            category="Programming",
            price=Decimal("19.99"),
            description="Initial course description."
        )
        edit_url = reverse('admin_portal:edit_course', args=[course.id])
        data = {
            'course_title': 'Updated Course Title Pro',
            'category': 'Advanced Programming',
            'price': '29.99',
            'description': 'Updated course description with new syllabus.',
        }
        response = self.client.post(edit_url, data, follow=True)
        self.assertRedirects(response, self.dashboard_url)
        course.refresh_from_db()
        self.assertEqual(course.course_title, 'Updated Course Title Pro')
        self.assertEqual(course.price, Decimal('29.99'))

    def test_admin_can_delete_course(self):
        """Admin can permanently delete a course from the catalog."""
        course = Course.objects.create(
            course_title="Course To Be Deleted",
            category="Testing",
            price=Decimal("10.00"),
            description="Temporary course for deletion testing."
        )
        delete_url = reverse('admin_portal:delete_course', args=[course.id])
        response = self.client.post(delete_url, follow=True)
        self.assertRedirects(response, self.dashboard_url)
        self.assertFalse(Course.objects.filter(id=course.id).exists())

