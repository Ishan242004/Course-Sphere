from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib import admin
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from Admin.models import Admin
from Instructor.models import Instructor, Course
from Student.models import Enrollment, Order, OrderItem, Student


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


class InstructorDashboardAndCourseTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.dashboard_url = reverse('instructor:instructor_dashboard')
        self.courses_url = reverse('instructor:instructor_courses')
        self.add_course_url = reverse('instructor:add_course')
        self.profile_url = reverse('instructor:instructor_profile')

        self.user_a = User.objects.create_user(
            username='prof_ananya',
            email='ananya@coursesphere.com',
            password='Password123',
            first_name='Ananya',
            last_name='Sharma',
        )
        self.instructor_a = Instructor.objects.create(
            user=self.user_a,
            phone='9876543210',
            specialization='Full-Stack Python',
            bio='12 years building distributed Python systems.',
        )

        self.user_b = User.objects.create_user(
            username='prof_vikram',
            email='vikram@coursesphere.com',
            password='Password123',
            first_name='Vikram',
            last_name='Desai',
        )
        self.instructor_b = Instructor.objects.create(
            user=self.user_b,
            specialization='UI Design',
        )

        self.course_a1 = Course.objects.create(
            course_title='Django Production Systems',
            category='Backend',
            price=Decimal('499.00'),
            status='Published',
            description='Deep dive into scalable Django architecture and deployment.',
            instructor=self.instructor_a,
        )
        self.course_a2 = Course.objects.create(
            course_title='Async Python Draft Workshop',
            category='Programming',
            price=Decimal('0.00'),
            status='Draft',
            description='Upcoming interactive workshop on Python asyncio patterns.',
            instructor=self.instructor_a,
        )
        self.course_b1 = Course.objects.create(
            course_title='Secret Instructor B Figma Lab',
            category='Design',
            price=Decimal('799.00'),
            status='Published',
            description='Private UI design mastery owned strictly by instructor B.',
            instructor=self.instructor_b,
        )

        stu1_user = User.objects.create_user(username='stu_one', email='s1@example.com', password='Password123', first_name='Karan', last_name='Patel')
        stu2_user = User.objects.create_user(username='stu_two', email='s2@example.com', password='Password123', first_name='Meera', last_name='Joshi')
        self.student1 = Student.objects.create(user=stu1_user, phone='9111111111', roll_number='STU-01')
        self.student2 = Student.objects.create(user=stu2_user, phone='9222222222', roll_number='STU-02')

        paid_order = Order.objects.create(
            student=self.student1,
            subtotal=Decimal('499.00'),
            tax_amount=Decimal('89.82'),
            total_amount=Decimal('588.82'),
            payment_method='RAZORPAY',
            razorpay_payment_id='pay_INST_TEST_01',
            status='PAID',
        )
        OrderItem.objects.create(
            order=paid_order,
            course=self.course_a1,
            course_title=self.course_a1.course_title,
            price=self.course_a1.price,
        )

        Enrollment.objects.create(
            student=self.student1,
            course=self.course_a1,
            order=paid_order,
            status='Active',
            payment_reference='pay_INST_TEST_01',
        )
        Enrollment.objects.create(
            student=self.student2,
            course=self.course_a1,
            status='Enrolled',
            payment_reference='ADMIN-MANUAL',
        )
        # Pending enrollment should NOT count in active enrolled students metric
        Enrollment.objects.create(
            student=self.student2,
            course=self.course_a2,
            status='Pending',
        )
        # Enrollment on Instructor B course should NOT leak into Instructor A metrics
        Enrollment.objects.create(
            student=self.student1,
            course=self.course_b1,
            status='Active',
        )

    def test_permissions_block_guests_students_and_non_instructors(self):
        # Guest redirected to instructor login across protected endpoints
        for url in [self.dashboard_url, self.courses_url, self.add_course_url, self.profile_url]:
            res = self.client.get(url)
            self.assertRedirects(res, f"{reverse('instructor:instructor_login')}?next={url}")

        # Student user denied access
        self.client.login(username='stu_one', password='Password123')
        res = self.client.get(self.dashboard_url, follow=True)
        self.assertRedirects(res, reverse('instructor:instructor_login'))
        self.assertContains(res, "Access denied")
        self.client.logout()

        # Admin without instructor_profile also denied access to instructor cockpit
        admin_user = User.objects.create_user(username='admin_only', password='Password123', is_staff=True)
        Admin.objects.create(user=admin_user, phone='9999999999')
        self.client.login(username='admin_only', password='Password123')
        res_admin = self.client.get(self.dashboard_url)
        self.assertRedirects(res_admin, reverse('instructor:instructor_login'))

    def test_instructor_dashboard_renders_real_profile_metrics_and_owned_courses_only(self):
        self.client.login(username='prof_ananya', password='Password123')
        res = self.client.get(self.dashboard_url)
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'Instructor/dashboard.html')

        # Profile identity & contact details
        self.assertContains(res, "Ananya Sharma")
        self.assertContains(res, "ananya@coursesphere.com")
        self.assertContains(res, "Full-Stack Python")
        self.assertContains(res, "9876543210")

        # Navigation links: Dashboard, My Courses, Add Course, Profile
        self.assertContains(res, reverse('instructor:instructor_dashboard'))
        self.assertContains(res, reverse('instructor:instructor_courses'))
        self.assertContains(res, reverse('instructor:add_course'))
        self.assertContains(res, reverse('instructor:instructor_profile'))
        self.assertContains(res, "Dashboard")
        self.assertContains(res, "My Courses")
        self.assertContains(res, "Add Course")
        self.assertContains(res, "Profile")

        # Real DB statistics strictly scoped to instructor_a
        stats = res.context['stats']
        self.assertEqual(stats['total_courses'], 2)
        self.assertEqual(stats['published_courses'], 1)
        self.assertEqual(stats['draft_courses'], 1)
        self.assertEqual(stats['total_enrollments'], 2)
        self.assertEqual(stats['unique_students'], 2)
        self.assertEqual(stats['total_revenue'], Decimal('499.00'))

        # Instructor's own courses with title, category, price, status shown
        self.assertContains(res, "Django Production Systems")
        self.assertContains(res, "Backend")
        self.assertContains(res, "₹499.00")
        self.assertContains(res, "Published")
        self.assertContains(res, "Async Python Draft Workshop")
        self.assertContains(res, "Draft")

        # Instructor Dashboard matches Student colors and omits top site navbar header
        self.assertNotContains(res, 'class="cs-dock-shell"')
        self.assertContains(res, 'id="themeToggleBtn"')
        self.assertNotContains(res, '#8B5CF6')
        self.assertNotContains(res, 'glass-btn-instructor')

        # Other instructor's course is NEVER exposed on dashboard or My Courses
        self.assertNotContains(res, "Secret Instructor B Figma Lab")
        courses_res = self.client.get(self.courses_url)
        self.assertEqual(courses_res.status_code, 200)
        self.assertContains(courses_res, "Django Production Systems")
        self.assertNotContains(courses_res, "Secret Instructor B Figma Lab")

    def test_instructor_course_crud_and_cross_instructor_isolation(self):
        self.client.login(username='prof_ananya', password='Password123')

        # Add Course automatically sets instructor=instructor_a
        add_res = self.client.post(self.add_course_url, {
            'course_title': 'Microservices with FastAPI',
            'category': 'Backend',
            'price': '299.00',
            'status': 'Published',
            'description': 'Design production-ready async APIs using FastAPI and Pydantic.',
        }, follow=True)
        self.assertRedirects(add_res, self.courses_url)
        created = Course.objects.get(course_title='Microservices with FastAPI')
        self.assertEqual(created.instructor, self.instructor_a)
        self.assertEqual(created.status, 'Published')

        # Edit own course
        edit_res = self.client.post(reverse('instructor:edit_course', args=[created.id]), {
            'course_title': 'Microservices with FastAPI Pro',
            'category': 'Backend',
            'price': '349.00',
            'status': 'Draft',
            'description': 'Updated syllabus with distributed tracing and Docker.',
        }, follow=True)
        self.assertRedirects(edit_res, self.courses_url)
        created.refresh_from_db()
        self.assertEqual(created.course_title, 'Microservices with FastAPI Pro')
        self.assertEqual(created.status, 'Draft')

        # View own course detail & active enrolled students
        detail_res = self.client.get(reverse('instructor:course_detail', args=[self.course_a1.id]))
        self.assertEqual(detail_res.status_code, 200)
        self.assertContains(detail_res, "Karan Patel")
        self.assertContains(detail_res, "₹499.00")

        # Cross-instructor isolation: prof_ananya CANNOT view, edit, or delete course_b1
        self.assertEqual(self.client.get(reverse('instructor:course_detail', args=[self.course_b1.id])).status_code, 404)
        self.assertEqual(self.client.get(reverse('instructor:edit_course', args=[self.course_b1.id])).status_code, 404)
        self.assertEqual(self.client.post(reverse('instructor:edit_course', args=[self.course_b1.id]), {
            'course_title': 'Hacked Title',
            'category': 'Hack',
            'price': '0.00',
            'status': 'Draft',
            'description': 'Unauthorized edit attempt.',
        }).status_code, 404)
        self.assertEqual(self.client.post(reverse('instructor:delete_course', args=[self.course_b1.id])).status_code, 404)
        self.course_b1.refresh_from_db()
        self.assertEqual(self.course_b1.course_title, 'Secret Instructor B Figma Lab')

        # Delete own course
        del_res = self.client.post(reverse('instructor:delete_course', args=[created.id]), follow=True)
        self.assertRedirects(del_res, self.courses_url)
        self.assertFalse(Course.objects.filter(id=created.id).exists())

    def test_instructor_profile_view_and_update(self):
        self.client.login(username='prof_ananya', password='Password123')
        res = self.client.post(self.profile_url, {
            'first_name': 'Dr. Ananya',
            'last_name': 'Verma',
            'email': 'ananya.verma@coursesphere.com',
            'phone': '9888877777',
            'specialization': 'Distributed Cloud & Python',
            'bio': 'Updated professor bio.',
        }, follow=True)
        self.assertRedirects(res, self.profile_url)
        self.instructor_a.refresh_from_db()
        self.assertEqual(self.instructor_a.user.first_name, 'Dr. Ananya')
        self.assertEqual(self.instructor_a.specialization, 'Distributed Cloud & Python')
        self.assertContains(res, "Updated professor bio.")


