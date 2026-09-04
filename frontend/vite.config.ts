import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { VitePWA } from "vite-plugin-pwa";

// MapLibre is code-split out of the entry bundle by the dynamic import in
// components/MapCanvas.tsx — ARCHITECTURE.md §14 load budget. No manualChunks
// entry: that produced an empty stub chunk alongside the real split.
export default defineConfig(({ command, mode }) => {
  const env = loadEnv(mode, process.cwd(), "");

  // Vite inlines import.meta.env at build time, so a production build made
  // without the key permanently drops the map: the guard in MapCanvas folds to
  // a constant and Rollup removes the dynamic import with it. Fail loudly
  // rather than shipping a 180 kB app with no basemap in it.
  if (command === "build" && !env.VITE_MAPID_BASEMAP_KEY) {
    throw new Error(
      "VITE_MAPID_BASEMAP_KEY is not set — the production build would ship without MapLibre. See frontend/.env.example.",
    );
  }

  return {
    plugins: [
      react(),
      tailwindcss(),
      // A repeat visit should not re-download 1.05MB of MapLibre. The service
      // worker precaches the shell and runtime-caches the third parties the app
      // reads from; /api is deliberately absent, because the in-app cache owns
      // that and stale transit data is worse than a request.
      VitePWA({
        registerType: "autoUpdate",
        // Off in dev so it cannot fight HMR or serve a stale module.
        devOptions: { enabled: false },
        includeAssets: ["favicon.ico"],
        manifest: {
          name: "PATHRIX",
          short_name: "PATHRIX",
          description: "Navigasi multimoda Yogyakarta",
          lang: "id",
          start_url: "/",
          display: "standalone",
          background_color: "#ffffff",
          theme_color: "#ffffff",
        },
        workbox: {
          // MapLibre alone is over the 2MB default.
          maximumFileSizeToCacheInBytes: 4 * 1024 * 1024,
          globPatterns: ["**/*.{js,css,html,woff2}"],
          navigateFallbackDenylist: [/^\/api/, /^\/ws/],
          runtimeCaching: [
            {
              urlPattern: /^https:\/\/v2\.basemap\.mapid\.io\/.*/i,
              handler: "CacheFirst",
              options: {
                cacheName: "mapid-basemap",
                expiration: { maxEntries: 600, maxAgeSeconds: 60 * 60 * 24 * 14 },
                cacheableResponse: { statuses: [0, 200] },
              },
            },
            {
              urlPattern: /^https:\/\/fonts\.(googleapis|gstatic)\.com\/.*/i,
              handler: "CacheFirst",
              options: {
                cacheName: "google-fonts",
                expiration: { maxEntries: 20, maxAgeSeconds: 60 * 60 * 24 * 365 },
                cacheableResponse: { statuses: [0, 200] },
              },
            },
            {
              urlPattern: /^https:\/\/(id\.wikipedia\.org|thumb\.wikimedia\.org|upload\.wikimedia\.org)\/.*/i,
              handler: "CacheFirst",
              options: {
                cacheName: "place-photos",
                expiration: { maxEntries: 120, maxAgeSeconds: 60 * 60 * 24 * 30 },
                cacheableResponse: { statuses: [0, 200] },
              },
            },
            {
              urlPattern: /^https:\/\/api\.dicebear\.com\/.*/i,
              handler: "CacheFirst",
              options: {
                cacheName: "avatars",
                expiration: { maxEntries: 40, maxAgeSeconds: 60 * 60 * 24 * 90 },
                cacheableResponse: { statuses: [0, 200] },
              },
            },
          ],
        },
      }),
    ],
    server: {
      proxy: {
        "/api": { target: "http://localhost:8000", changeOrigin: true },
        "/ws": { target: "ws://localhost:8000", ws: true },
      },
    },
  };
});
