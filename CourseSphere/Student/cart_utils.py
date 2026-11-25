from decimal import Decimal, ROUND_HALF_UP

GST_RATE = Decimal('0.18')

VALID_COUPONS = {
    'SPHERE10': {'rate': Decimal('0.10'), 'percent': 10, 'label': '10% Welcome Discount'},
    'WELCOME15': {'rate': Decimal('0.15'), 'percent': 15, 'label': '15% Learner Discount'},
    'SPHERE20': {'rate': Decimal('0.20'), 'percent': 20, 'label': '20% Pro Bundle Discount'},
}


def quantize_money(value: Decimal) -> Decimal:
    return value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def normalize_coupon(code: str | None) -> str:
    return (code or '').strip().upper()


def calculate_cart_summary(cart_items, coupon_code: str | None = None) -> dict:
    """
    Calculate complete itemized pricing and payment breakdown for cart items.
    Uses Decimal ROUND_HALF_UP arithmetic across subtotal, promo discount, and 18% GST.
    """
    items = list(cart_items)
    item_count = len(items)
    free_count = sum(1 for item in items if item.course.price == Decimal('0.00'))
    paid_count = item_count - free_count

    subtotal = quantize_money(sum((item.course.price for item in items), Decimal('0.00')))

    normalized_code = normalize_coupon(coupon_code)
    coupon_info = VALID_COUPONS.get(normalized_code)

    if coupon_info and subtotal > Decimal('0.00'):
        discount_amount = quantize_money(subtotal * coupon_info['rate'])
        discount_percent = coupon_info['percent']
        coupon_label = coupon_info['label']
        active_coupon = normalized_code
    else:
        discount_amount = Decimal('0.00')
        discount_percent = 0
        coupon_label = ''
        active_coupon = ''

    taxable_amount = quantize_money(max(Decimal('0.00'), subtotal - discount_amount))
    tax_amount = quantize_money(taxable_amount * GST_RATE) if taxable_amount > Decimal('0.00') else Decimal('0.00')
    total_amount = quantize_money(taxable_amount + tax_amount)

    return {
        'items': items,
        'item_count': item_count,
        'free_count': free_count,
        'paid_count': paid_count,
        'subtotal': subtotal,
        'discount_amount': discount_amount,
        'discount_percent': discount_percent,
        'taxable_amount': taxable_amount,
        'tax_rate_percent': 18,
        'tax_amount': tax_amount,
        'total_amount': total_amount,
        'coupon_code': active_coupon,
        'coupon_label': coupon_label,
        'is_free_order': total_amount == Decimal('0.00'),
    }
