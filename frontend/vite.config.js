import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/query':        'http://localhost:8000',
      '/health':       'http://localhost:8000',
      '/dataset':      'http://localhost:8000',
      '/suggestions':  'http://localhost:8000',
      '/export':       'http://localhost:8000',
    }
  }
})