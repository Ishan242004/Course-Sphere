from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from Admin.models import Admin
from Student.models import Student
from Instructor.models import Instructor


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
