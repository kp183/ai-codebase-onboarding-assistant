# Checkout orchestration.
def checkout(items, inventory):
    if not items:
        raise ValueError("cart is empty")
    return {"total": sum(x["price"] for x in items), "inventory": inventory}
