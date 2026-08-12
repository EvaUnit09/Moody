import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/setupTests.ts'],
    // Node's built-in experimental `localStorage` global shadows jsdom's
    // window.localStorage in newer Node versions unless disabled here.
    env: { NODE_OPTIONS: '--no-experimental-webstorage' },
  },
})
