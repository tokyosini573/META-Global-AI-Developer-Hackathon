import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  // The live interview API (python -m engine.serve)
  server: { proxy: { '/api': 'http://localhost:8787' } },
})
