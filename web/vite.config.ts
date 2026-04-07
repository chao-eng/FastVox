import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import path from 'path';

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8047',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '/api/v1'), // 转发到后端 API
      },
      '/ws': {
        target: 'http://localhost:8047',
        ws: true,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/ws/, '/api/v1/tts/stream'), // 转发到后端 WebSocket
      },
    },
  },
});
