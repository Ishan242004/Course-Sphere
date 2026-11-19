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

    def test_student_registration_success(self):
        response = self.client.post(self.register_url, {
            'first_name': 'Rahul',
            'last_name': 'Sharma',
            'username': 'rahul_s',
            'email': 'rahul@example.com',
            'phone': '9876543210',
            'roll_number': 'STU2026-001',
            'password': 'StrongPassword123',
            'confirm_password': 'StrongPassword123',
        })
        self.assertRedirects(response, self.login_url)
        self.assertTrue(User.objects.filter(username='rahul_s').exists())
        user = User.objects.get(username='rahul_s')
        self.assertTrue(hasattr(user, 'student_profile'))
        self.assertEqual(user.student_profile.roll_number, 'STU2026-001')

    def test_student_registration_password_mismatch(self):
        response = self.client.post(self.register_url, {
            'first_name': 'Rahul',
            'last_name': 'Sharma',
            'username': 'rahul_mismatch',
            'email': 'mismatch@example.com',
            'roll_number': 'STU2026-002',
            'password': 'PasswordOne123',
            'confirm_password': 'PasswordTwo123',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='rahul_mismatch').exists())
        self.assertFormError(response.context['form'], 'confirm_password', 'Passwords do not match.')

    def test_student_login_success(self):
        user = User.objects.create_user(username='john_doe', email='john@example.com', password='Password123')
        Student.objects.create(user=user, roll_number='STU-100')

        response = self.client.post(self.login_url, {
            'username': 'john_doe',
            'password': 'Password123'
        })
        self.assertRedirects(response, self.dashboard_url)

    def test_student_login_with_email(self):
        user = User.objects.create_user(username='jane_doe', email='jane@example.com', password='Password123')
        Student.objects.create(user=user, roll_number='STU-101')

        response = self.client.post(self.login_url, {
            'username': 'jane@example.com',
            'password': 'Password123'
        })
        self.assertRedirects(response, self.dashboard_url)

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

    def test_unauthenticated_dashboard_redirect(self):
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.login_url in response.url)
