import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/chat': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/product-hierarchy': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/product-lines': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/upload-file': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/categories': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/products': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/files': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      }
    }
  }
})
