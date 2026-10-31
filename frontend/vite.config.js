import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  test: { environment: "jsdom" },
  build: {
    rollupOptions: {
      output: {
        // keep big libraries in their own cacheable chunks
        manualChunks: {
          react: ["react", "react-dom", "react-router-dom"],
          charts: ["recharts"],
        },
      },
    },
  },
});
