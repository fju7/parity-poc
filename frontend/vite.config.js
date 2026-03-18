import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { execSync } from 'child_process'

const gitCommit = (() => {
  try {
    return execSync('git rev-parse --short HEAD', { encoding: 'utf-8' }).trim()
  } catch {
    return 'unknown'
  }
})()

export default defineConfig({
  plugins: [react(), tailwindcss()],
  define: {
    __GIT_COMMIT__: JSON.stringify(gitCommit),
    __BUILD_TIME__: JSON.stringify(new Date().toISOString()),
  },
  test: {
    setupFiles: ['./src/test-setup.js'],
  },
})
