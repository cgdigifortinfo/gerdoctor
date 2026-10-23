import { fileURLToPath } from 'node:url';
import { defineConfig, loadEnv, transformWithOxc } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig(({ mode, command }) => {
  const env = loadEnv(mode, process.cwd(), '');
  return {
    plugins: [
      {
        name: 'gerdoctor-jsx-in-js',
        enforce: 'pre',
        transform(code, id) {
          if (!id.includes('/src/') || !id.endsWith('.js')) return;
          return transformWithOxc(code, `${id}x`, {
            jsx: { runtime: 'automatic', development: command === 'serve' },
          });
        },
      },
      react(),
      tailwindcss(),
    ],
    resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
    // Expose only the existing public setting, never the full process environment.
    define: {
      'process.env.REACT_APP_BACKEND_URL': JSON.stringify(env.REACT_APP_BACKEND_URL || ''),
    },
    server: {
      host: env.HOST || 'localhost',
      port: Number(env.PORT || 3001),
      strictPort: true,
      proxy: {
        '/api': {
          target: env.API_PROXY_TARGET || env.REACT_APP_BACKEND_URL || 'http://localhost:8001',
          changeOrigin: true,
        },
      },
    },
    optimizeDeps: { rolldownOptions: { moduleTypes: { '.js': 'jsx' } } },
    build: {
      outDir: 'build',
      target: ['chrome111', 'edge111', 'firefox128', 'safari16.4'],
      rolldownOptions: {
        output: {
          codeSplitting: {
            groups: [
              { name: 'flow', test: /node_modules\/(?:@reactflow|reactflow|dagre|graphlib)\// },
              { name: 'react', test: /node_modules\/(?:react|react-dom|scheduler)\// },
              { name: 'ui', test: /node_modules\/(?:@radix-ui|@phosphor-icons|lucide-react)\// },
            ],
          },
        },
      },
    },
  };
});
