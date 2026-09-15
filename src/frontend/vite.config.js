import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // In production (Railway), the FastAPI server serves the built files
  // from the same origin, so /api calls go to the same host — no proxy needed.
  // In local dev, Vite proxies /api to the FastAPI dev server on port 8001.
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
    },
  },
  build: {
    // Output into src/frontend/dist — FastAPI serves this as static files
    outDir: 'dist',
    emptyOutDir: true,
  },
})
