from decimal import Decimal
import uuid
from django.db import models
from django.contrib.auth.models import User
from Instructor.models import Course


class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    phone = models.CharField(max_length=15, blank=True, null=True)
    roll_number = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} ({self.roll_number or 'Student'})"


class Cart(models.Model):
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='cart_items',
        verbose_name='Student',
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='cart_items',
        verbose_name='Course',
    )
    added_at = models.DateTimeField(auto_now_add=True, verbose_name='Added At')

    class Meta:
        verbose_name = 'Cart'
        verbose_name_plural = 'Carts'
        ordering = ['-added_at']
        constraints = [
            models.UniqueConstraint(fields=['student', 'course'], name='unique_student_course_cart'),
        ]

    def __str__(self):
        return f"{self.student.user.username} - {self.course.course_title}"


def generate_order_id():
    return f"CS-{uuid.uuid4().hex[:10].upper()}"


class Order(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('UPI', 'UPI / QR Payment'),
        ('CARD', 'Credit / Debit Card'),
        ('NETBANKING', 'Net Banking'),
        ('FREE', 'Free Enrollment'),
    ]
    STATUS_CHOICES = [
        ('PAID', 'Paid'),
        ('PENDING', 'Pending'),
        ('FAILED', 'Failed'),
    ]

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='orders',
        verbose_name='Student',
    )
    order_id = models.CharField(
        max_length=32,
        unique=True,
        default=generate_order_id,
        editable=False,
        verbose_name='Order ID',
    )
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    coupon_code = models.CharField(max_length=32, blank=True, default='')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='CARD')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PAID')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.order_id} ({self.student.user.username} - ₹{self.total_amount})"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, related_name='order_items')
    course_title = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    def __str__(self):
        return f"{self.order.order_id}: {self.course_title}"


class Enrollment(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True, related_name='enrollments')
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-enrolled_at']
        constraints = [
            models.UniqueConstraint(fields=['student', 'course'], name='unique_student_course_enrollment'),
        ]

    def __str__(self):
        return f"{self.student.user.username} -> {self.course.course_title}"
