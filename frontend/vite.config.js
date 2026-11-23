import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The dev server proxies /api calls to Flask so the browser only talks to one
// origin. In production, Nginx performs the same job (see docker/nginx.conf).
export default defineConfig({
  plugins: [react()],
  build: {
    // ECharts is intentionally kept in its own cached chunk (~540 KB).
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      output: {
        // Keep heavy chart/map libraries out of the main application bundle.
        manualChunks(id) {
          if (id.includes('node_modules/echarts') || id.includes('node_modules/zrender')) {
            return 'echarts'
          }
          if (id.includes('node_modules/leaflet') || id.includes('node_modules/react-leaflet')) {
            return 'leaflet'
          }
          if (id.includes('node_modules/react-dom') || id.includes('node_modules/react/')) {
            return 'react'
          }
          return undefined
        },
      },
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
    },
  },
})
