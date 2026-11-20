from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import (
    MinLengthValidator,
    MinValueValidator,
    FileExtensionValidator,
)
from django.core.exceptions import ValidationError


def validate_image_size(value):
    max_size = 5 * 1024 * 1024  # 5 MB
    if value and hasattr(value, 'size') and value.size > max_size:
        raise ValidationError("Course image file size cannot exceed 5MB.")


class Instructor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='instructor_profile')
    phone = models.CharField(max_length=15, blank=True, null=True)
    specialization = models.CharField(max_length=100, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} ({self.specialization or 'Instructor'})"


class CourseQuerySet(models.QuerySet):
    def _map_kwargs(self, kwargs):
        mapping = {
            'title': 'course_title',
            'image': 'course_image',
            'created_at': 'created_date',
        }
        new_kwargs = {}
        for k, v in kwargs.items():
            mapped = False
            for key, target in mapping.items():
                if k == key:
                    new_kwargs[target] = v
                    mapped = True
                    break
                elif k.startswith(f"{key}__"):
                    new_kwargs[f"{target}__{k[len(key)+2:]}"] = v
                    mapped = True
                    break
            if not mapped:
                new_kwargs[k] = v
        return new_kwargs

    def filter(self, *args, **kwargs):
        return super().filter(*args, **self._map_kwargs(kwargs))

    def exclude(self, *args, **kwargs):
        return super().exclude(*args, **self._map_kwargs(kwargs))


class CourseManager(models.Manager):
    def get_queryset(self):
        return CourseQuerySet(self.model, using=self._db)

    def create(self, **kwargs):
        if 'title' in kwargs and 'course_title' not in kwargs:
            kwargs['course_title'] = kwargs.pop('title')
        if 'image' in kwargs and 'course_image' not in kwargs:
            kwargs['course_image'] = kwargs.pop('image')
        if 'created_at' in kwargs and 'created_date' not in kwargs:
            kwargs['created_date'] = kwargs.pop('created_at')
        return super().create(**kwargs)


class Course(models.Model):
    course_title = models.CharField(
        max_length=200,
        verbose_name="Course Title",
        validators=[MinLengthValidator(3, message="Course title must be at least 3 characters long.")],
        help_text="Enter a descriptive course title (minimum 3 characters)."
    )
    category = models.CharField(
        max_length=100,
        verbose_name="Category",
        validators=[MinLengthValidator(2, message="Category must be at least 2 characters long.")],
        help_text="Enter the course category or domain (e.g. Web Development, Data Science)."
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Price",
        validators=[MinValueValidator(Decimal('0.00'), message="Price cannot be negative.")],
        help_text="Course price in currency units (set 0.00 for free courses)."
    )
    description = models.TextField(
        verbose_name="Description",
        validators=[MinLengthValidator(10, message="Description must be at least 10 characters long.")],
        help_text="Detailed overview of what the course covers (minimum 10 characters)."
    )
    course_image = models.ImageField(
        upload_to='courses/images/',
        blank=True,
        null=True,
        verbose_name="Course Image",
        validators=[
            FileExtensionValidator(
                allowed_extensions=['jpg', 'jpeg', 'png', 'webp', 'gif'],
                message="Only jpg, jpeg, png, webp, and gif formats are allowed."
            ),
            validate_image_size
        ],
        help_text="Optional banner or thumbnail image for the course (max 5MB)."
    )
    created_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created Date"
    )
    instructor = models.ForeignKey(
        Instructor,
        on_delete=models.CASCADE,
        related_name='courses',
        blank=True,
        null=True,
        verbose_name="Instructor",
        help_text="Associated instructor profile (optional/reusable)."
    )

    objects = CourseManager()

    class Meta:
        verbose_name = "Course"
        verbose_name_plural = "Courses"
        ordering = ['-created_date']

    def __init__(self, *args, **kwargs):
        if 'title' in kwargs and 'course_title' not in kwargs:
            kwargs['course_title'] = kwargs.pop('title')
        if 'image' in kwargs and 'course_image' not in kwargs:
            kwargs['course_image'] = kwargs.pop('image')
        if 'created_at' in kwargs and 'created_date' not in kwargs:
            kwargs['created_date'] = kwargs.pop('created_at')
        super().__init__(*args, **kwargs)

    @property
    def title(self):
        return self.course_title

    @title.setter
    def title(self, value):
        self.course_title = value

    @property
    def image(self):
        return self.course_image

    @image.setter
    def image(self, value):
        self.course_image = value

    @property
    def created_at(self):
        return self.created_date

    @created_at.setter
    def created_at(self, value):
        self.created_date = value

    def clean(self):
        super().clean()
        if self.course_title and not self.course_title.strip():
            raise ValidationError({'course_title': 'Course title cannot be empty or just whitespace.'})
        if self.category and not self.category.strip():
            raise ValidationError({'category': 'Category cannot be empty or just whitespace.'})
        if self.description and not self.description.strip():
            raise ValidationError({'description': 'Description cannot be empty or just whitespace.'})
        if self.price is not None and self.price < Decimal('0.00'):
            raise ValidationError({'price': 'Price cannot be negative.'})

    def __str__(self):
        return self.course_title


_orig_course_get_field = Course._meta.get_field


def _aliased_course_get_field(field_name):
    aliases = {
        'title': 'course_title',
        'image': 'course_image',
        'created_at': 'created_date',
    }
    return _orig_course_get_field(aliases.get(field_name, field_name))


Course._meta.get_field = _aliased_course_get_field
