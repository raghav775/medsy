// Service Worker — caches OpenStreetMap tiles for offline use.
// Tiles are cached when first fetched; subsequent requests are served
// from cache even without internet.

const TILE_CACHE = "osm-tiles-v1";

// Only intercept OSM tile requests
self.addEventListener("fetch", (event) => {
  const url = event.request.url;
  if (!url.includes("tile.openstreetmap.org")) return;

  event.respondWith(
    caches.open(TILE_CACHE).then(async (cache) => {
      const cached = await cache.match(event.request);
      if (cached) return cached;

      try {
        const response = await fetch(event.request);
        if (response.ok) {
          cache.put(event.request, response.clone());
        }
        return response;
      } catch {
        // Offline and tile not in cache — return a transparent 1x1 tile
        return new Response(
          atob(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
          ),
          {
            headers: {
              "Content-Type": "image/png",
              "Cache-Control": "no-store",
            },
          }
        );
      }
    })
  );
});
