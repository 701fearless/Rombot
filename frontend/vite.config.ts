import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://127.0.0.1:8000",
      "/health": "http://127.0.0.1:8000",
      "/openapi.json": "http://127.0.0.1:8000",
      "/docs": "http://127.0.0.1:8000",
      "/redoc": "http://127.0.0.1:8000",
      "/outputs": "http://127.0.0.1:8000",
      "/sample_data": "http://127.0.0.1:8000",
      "/static": "http://127.0.0.1:8000",
    },
  },
})
