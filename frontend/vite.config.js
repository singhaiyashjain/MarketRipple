import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  base: process.env.VITE_BASE || '/',   // GitHub Pages serves from /<repo-name>/
  plugins: [react()],
  resolve: { alias: { '@contracts': path.resolve(__dirname, '../contracts') } },
  server: {
    fs: { allow: ['..'] },
    proxy: { '/api': 'http://localhost:8000' },
  },
  build: { chunkSizeWarningLimit: 2000 },
})
