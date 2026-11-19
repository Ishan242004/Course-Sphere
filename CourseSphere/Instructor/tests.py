from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from Instructor.models import Instructor
from Student.models import Student


class InstructorAuthTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.register_url = reverse('instructor:instructor_register')
        self.login_url = reverse('instructor:instructor_login')
        self.logout_url = reverse('instructor:instructor_logout')
        self.dashboard_url = reverse('instructor:instructor_dashboard')

    def test_instructor_registration_success(self):
        response = self.client.post(self.register_url, {
            'first_name': 'Dr. Robert',
            'last_name': 'Brown',
            'username': 'dr_brown',
            'email': 'brown@example.com',
            'phone': '9876543211',
            'specialization': 'Computer Science',
            'bio': 'PhD in Artificial Intelligence',
            'password': 'StrongPassword123',
            'confirm_password': 'StrongPassword123',
        })
        self.assertRedirects(response, self.login_url)
        self.assertTrue(User.objects.filter(username='dr_brown').exists())
        user = User.objects.get(username='dr_brown')
        self.assertTrue(hasattr(user, 'instructor_profile'))
        self.assertEqual(user.instructor_profile.specialization, 'Computer Science')

    def test_instructor_login_success(self):
        user = User.objects.create_user(username='prof_clark', email='clark@example.com', password='Password123')
        Instructor.objects.create(user=user, specialization='Mathematics')

        response = self.client.post(self.login_url, {
            'username': 'prof_clark',
            'password': 'Password123'
        })
        self.assertRedirects(response, self.dashboard_url)

    def test_student_blocked_from_instructor_login(self):
        user = User.objects.create_user(username='student_sam', email='sam@example.com', password='Password123')
        Student.objects.create(user=user, roll_number='STU-999')

        response = self.client.post(self.login_url, {
            'username': 'student_sam',
            'password': 'Password123'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This account is registered as a Student")

    def test_instructor_logout(self):
        user = User.objects.create_user(username='prof_foster', password='Password123')
        Instructor.objects.create(user=user, specialization='History')
        self.client.login(username='prof_foster', password='Password123')

        response = self.client.get(self.logout_url)
        self.assertRedirects(response, self.login_url)
