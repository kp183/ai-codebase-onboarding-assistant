// Storefront API client.
export async function loadCatalog(fetcher) {
  const response = await fetcher('/api/catalog');
  return response.json();
}
