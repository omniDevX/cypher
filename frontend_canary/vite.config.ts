import { readFileSync } from 'node:fs'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

const backendProject = readFileSync(new URL('../ontology_knowledgegraph/pyproject.toml', import.meta.url), 'utf8')
const appVersion = backendProject.match(/^version\s*=\s*"([^"]+)"/m)?.[1]
if (!appVersion) throw new Error('Backend project version is missing from pyproject.toml')

const deploymentId = (process.env.CF_PAGES_COMMIT_SHA ?? process.env.GITHUB_SHA ?? '').slice(0, 7)

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  define: {
    __APP_VERSION__: JSON.stringify(appVersion),
    __DEPLOYMENT_ID__: JSON.stringify(deploymentId),
  },
})
