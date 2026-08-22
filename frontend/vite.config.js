import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Proxies API calls to the FastAPI backend running on :8000
// so the React dev server (:5173) can call /query, /ingest, /status
// without CORS friction during development.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/query": "http://127.0.0.1:8000",
      "/ingest": "http://127.0.0.1:8000",
      "/status": "http://127.0.0.1:8000",
    },
  },
});
