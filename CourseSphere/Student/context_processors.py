from decimal import Decimal
from .models import Cart, Enrollment
from .cart_utils import calculate_cart_summary


def cart_context(request):
    """Inject live student cart count, payment total, cart course IDs, and enrolled IDs globally."""
    user = getattr(request, 'user', None)
    if user and user.is_authenticated and hasattr(user, 'student_profile'):
        student = user.student_profile
        items = list(Cart.objects.filter(student=student).select_related('course'))
        coupon_code = request.session.get('cart_coupon', '')
        summary = calculate_cart_summary(items, coupon_code=coupon_code)
        enrolled_ids = set(
            Enrollment.objects.filter(
                student=student,
                status__in=Enrollment.ACTIVE_STATUSES,
            ).values_list('course_id', flat=True)
        )
        return {
            'cart_count': summary['item_count'],
            'cart_subtotal': summary['subtotal'],
            'cart_total_amount': summary['total_amount'],
            'cart_course_ids': {item.course_id for item in items},
            'enrolled_course_ids': enrolled_ids,
        }

    return {
        'cart_count': 0,
        'cart_subtotal': Decimal('0.00'),
        'cart_total_amount': Decimal('0.00'),
        'cart_course_ids': set(),
        'enrolled_course_ids': set(),
    }
