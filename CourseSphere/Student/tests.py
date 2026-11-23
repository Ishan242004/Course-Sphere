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

    def test_registration_rejects_duplicate_username(self):
        """Registration rejects if another student/user already has the same username."""
        User.objects.create_user(username='existing_user', email='exist@example.com', password='Password123')

        response = self.client.post(self.register_url, {
            'first_name': 'Amit',
            'last_name': 'Verma',
            'username': 'existing_user',
            'email': 'amit@example.com',
            'phone': '9876543211',
            'roll_number': 'STU2026-002',
            'password': 'Password1234',
            'confirm_password': 'Password1234',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This username is already taken")

    def test_registration_rejects_password_less_than_8_chars(self):
        """Registration rejects passwords with less than 8 characters."""
        response = self.client.post(self.register_url, {
            'first_name': 'Amit',
            'last_name': 'Verma',
            'username': 'amit_v',
            'email': 'amit@example.com',
            'phone': '9876543212',
            'roll_number': 'STU2026-003',
            'password': '1234567',  # 7 characters
            'confirm_password': '1234567',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "at least 8 characters")

    def test_registration_requires_exactly_10_digit_phone(self):
        """Registration enforces exactly 10-digit numeric phone number."""
        # Test less than 10 digits
        res_short = self.client.post(self.register_url, {
            'first_name': 'Amit',
            'last_name': 'Verma',
            'username': 'amit_short',
            'email': 'amit_short@example.com',
            'phone': '987654321',  # 9 digits
            'roll_number': 'STU2026-004',
            'password': 'Password1234',
            'confirm_password': 'Password1234',
        })
        self.assertEqual(res_short.status_code, 200)
        self.assertContains(res_short, "exactly 10 digits")

        # Test non-numeric phone
        res_letters = self.client.post(self.register_url, {
            'first_name': 'Amit',
            'last_name': 'Verma',
            'username': 'amit_letters',
            'email': 'amit_letters@example.com',
            'phone': '987654321a',  # non-numeric
            'roll_number': 'STU2026-005',
            'password': 'Password1234',
            'confirm_password': 'Password1234',
        })
        self.assertEqual(res_letters.status_code, 200)
        self.assertContains(res_letters, "digits only")

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
        self.assertContains(response, "₹19.99")
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
        self.assertContains(response, "₹19.99")
        self.assertContains(response, "John Watson")

    def test_course_detail_view_404_invalid_id(self):
        """Nonexistent course id returns 404."""
        invalid_url = reverse('student:course_detail', args=[99999])
        response = self.client.get(invalid_url)
        self.assertEqual(response.status_code, 404)

    def test_search_courses_by_title(self):
        """Search query matches courses by title."""
        response = self.client.get(self.course_list_url, {'q': 'Modern Python'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Modern Python Bootcamp")
        self.assertNotContains(response, "UI/UX Design Masterclass")

    def test_filter_by_price_free(self):
        """Filtering by price=free returns only free courses."""
        response = self.client.get(self.course_list_url, {'price': 'free'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "UI/UX Design Masterclass")
        self.assertNotContains(response, "Modern Python Bootcamp")

    def test_filter_by_price_paid(self):
        """Filtering by price=paid returns only paid courses."""
        response = self.client.get(self.course_list_url, {'price': 'paid'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Modern Python Bootcamp")
        self.assertNotContains(response, "UI/UX Design Masterclass")

    def test_filter_by_category_and_price_combined(self):
        """Filtering by both category and price simultaneously."""
        response = self.client.get(self.course_list_url, {
            'category': 'Programming',
            'price': 'paid'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Modern Python Bootcamp")
        self.assertNotContains(response, "UI/UX Design Masterclass")

    def test_pagination_splits_courses_across_pages(self):
        """When courses exceed per_page limit, pagination splits them across pages."""
        # Create 5 more courses so total is 7 (exceeding per_page=6)
        for i in range(1, 6):
            Course.objects.create(
                course_title=f"Extra Course {i}",
                category="Programming",
                price=Decimal(f"{10 + i}.00"),
                description=f"Description for extra course {i} to test pagination.",
                instructor=self.instructor
            )

        # Page 1 should contain 6 courses and show pagination
        response_p1 = self.client.get(self.course_list_url, {'page': 1})
        self.assertEqual(response_p1.status_code, 200)
        self.assertEqual(len(response_p1.context['page_obj']), 6)
        self.assertTrue(response_p1.context['page_obj'].has_next())

        # Page 2 should contain 1 course
        response_p2 = self.client.get(self.course_list_url, {'page': 2})
        self.assertEqual(response_p2.status_code, 200)
        self.assertEqual(len(response_p2.context['page_obj']), 1)
        self.assertTrue(response_p2.context['page_obj'].has_previous())

    def test_pagination_preserves_search_and_filter_parameters(self):
        """Pagination links preserve search query, category, and price parameters."""
        # Create 7 courses in 'Design' category
        for i in range(1, 8):
            Course.objects.create(
                course_title=f"Design Pro {i}",
                category="Design",
                price=Decimal("25.00"),
                description=f"Learn advanced design techniques in module {i}.",
                instructor=self.instructor
            )

        response = self.client.get(self.course_list_url, {
            'category': 'Design',
            'price': 'paid',
            'page': 1
        })
        self.assertEqual(response.status_code, 200)
        # Check that page 2 link retains category=Design and price=paid
        self.assertContains(response, "category=Design")
        self.assertContains(response, "price=paid")
        self.assertContains(response, "page=2")

    def test_empty_state_message_when_no_courses_match_filters(self):
        """When filters return no matching courses, an empty state message is shown."""
        response = self.client.get(self.course_list_url, {'q': 'NonExistentTitleXYZ'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No Courses Found")

    def test_admin_created_course_appears_on_student_course_browsing_page(self):
        """Courses added via Django Admin dynamically appear in the student course catalog."""
        Course.objects.create(
            course_title="Admin Specialized Machine Learning",
            category="Artificial Intelligence",
            price=Decimal("89.99"),
            description="Comprehensive AI and ML masterclass added by administrator.",
        )
        response = self.client.get(self.course_list_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Admin Specialized Machine Learning")
        self.assertContains(response, "Artificial Intelligence")
        self.assertContains(response, "₹89.99")


