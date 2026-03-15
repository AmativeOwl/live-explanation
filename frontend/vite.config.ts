import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
    },
  },
})

// Now to fetch connection to backend we can do fetch('/api/items') instead of fetch('http://localhost:8000/api/items') 
// preventing CORS issues.

// const ws = new WebSocket('ws://localhost:5173/ws')  ---> How to make 