from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from Student.models import Student
from Instructor.models import Instructor


class StudentAuthTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.register_url = reverse('student:student_register')
        self.login_url = reverse('student:student_login')
        self.logout_url = reverse('student:student_logout')
        self.dashboard_url = reverse('student:student_dashboard')
        self.home_url = reverse('home')

    def test_new_student_login_redirects_to_register_page(self):
        """New student entering nonexistent credentials on login gets redirected to register with simple message."""
        response = self.client.post(self.login_url, {
            'username': 'brand_new_student',
            'password': 'SomePassword123'
        }, follow=True)
        # Should redirect to register page
        self.assertRedirects(response, f"{self.register_url}?username=brand_new_student")
        self.assertContains(response, "Account not found. Please register first.")

    def test_student_registration_redirects_to_login_page(self):
        """After registration, redirects to login page with simple success message."""
        response = self.client.post(self.register_url, {
            'first_name': 'Rahul',
            'last_name': 'Sharma',
            'username': 'rahul_s',
            'email': 'rahul@example.com',
            'phone': '9876543210',
            'roll_number': 'STU2026-001',
            'password': 'StrongPassword123',
            'confirm_password': 'StrongPassword123',
        }, follow=True)
        self.assertRedirects(response, self.login_url)
        self.assertContains(response, "Registration successful! Please login.")
        self.assertTrue(User.objects.filter(username='rahul_s').exists())

    def test_student_login_redirects_to_home_page(self):
        """After login, redirects to home page with success message."""
        user = User.objects.create_user(username='john_doe', email='john@example.com', password='Password123')
        Student.objects.create(user=user, roll_number='STU-100')

        response = self.client.post(self.login_url, {
            'username': 'john_doe',
            'password': 'Password123'
        }, follow=True)
        self.assertRedirects(response, self.home_url)
        self.assertContains(response, "Login successful! Welcome to CourseSphere.")

    def test_student_login_with_email_redirects_to_home(self):
        user = User.objects.create_user(username='jane_doe', email='jane@example.com', password='Password123')
        Student.objects.create(user=user, roll_number='STU-101')

        response = self.client.post(self.login_url, {
            'username': 'jane@example.com',
            'password': 'Password123'
        }, follow=True)
        self.assertRedirects(response, self.home_url)
        self.assertContains(response, "Login successful! Welcome to CourseSphere.")

    def test_instructor_blocked_from_student_login(self):
        user = User.objects.create_user(username='prof_smith', email='smith@example.com', password='Password123')
        Instructor.objects.create(user=user, specialization='Physics')

        response = self.client.post(self.login_url, {
            'username': 'prof_smith',
            'password': 'Password123'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This account is registered as an Instructor")

    def test_student_logout(self):
        user = User.objects.create_user(username='alex', password='Password123')
        Student.objects.create(user=user, roll_number='STU-102')
        self.client.login(username='alex', password='Password123')

        response = self.client.get(self.logout_url)
        self.assertRedirects(response, self.login_url)
