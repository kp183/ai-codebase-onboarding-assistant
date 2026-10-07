# In-memory catalog operations.
def find_product(products, product_id):
    return next((p for p in products if p["id"] == product_id), None)
