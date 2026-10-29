import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In development the API runs separately on :8000; in production FastAPI serves this build.
export default defineConfig({
  plugins: [react()],
  build: { chunkSizeWarningLimit: 800 }, // single small app; charts library dominates
  server: {
    proxy: { "/api": process.env.VITE_API_PROXY ?? "http://localhost:8000" },
  },
});
