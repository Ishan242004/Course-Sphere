from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib import admin
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from Instructor.models import Instructor, Course
from Student.models import Student


class InstructorAuthTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.register_url = reverse('instructor:instructor_register')
        self.login_url = reverse('instructor:instructor_login')
        self.logout_url = reverse('instructor:instructor_logout')
        self.dashboard_url = reverse('instructor:instructor_dashboard')
        self.home_url = reverse('home')

    def test_new_instructor_login_redirects_to_register_page(self):
        """New instructor entering nonexistent credentials on login gets redirected to register with simple message."""
        response = self.client.post(self.login_url, {
            'username': 'brand_new_prof',
            'password': 'SomePassword123'
        }, follow=True)
        self.assertRedirects(response, f"{self.register_url}?username=brand_new_prof")
        self.assertContains(response, "Account not found. Please register first.")

    def test_instructor_registration_redirects_to_login_page(self):
        """After registration, redirects to login page with simple success message."""
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
        }, follow=True)
        self.assertRedirects(response, self.login_url)
        self.assertContains(response, "Registration successful! Please login.")
        self.assertTrue(User.objects.filter(username='dr_brown').exists())

    def test_instructor_login_redirects_to_home_page(self):
        """After login, redirects to home page with success message."""
        user = User.objects.create_user(username='prof_clark', email='clark@example.com', password='Password123')
        Instructor.objects.create(user=user, specialization='Mathematics')

        response = self.client.post(self.login_url, {
            'username': 'prof_clark',
            'password': 'Password123'
        }, follow=True)
        self.assertRedirects(response, self.home_url)
        self.assertContains(response, "Login successful! Welcome to CourseSphere.")

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


class CourseModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='course_prof', email='prof@example.com', password='Password123')
        self.instructor = Instructor.objects.create(user=self.user, specialization='Computer Science')

    def test_create_course_with_required_fields(self):
        """Create course with title, category, price, description."""
        course = Course.objects.create(
            course_title="Introduction to Python",
            category="Programming",
            price=Decimal("29.99"),
            description="A comprehensive introduction to Python programming language.",
            instructor=self.instructor
        )
        self.assertEqual(course.course_title, "Introduction to Python")
        self.assertEqual(course.title, "Introduction to Python")
        self.assertEqual(course.category, "Programming")
        self.assertEqual(course.price, Decimal("29.99"))
        self.assertTrue(course.created_date)
        self.assertEqual(course.created_at, course.created_date)
        self.assertEqual(str(course), "Introduction to Python")
        self.assertIsNone(course.course_image.name)
        self.assertEqual(course.instructor, self.instructor)

    def test_create_course_using_aliases(self):
        """Test aliases: title, image, created_at work in create, filter and properties."""
        course = Course.objects.create(
            title="Django Masterclass",
            category="Web Development",
            price=Decimal("49.99"),
            description="Build scalable web apps with Django and Python."
        )
        self.assertEqual(course.course_title, "Django Masterclass")
        self.assertEqual(course.title, "Django Masterclass")

        # Test filter via alias
        fetched = Course.objects.filter(title="Django Masterclass").first()
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.id, course.id)

    def test_course_validation_negative_price(self):
        """Price cannot be negative."""
        course = Course(
            course_title="Free Python",
            category="Programming",
            price=Decimal("-10.00"),
            description="Valid description with enough length."
        )
        with self.assertRaises(ValidationError):
            course.full_clean()

    def test_course_validation_short_title(self):
        """Title must be at least 3 characters."""
        course = Course(
            course_title="Py",
            category="Programming",
            price=Decimal("0.00"),
            description="Valid description with enough length."
        )
        with self.assertRaises(ValidationError):
            course.full_clean()

    def test_course_validation_short_description(self):
        """Description must be at least 10 characters."""
        course = Course(
            course_title="Valid Title",
            category="Programming",
            price=Decimal("0.00"),
            description="Too short"
        )
        with self.assertRaises(ValidationError):
            course.full_clean()

    def test_course_registered_in_admin(self):
        """Verify Course is registered in django.contrib.admin."""
        self.assertTrue(admin.site.is_registered(Course))

