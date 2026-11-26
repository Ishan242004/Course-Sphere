from decimal import Decimal
from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from Admin.models import Admin
from Instructor.models import Course, Instructor
from Student.models import Enrollment, Order, Student


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


class AdminEntitiesCRUDTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_user(
            username='crud_admin',
            email='crud_admin@coursesphere.com',
            password='AdminPassword123',
        )
        Admin.objects.create(user=self.admin_user, phone='9999999999')
        self.client.login(username='crud_admin', password='AdminPassword123')

    def test_sidebar_and_dashboard_expose_students_instructors_and_receipts(self):
        response = self.client.get(reverse('admin_portal:admin_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('admin_portal:student_list'))
        self.assertContains(response, reverse('admin_portal:instructor_list'))
        self.assertContains(response, reverse('admin_portal:receipt_list'))
        self.assertContains(response, "All Students")
        self.assertContains(response, "All Instructors")
        self.assertContains(response, "Payment Receipts")

    def test_admin_student_full_crud(self):
        # Create
        create_res = self.client.post(reverse('admin_portal:add_student'), {
            'first_name': 'Neha',
            'last_name': 'Verma',
            'username': 'neha_v',
            'email': 'neha@example.com',
            'password': 'StrongPassword123',
            'confirm_password': 'StrongPassword123',
            'is_active': 'on',
            'roll_number': 'STU-501',
            'phone': '9123456789',
        }, follow=True)
        self.assertRedirects(create_res, reverse('admin_portal:student_list'))
        student = Student.objects.get(user__username='neha_v')
        self.assertEqual(student.roll_number, 'STU-501')

        # Read (List & Detail)
        list_res = self.client.get(reverse('admin_portal:student_list'), {'q': 'STU-501'})
        self.assertContains(list_res, 'Neha Verma')
        detail_res = self.client.get(reverse('admin_portal:student_detail', args=[student.id]))
        self.assertEqual(detail_res.status_code, 200)
        self.assertContains(detail_res, 'STU-501')

        # Update
        edit_res = self.client.post(reverse('admin_portal:edit_student', args=[student.id]), {
            'first_name': 'Neha',
            'last_name': 'Kapoor',
            'username': 'neha_v',
            'email': 'neha@example.com',
            'password': '',
            'confirm_password': '',
            'is_active': 'on',
            'roll_number': 'STU-509',
            'phone': '9123456780',
        }, follow=True)
        self.assertRedirects(edit_res, reverse('admin_portal:student_list'))
        student.refresh_from_db()
        self.assertEqual(student.user.last_name, 'Kapoor')
        self.assertEqual(student.roll_number, 'STU-509')

        # Delete
        del_res = self.client.post(reverse('admin_portal:delete_student', args=[student.id]), follow=True)
        self.assertRedirects(del_res, reverse('admin_portal:student_list'))
        self.assertFalse(Student.objects.filter(id=student.id).exists())
        self.assertFalse(User.objects.filter(username='neha_v').exists())

    def test_admin_instructor_full_crud(self):
        # Create
        create_res = self.client.post(reverse('admin_portal:add_instructor'), {
            'first_name': 'Dr. Aarav',
            'last_name': 'Mehta',
            'username': 'aarav_prof',
            'email': 'aarav@example.com',
            'password': 'ProfPassword123',
            'confirm_password': 'ProfPassword123',
            'is_active': 'on',
            'specialization': 'Cloud Architecture',
            'phone': '9811122233',
            'bio': '10 years teaching distributed cloud systems.',
        }, follow=True)
        self.assertRedirects(create_res, reverse('admin_portal:instructor_list'))
        inst = Instructor.objects.get(user__username='aarav_prof')

        # Read (List & Detail)
        list_res = self.client.get(reverse('admin_portal:instructor_list'), {'specialization': 'Cloud Architecture'})
        self.assertContains(list_res, 'aarav_prof')
        detail_res = self.client.get(reverse('admin_portal:instructor_detail', args=[inst.id]))
        self.assertContains(detail_res, 'Cloud Architecture')

        # Update
        self.client.post(reverse('admin_portal:edit_instructor', args=[inst.id]), {
            'first_name': 'Prof. Aarav',
            'last_name': 'Mehta',
            'username': 'aarav_prof',
            'email': 'aarav@example.com',
            'password': '',
            'confirm_password': '',
            'is_active': 'on',
            'specialization': 'Kubernetes & DevOps',
            'phone': '9811122233',
            'bio': 'Updated faculty bio.',
        }, follow=True)
        inst.refresh_from_db()
        self.assertEqual(inst.specialization, 'Kubernetes & DevOps')

        # Delete
        self.client.post(reverse('admin_portal:delete_instructor', args=[inst.id]), follow=True)
        self.assertFalse(Instructor.objects.filter(id=inst.id).exists())

    def test_admin_payment_receipt_full_crud(self):
        s_user = User.objects.create_user(username='pay_stu', email='pay_stu@example.com', password='Password123')
        student = Student.objects.create(user=s_user, phone='9876500001', roll_number='STU-R1')
        c1 = Course.objects.create(course_title='Django API Pro', category='Backend', price=Decimal('100.00'), description='Build clean Django REST APIs.')
        c2 = Course.objects.create(course_title='React UI Lab', category='Frontend', price=Decimal('200.00'), description='Modern component design in React.')

        # Create Paid Receipt (100 - 10% = 90 + 18% GST = 106.20)
        create_res = self.client.post(reverse('admin_portal:add_receipt'), {
            'student': student.id,
            'courses': [c1.id],
            'coupon_code': 'SPHERE10',
            'payment_method': 'RAZORPAY',
            'status': 'PAID',
            'razorpay_order_id': 'order_ADMIN_001',
            'razorpay_payment_id': 'pay_ADMIN_001',
        }, follow=True)
        self.assertEqual(create_res.status_code, 200)
        order = Order.objects.get(student=student)
        self.assertEqual(order.total_amount, Decimal('106.20'))
        self.assertEqual(order.status, 'PAID')
        enr1 = Enrollment.objects.get(student=student, course=c1)
        self.assertEqual(enr1.status, 'Active')
        self.assertEqual(enr1.payment_reference, 'pay_ADMIN_001')

        # Read (List & Detail)
        list_res = self.client.get(reverse('admin_portal:receipt_list'), {'q': order.order_id})
        self.assertContains(list_res, order.order_id)
        self.assertContains(list_res, '₹106.20')

        # Update (Change courses & status)
        edit_res = self.client.post(reverse('admin_portal:edit_receipt', args=[order.order_id]), {
            'student': student.id,
            'courses': [c2.id],
            'coupon_code': '',
            'payment_method': 'RAZORPAY',
            'status': 'PAID',
            'razorpay_order_id': 'order_ADMIN_001',
            'razorpay_payment_id': 'pay_ADMIN_001',
        }, follow=True)
        self.assertEqual(edit_res.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.total_amount, Decimal('236.00'))
        self.assertFalse(Enrollment.objects.filter(student=student, course=c1).exists())
        self.assertTrue(Enrollment.objects.filter(student=student, course=c2, status='Active').exists())

        # Delete
        del_res = self.client.post(reverse('admin_portal:delete_receipt', args=[order.order_id]), follow=True)
        self.assertRedirects(del_res, reverse('admin_portal:receipt_list'))
        self.assertFalse(Order.objects.filter(order_id=order.order_id).exists())
        self.assertFalse(Enrollment.objects.filter(student=student, course=c2).exists())


