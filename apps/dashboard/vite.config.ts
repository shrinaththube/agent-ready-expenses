/// <reference types="vitest" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api/policy": { target: "http://localhost:8081", rewrite: (p) => p.replace(/^\/api\/policy/, "") },
      "/api/receipts": { target: "http://localhost:8082", rewrite: (p) => p.replace(/^\/api\/receipts/, "") },
    },
  },
  test: { include: ["test/**/*.test.ts"] },
});
