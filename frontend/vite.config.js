/**
 * File: vite.config.js
 * Description: Vite development server and API proxy configuration.
 * Author: zhangdadi
 * Created: 2026-03-10
 */

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8003',
        changeOrigin: true
      }
    }
  }
})
