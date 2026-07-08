import { defineConfig } from 'vite';
import path from 'node:path';
import electron from 'vite-plugin-electron/simple';
import react from '@vitejs/plugin-react';
// @ts-expect-error no @types
import SemiPlugin from 'vite-plugin-semi-theme';
import tailwindcss from '@tailwindcss/vite';
import { URL, fileURLToPath } from 'url';
import Icons from 'unplugin-icons/vite';
import { FileSystemIconLoader } from 'unplugin-icons/loaders';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(),
    electron({
      main: {
        entry: 'electron/main.ts',
        // 主进程配置为CJS格式
        vite: {
          build: {
            lib: {
              formats: ['cjs'],
              fileName: () => 'main.cjs',
            },
            rollupOptions: {
              output: {
                format: 'cjs',
                entryFileNames: 'main.cjs', // 主进程输出文件名
              },
            },
          },
        },
      },
      preload: {
        input: path.join(__dirname, 'electron/preload.ts'),
        // 预加载脚本配置为CJS格式
        vite: {
          build: {
            rollupOptions: {
              output: {
                format: 'cjs', // 预加载脚本输出为CJS
                entryFileNames: 'preload.cjs', // 预加载脚本输出文件名
              },
            },
          },
        },
      },
      renderer:
        process.env.NODE_ENV === 'test'
          ? undefined
          : {
              // 渲染进程通常保持ES模块格式
              // 如果需要也可以设置为cjs，但不推荐
              // format: 'cjs'
            },
    }),
    SemiPlugin({
      theme: '@semi-bot/semi-theme-zsim',
    }),
    tailwindcss(),
    Icons({
      compiler: 'jsx',
      jsx: 'react',
      customCollections: {
        zsim: FileSystemIconLoader('./src/assets/svgs'),
      },
    }),
  ],
  build: {
    rollupOptions: {
      // 全局输出配置，会被上面的具体配置覆盖
      output: {
        format: 'cjs', // 默认输出格式
      },
    },
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
});
