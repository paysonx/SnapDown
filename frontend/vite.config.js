import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  resolve: {
    // 避免 Vite 在 Windows 上通过子进程解析真实路径
    preserveSymlinks: true,
  },
  server: {
    port: 5173,
    proxy: {
      // 开发模式下将 /api 转发到 FastAPI 后端
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
