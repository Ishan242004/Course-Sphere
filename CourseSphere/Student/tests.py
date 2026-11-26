import hashlib
import hmac
import json
from decimal import Decimal
from unittest.mock import patch
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth.models import User
from Student.models import Student, Cart, Order, Enrollment
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


class StudentCartAndPaymentTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.student_user = User.objects.create_user(
            username='cart_student',
            email='cartstudent@example.com',
            password='Password123',
            first_name='Riya',
            last_name='Patel',
        )
        self.student = Student.objects.create(
            user=self.student_user,
            phone='9876543219',
            roll_number='STU-CART-01',
        )

        self.instructor_user = User.objects.create_user(
            username='cart_prof',
            email='cartprof@example.com',
            password='Password123',
        )
        self.instructor = Instructor.objects.create(
            user=self.instructor_user,
            specialization='Software Engineering',
        )

        self.course_one = Course.objects.create(
            course_title='Full Stack Python Mastery',
            category='Programming',
            price=Decimal('100.00'),
            description='Complete Python web backend engineering course with real projects.',
            instructor=self.instructor,
        )
        self.course_two = Course.objects.create(
            course_title='System Design Architecture',
            category='Programming',
            price=Decimal('200.00'),
            description='Learn scalable distributed systems and high-load architectures.',
            instructor=self.instructor,
        )
        self.course_free = Course.objects.create(
            course_title='Git and GitHub Starter',
            category='Programming',
            price=Decimal('0.00'),
            description='Essential version control workflows for modern software developers.',
            instructor=self.instructor,
        )

        self.cart_url = reverse('student:cart')
        self.coupon_url = reverse('student:apply_coupon')
        self.checkout_url = reverse('student:checkout')
        self.verify_url = reverse('student:razorpay_verify')
        self.clear_url = reverse('student:clear_cart')

    def test_guest_redirected_to_login_on_cart_access(self):
        response = self.client.get(self.cart_url)
        self.assertRedirects(response, f"{reverse('student:student_login')}?next={self.cart_url}")

        add_res = self.client.post(reverse('student:add_to_cart', args=[self.course_one.id]))
        expected_next = reverse('student:add_to_cart', args=[self.course_one.id])
        self.assertRedirects(add_res, f"{reverse('student:student_login')}?next={expected_next}")

    def test_instructor_cannot_add_to_student_cart(self):
        self.client.login(username='cart_prof', password='Password123')
        response = self.client.post(
            reverse('student:add_to_cart', args=[self.course_one.id]),
            follow=True,
        )
        self.assertContains(response, "Only registered students can add courses to the cart.")
        self.assertEqual(Cart.objects.count(), 0)

    def test_add_multiple_courses_recalculates_subtotal_gst_and_total(self):
        self.client.login(username='cart_student', password='Password123')

        # 1. Add first course (₹100.00) -> Subtotal 100.00, GST (18%) 18.00, Total 118.00
        self.client.post(reverse('student:add_to_cart', args=[self.course_one.id]))
        res1 = self.client.get(self.cart_url)
        self.assertEqual(res1.status_code, 200)
        summary1 = res1.context['summary']
        self.assertEqual(summary1['item_count'], 1)
        self.assertEqual(summary1['subtotal'], Decimal('100.00'))
        self.assertEqual(summary1['tax_amount'], Decimal('18.00'))
        self.assertEqual(summary1['total_amount'], Decimal('118.00'))
        self.assertContains(res1, "₹118.00")

        # 2. Add second course (₹200.00) -> Subtotal 300.00, GST (18%) 54.00, Total 354.00
        ajax_res = self.client.post(
            reverse('student:add_to_cart', args=[self.course_two.id]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(ajax_res.status_code, 200)
        payload = ajax_res.json()
        self.assertTrue(payload['ok'])
        self.assertTrue(payload['added'])
        self.assertEqual(payload['item_count'], 2)
        self.assertEqual(payload['subtotal'], '300.00')
        self.assertEqual(payload['tax_amount'], '54.00')
        self.assertEqual(payload['total_amount'], '354.00')

        res2 = self.client.get(self.cart_url)
        self.assertContains(res2, "Full Stack Python Mastery")
        self.assertContains(res2, "System Design Architecture")
        self.assertContains(res2, "₹300.00")
        self.assertContains(res2, "₹54.00")
        self.assertContains(res2, "₹354.00")

        # 3. Adding same course again does not duplicate or inflate totals
        dup_res = self.client.post(
            reverse('student:add_to_cart', args=[self.course_one.id]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertFalse(dup_res.json()['added'])
        self.assertEqual(dup_res.json()['item_count'], 2)
        self.assertEqual(dup_res.json()['total_amount'], '354.00')

    def test_coupon_calculation_and_removal_recalculates_payment(self):
        self.client.login(username='cart_student', password='Password123')
        self.client.post(reverse('student:add_to_cart', args=[self.course_one.id]))
        self.client.post(reverse('student:add_to_cart', args=[self.course_two.id]))

        # Invalid coupon rejected
        invalid_res = self.client.post(self.coupon_url, {'coupon_code': 'BADCODE'}, follow=True)
        self.assertContains(invalid_res, "Invalid promo code")

        # Valid 10% coupon SPHERE10: Subtotal 300 - 30 = 270 taxable; 18% GST = 48.60; Total = 318.60
        valid_res = self.client.post(self.coupon_url, {'coupon_code': 'sphere10'}, follow=True)
        summary = valid_res.context['summary']
        self.assertEqual(summary['coupon_code'], 'SPHERE10')
        self.assertEqual(summary['discount_amount'], Decimal('30.00'))
        self.assertEqual(summary['taxable_amount'], Decimal('270.00'))
        self.assertEqual(summary['tax_amount'], Decimal('48.60'))
        self.assertEqual(summary['total_amount'], Decimal('318.60'))
        self.assertContains(valid_res, "₹318.60")

        # Remove course_two -> only ₹100 remains with SPHERE10 -> 100 - 10 = 90; GST = 16.20; Total = 106.20
        rem_res = self.client.post(reverse('student:remove_from_cart', args=[self.course_two.id]), follow=True)
        rem_summary = rem_res.context['summary']
        self.assertEqual(rem_summary['item_count'], 1)
        self.assertEqual(rem_summary['subtotal'], Decimal('100.00'))
        self.assertEqual(rem_summary['discount_amount'], Decimal('10.00'))
        self.assertEqual(rem_summary['tax_amount'], Decimal('16.20'))
        self.assertEqual(rem_summary['total_amount'], Decimal('106.20'))

        # Clear cart completely resets items and coupon
        clear_res = self.client.post(self.clear_url, follow=True)
        self.assertEqual(clear_res.context['summary']['item_count'], 0)
        self.assertContains(clear_res, "Your Course Cart is Empty")

    def test_free_course_cart_total_is_zero(self):
        self.client.login(username='cart_student', password='Password123')
        self.client.post(reverse('student:add_to_cart', args=[self.course_free.id]))
        res = self.client.get(self.cart_url)
        summary = res.context['summary']
        self.assertTrue(summary['is_free_order'])
        self.assertEqual(summary['subtotal'], Decimal('0.00'))
        self.assertEqual(summary['tax_amount'], Decimal('0.00'))
        self.assertEqual(summary['total_amount'], Decimal('0.00'))
        self.assertContains(res, "Complete Free Enrollment")

    def test_cart_hides_payment_method_selector_and_shows_pay_button(self):
        self.client.login(username='cart_student', password='Password123')
        self.client.post(reverse('student:add_to_cart', args=[self.course_one.id]))
        res = self.client.get(self.cart_url)
        self.assertEqual(res.status_code, 200)
        self.assertNotContains(res, "Select Payment Method")
        self.assertNotContains(res, 'name="payment_method"')
        self.assertContains(res, "Pay ₹118.00 & Enroll")
        self.assertContains(res, "Secured by Razorpay")

    def test_free_course_checkout_bypasses_razorpay_and_enrolls_directly(self):
        self.client.login(username='cart_student', password='Password123')
        self.client.post(reverse('student:add_to_cart', args=[self.course_free.id]))

        checkout_res = self.client.post(
            self.checkout_url,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(checkout_res.status_code, 200)
        payload = checkout_res.json()
        self.assertTrue(payload['ok'])
        self.assertTrue(payload['free_order'])

        order = Order.objects.get(student=self.student)
        self.assertEqual(order.payment_method, 'FREE')
        self.assertEqual(order.status, 'PAID')
        self.assertEqual(order.total_amount, Decimal('0.00'))
        self.assertEqual(Cart.objects.filter(student=self.student).count(), 0)
        free_enrollment = Enrollment.objects.get(student=self.student, course=self.course_free)
        self.assertEqual(free_enrollment.status, 'Active')
        self.assertEqual(free_enrollment.order, order)
        self.assertEqual(free_enrollment.payment_reference, order.order_id)

    @override_settings(RAZORPAY_KEY_ID='rzp_test_unit_key', RAZORPAY_KEY_SECRET='unit_test_secret_123')
    @patch('Student.views.create_razorpay_order')
    def test_razorpay_checkout_verifies_signature_and_completes_order(self, mock_create_rzp_order):
        mock_create_rzp_order.return_value = {
            'id': 'order_TEST_RZP_123456',
            'amount': 28320,
            'currency': 'INR',
        }

        self.client.login(username='cart_student', password='Password123')
        self.client.post(reverse('student:add_to_cart', args=[self.course_one.id]))
        self.client.post(reverse('student:add_to_cart', args=[self.course_two.id]))
        self.client.post(self.coupon_url, {'coupon_code': 'SPHERE20'})

        # Step 1: Checkout initializes Razorpay order (₹283.20 -> 28320 paise)
        init_res = self.client.post(
            self.checkout_url,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(init_res.status_code, 200)
        init_payload = init_res.json()
        self.assertTrue(init_payload['ok'])
        self.assertFalse(init_payload['free_order'])
        self.assertEqual(init_payload['key'], 'rzp_test_unit_key')
        self.assertEqual(init_payload['razorpay_order_id'], 'order_TEST_RZP_123456')
        self.assertEqual(init_payload['amount'], 28320)
        self.assertEqual(init_payload['currency'], 'INR')
        mock_create_rzp_order.assert_called_once()
        self.assertEqual(mock_create_rzp_order.call_args.kwargs['amount_paise'], 28320)

        # Before verification: Order is PENDING, Cart intact, ZERO enrollments created
        pending_order = Order.objects.get(student=self.student, razorpay_order_id='order_TEST_RZP_123456')
        self.assertEqual(pending_order.status, 'PENDING')
        self.assertEqual(Enrollment.objects.count(), 0)
        self.assertEqual(Cart.objects.filter(student=self.student).count(), 2)

        # Step 2: Valid HMAC-SHA256 signature succeeds and unlocks courses automatically
        rzp_payment_id = 'pay_TEST_987654'
        valid_signature = hmac.new(
            b'unit_test_secret_123',
            f"order_TEST_RZP_123456|{rzp_payment_id}".encode(),
            hashlib.sha256,
        ).hexdigest()

        verify_res = self.client.post(
            self.verify_url,
            data=json.dumps({
                'razorpay_order_id': 'order_TEST_RZP_123456',
                'razorpay_payment_id': rzp_payment_id,
                'razorpay_signature': valid_signature,
            }),
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(verify_res.status_code, 200)
        verify_payload = verify_res.json()
        self.assertTrue(verify_payload['ok'])
        self.assertFalse(verify_payload['duplicate'])
        self.assertEqual(verify_payload['enrolled_count'], 2)

        order = Order.objects.get(student=self.student)
        self.assertEqual(order.subtotal, Decimal('300.00'))
        self.assertEqual(order.discount_amount, Decimal('60.00'))
        self.assertEqual(order.tax_amount, Decimal('43.20'))
        self.assertEqual(order.total_amount, Decimal('283.20'))
        self.assertEqual(order.coupon_code, 'SPHERE20')
        self.assertEqual(order.payment_method, 'RAZORPAY')
        self.assertEqual(order.razorpay_order_id, 'order_TEST_RZP_123456')
        self.assertEqual(order.razorpay_payment_id, rzp_payment_id)
        self.assertEqual(order.razorpay_signature, valid_signature)
        self.assertEqual(order.status, 'PAID')
        self.assertEqual(order.items.count(), 2)

        # Automatic Enrollments created with Active status, enrolled_at, and payment_reference
        enr1 = Enrollment.objects.get(student=self.student, course=self.course_one)
        enr2 = Enrollment.objects.get(student=self.student, course=self.course_two)
        for enr in (enr1, enr2):
            self.assertEqual(enr.status, 'Active')
            self.assertEqual(enr.payment_reference, rzp_payment_id)
            self.assertEqual(enr.order, order)
            self.assertIsNotNone(enr.enrolled_at)

        # Receipt page displays Order ID, Payment ID, Method, and Paid Total
        receipt_res = self.client.get(verify_payload['redirect_url'])
        self.assertEqual(receipt_res.status_code, 200)
        self.assertTemplateUsed(receipt_res, 'Student/order_success.html')
        self.assertContains(receipt_res, order.order_id)
        self.assertContains(receipt_res, rzp_payment_id)
        self.assertContains(receipt_res, "Razorpay")
        self.assertContains(receipt_res, "₹283.20")

        # Cart is now empty
        self.assertEqual(Cart.objects.filter(student=self.student).count(), 0)

        # Student dashboard & course detail recognize active enrollment
        dash_res = self.client.get(reverse('student:student_dashboard'))
        self.assertContains(dash_res, "Full Stack Python Mastery")
        self.assertContains(dash_res, "System Design Architecture")
        self.assertContains(dash_res, order.order_id)
        self.assertNotContains(dash_res, 'class="cs-dock-shell"')
        self.assertContains(dash_res, 'id="themeToggleBtn"')
        detail_res = self.client.get(reverse('student:course_detail', args=[self.course_one.id]))
        self.assertContains(detail_res, "Enrolled ✓")

        # Already enrolled course cannot be re-added to cart
        readd_res = self.client.post(reverse('student:add_to_cart', args=[self.course_one.id]), follow=True)
        self.assertContains(readd_res, "already enrolled")
        self.assertEqual(Cart.objects.filter(student=self.student).count(), 0)

    @override_settings(RAZORPAY_KEY_ID='rzp_test_unit_key', RAZORPAY_KEY_SECRET='unit_test_secret_123')
    @patch('Student.views.create_razorpay_order')
    def test_failed_and_cancelled_payment_does_not_enroll_and_updates_only_after_success(self, mock_create_rzp_order):
        # Pre-existing Pending enrollment record must NOT become Active until verified payment succeeds
        existing_enr = Enrollment.objects.create(
            student=self.student,
            course=self.course_one,
            status='Pending',
            payment_reference='',
        )

        mock_create_rzp_order.side_effect = [
            {'id': 'order_FAIL_SIG_1', 'amount': 11800, 'currency': 'INR'},
            {'id': 'order_FAIL_CANCEL_2', 'amount': 11800, 'currency': 'INR'},
            {'id': 'order_RETRY_SUCCESS_3', 'amount': 11800, 'currency': 'INR'},
        ]

        self.client.login(username='cart_student', password='Password123')
        self.client.post(reverse('student:add_to_cart', args=[self.course_one.id]))

        # Scenario A: Signature tampering fails backend verification
        self.client.post(self.checkout_url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        bad_verify = self.client.post(
            self.verify_url,
            data=json.dumps({
                'razorpay_order_id': 'order_FAIL_SIG_1',
                'razorpay_payment_id': 'pay_BAD_001',
                'razorpay_signature': 'invalid_tampered_signature',
            }),
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(bad_verify.status_code, 400)
        self.assertFalse(bad_verify.json()['ok'])
        self.assertEqual(Order.objects.get(razorpay_order_id='order_FAIL_SIG_1').status, 'FAILED')
        existing_enr.refresh_from_db()
        self.assertEqual(existing_enr.status, 'Pending')
        self.assertEqual(existing_enr.payment_reference, '')
        self.assertEqual(Cart.objects.filter(student=self.student).count(), 1)

        # Scenario B: Payment cancelled / failed via modal callback
        self.client.post(self.checkout_url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        fail_res = self.client.post(
            reverse('student:razorpay_failed'),
            data=json.dumps({'razorpay_order_id': 'order_FAIL_CANCEL_2', 'reason': 'Modal dismissed'}),
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(fail_res.status_code, 200)
        self.assertEqual(Order.objects.get(razorpay_order_id='order_FAIL_CANCEL_2').status, 'FAILED')
        existing_enr.refresh_from_db()
        self.assertEqual(existing_enr.status, 'Pending')
        self.assertEqual(Cart.objects.filter(student=self.student).count(), 1)

        # Scenario C: Retry succeeds -> updates existing Pending Enrollment record to Active
        self.client.post(self.checkout_url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        rzp_payment_id = 'pay_RETRY_OK_3'
        sig = hmac.new(
            b'unit_test_secret_123',
            f"order_RETRY_SUCCESS_3|{rzp_payment_id}".encode(),
            hashlib.sha256,
        ).hexdigest()
        ok_res = self.client.post(
            self.verify_url,
            data=json.dumps({
                'razorpay_order_id': 'order_RETRY_SUCCESS_3',
                'razorpay_payment_id': rzp_payment_id,
                'razorpay_signature': sig,
            }),
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(ok_res.status_code, 200)
        self.assertEqual(Enrollment.objects.filter(student=self.student, course=self.course_one).count(), 1)
        existing_enr.refresh_from_db()
        self.assertEqual(existing_enr.status, 'Active')
        self.assertEqual(existing_enr.payment_reference, rzp_payment_id)
        self.assertEqual(existing_enr.order.razorpay_order_id, 'order_RETRY_SUCCESS_3')

    @override_settings(RAZORPAY_KEY_ID='rzp_test_unit_key', RAZORPAY_KEY_SECRET='unit_test_secret_123')
    @patch('Student.views.create_razorpay_order')
    def test_duplicate_verification_and_replayed_payment_prevented(self, mock_create_rzp_order):
        mock_create_rzp_order.side_effect = [
            {'id': 'order_FIRST_100', 'amount': 11800, 'currency': 'INR'},
            {'id': 'order_SECOND_200', 'amount': 23600, 'currency': 'INR'},
        ]

        self.client.login(username='cart_student', password='Password123')
        self.client.post(reverse('student:add_to_cart', args=[self.course_one.id]))
        self.client.post(self.checkout_url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        sig1 = hmac.new(
            b'unit_test_secret_123',
            b"order_FIRST_100|pay_UNIQUE_100",
            hashlib.sha256,
        ).hexdigest()

        # First verification succeeds
        res1 = self.client.post(
            self.verify_url,
            data=json.dumps({
                'razorpay_order_id': 'order_FIRST_100',
                'razorpay_payment_id': 'pay_UNIQUE_100',
                'razorpay_signature': sig1,
            }),
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(res1.status_code, 200)
        self.assertFalse(res1.json()['duplicate'])

        # Duplicate verification callback for the same order returns idempotently without duplicating records
        res_dup = self.client.post(
            self.verify_url,
            data=json.dumps({
                'razorpay_order_id': 'order_FIRST_100',
                'razorpay_payment_id': 'pay_UNIQUE_100',
                'razorpay_signature': sig1,
            }),
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(res_dup.status_code, 200)
        self.assertTrue(res_dup.json()['duplicate'])
        self.assertEqual(Order.objects.filter(razorpay_order_id='order_FIRST_100').count(), 1)
        self.assertEqual(Enrollment.objects.filter(student=self.student, course=self.course_one).count(), 1)

        # Replay attack using the same razorpay_payment_id on a second course order must fail (409)
        self.client.post(reverse('student:add_to_cart', args=[self.course_two.id]))
        self.client.post(self.checkout_url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        sig_replay = hmac.new(
            b'unit_test_secret_123',
            b"order_SECOND_200|pay_UNIQUE_100",
            hashlib.sha256,
        ).hexdigest()
        replay_res = self.client.post(
            self.verify_url,
            data=json.dumps({
                'razorpay_order_id': 'order_SECOND_200',
                'razorpay_payment_id': 'pay_UNIQUE_100',
                'razorpay_signature': sig_replay,
            }),
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(replay_res.status_code, 409)
        self.assertTrue(replay_res.json()['duplicate'])
        self.assertFalse(Enrollment.objects.filter(student=self.student, course=self.course_two).exists())
        self.assertEqual(Order.objects.get(razorpay_order_id='order_SECOND_200').status, 'PENDING')


