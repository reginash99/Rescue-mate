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
    '^/transcribe-audio/?$': {
      target: 'http://127.0.0.1:8000',   // or 8001 if that’s your backend
      changeOrigin: true,
    },
    '^/geocode/?$': {
      target: 'http://127.0.0.1:8000',
      changeOrigin: true,
    },
      '^/get-history/?$':{
      target: 'http://127.0.0.1:8000',
      changeOrigin: true,
      
    }
  },
},



})


