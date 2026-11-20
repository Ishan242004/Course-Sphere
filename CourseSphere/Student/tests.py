from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from Student.models import Student
from Instructor.models import Instructor, Course


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


class CourseListingTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.course_list_url = reverse('student:course_list')

        # Create instructor for courses
        self.instructor_user = User.objects.create_user(
            username='dr_watson',
            email='watson@example.com',
            password='Password123',
            first_name='John',
            last_name='Watson'
        )
        self.instructor = Instructor.objects.create(
            user=self.instructor_user,
            specialization='Full Stack Development'
        )

        # Create sample courses dynamically in database
        self.course1 = Course.objects.create(
            course_title="Modern Python Bootcamp",
            category="Programming",
            price=Decimal("19.99"),
            description="Master Python from basics to advanced object-oriented programming concepts.",
            instructor=self.instructor
        )
        self.course2 = Course.objects.create(
            course_title="UI/UX Design Masterclass",
            category="Design",
            price=Decimal("0.00"),
            description="Learn how to design modern web interfaces using Figma and user research.",
            instructor=self.instructor
        )

    def test_course_list_page_status_code(self):
        """Course listing page returns HTTP 200."""
        response = self.client.get(self.course_list_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'Student/course_list.html')

    def test_course_list_displays_courses_dynamically(self):
        """Courses created in the database are rendered dynamically with title, category, price, description."""
        response = self.client.get(self.course_list_url)
        self.assertEqual(response.status_code, 200)

        # Course 1 verification
        self.assertContains(response, "Modern Python Bootcamp")
        self.assertContains(response, "Programming")
        self.assertContains(response, "$19.99")
        self.assertContains(response, "Master Python from basics")

        # Course 2 verification (Free price)
        self.assertContains(response, "UI/UX Design Masterclass")
        self.assertContains(response, "Design")
        self.assertContains(response, "Free")
        self.assertContains(response, "Learn how to design modern web interfaces")

        # View Details button verification
        detail_url_1 = reverse('student:course_detail', args=[self.course1.id])
        detail_url_2 = reverse('student:course_detail', args=[self.course2.id])
        self.assertContains(response, detail_url_1)
        self.assertContains(response, detail_url_2)
        self.assertContains(response, "View Details")

    def test_course_list_empty_state(self):
        """When no courses exist in the database, the empty state is displayed."""
        Course.objects.all().delete()
        response = self.client.get(self.course_list_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No Courses Found")

    def test_course_list_filter_by_category(self):
        """Filtering by category only returns matching courses."""
        response = self.client.get(self.course_list_url, {'category': 'Programming'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Modern Python Bootcamp")
        self.assertNotContains(response, "UI/UX Design Masterclass")

    def test_course_list_search_query(self):
        """Searching by keyword returns only matching courses."""
        response = self.client.get(self.course_list_url, {'q': 'Figma'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "UI/UX Design Masterclass")
        self.assertNotContains(response, "Modern Python Bootcamp")

    def test_course_detail_view_success(self):
        """Clicking View Details navigates to the course detail page."""
        detail_url = reverse('student:course_detail', args=[self.course1.id])
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'Student/course_detail.html')
        self.assertContains(response, "Modern Python Bootcamp")
        self.assertContains(response, "Programming")
        self.assertContains(response, "$19.99")
        self.assertContains(response, "John Watson")

    def test_course_detail_view_404_invalid_id(self):
        """Nonexistent course id returns 404."""
        invalid_url = reverse('student:course_detail', args=[99999])
        response = self.client.get(invalid_url)
        self.assertEqual(response.status_code, 404)

