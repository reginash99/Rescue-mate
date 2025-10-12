import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const API_TARGET = env.VITE_API_URL || 'http://api:8000'  // docker-internal default

  return {
    plugins: [vue()],
    server: {
      host: '0.0.0.0',
      port: 5173,
      strictPort: true,
      proxy: {
        '/api': {
          target: API_TARGET,       // <- will be http://api:8000 in container
          changeOrigin: true,
          secure: false,
          rewrite: p => p.replace(/^\/api/, ''),
        },
      },
    },
    resolve: {
      alias: { '@': '/src' },
    },
    build: {
      outDir: 'dist',
      sourcemap: true,
    },
  }
})
