import {defineConfig} from 'vite';
import react from '@vitejs/plugin-react';
export default defineConfig({
  plugins:[react()],
  server:{proxy:{'/api':process.env.API_PROXY || 'http://127.0.0.1:8000'}},
  build:{rollupOptions:{output:{manualChunks(id){
    if(!id.includes('node_modules'))return;
    if(/recharts|d3-|victory|react-smooth|lodash|decimal\.js/.test(id))return 'charts';
    if(/\/node_modules\/(react|react-dom|scheduler)\//.test(id))return 'react';
  }}}},
  test:{environment:'jsdom'}
});
