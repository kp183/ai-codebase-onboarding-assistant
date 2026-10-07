# Sample service demonstrating an onboarding-ready repository.
def calculate_total(items):
    """Return the sum of item prices."""
    return sum(item["price"] for item in items)
