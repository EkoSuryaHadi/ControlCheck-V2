import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '.', 'CONTROLCHECK_');
  return {
    plugins: [react()],
    server: {
      port: 5173,
      strictPort: true,
      proxy: { '/api': env.CONTROLCHECK_API_URL || 'http://127.0.0.1:8000' },
    },
  };
});

