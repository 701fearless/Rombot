import path from 'node:path'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { '@': path.resolve(__dirname, 'src') } },
  server: { proxy: Object.fromEntries(['/api', '/outputs', '/sample_data', '/static'].map((prefix) => [prefix, 'http://127.0.0.1:8000'])) },
})
