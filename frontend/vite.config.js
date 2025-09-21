import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  server: {
    proxy: {
      // FastAPI endpoints
      '/geocode': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
      },
      '/transcribe-audio': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
      },
    },
  },
})
