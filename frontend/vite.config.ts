import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

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
    plugins: [react(), tailwindcss()],
    server: {
      proxy: {
        "/api": { target: "http://localhost:8000", changeOrigin: true },
        "/ws": { target: "ws://localhost:8000", ws: true },
      },
    },
  };
});
