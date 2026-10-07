// Filter visible products by name.
export function filterProducts(products, query) {
  return products.filter((product) => product.name.toLowerCase().includes(query.toLowerCase()));
}
