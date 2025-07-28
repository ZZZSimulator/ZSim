import path from 'node:path'
import Vue from '@vitejs/plugin-vue'
import { defineConfig, externalizeDepsPlugin } from 'electron-vite'
import UnoCSS from 'unocss/vite'
import AutoImport from 'unplugin-auto-import/vite'

export default defineConfig(() => {
  const dir = path.resolve(__dirname)
  return {
    main: {
      plugins: [externalizeDepsPlugin()],
    },
    preload: {
      plugins: [externalizeDepsPlugin()],
    },
    renderer: {
      resolve: {
        alias: {
          '@renderer': path.join(dir, 'src/renderer/src'),
          '@locales': path.join(dir, 'src/locales'),
          '@/hooks': path.join(dir, 'src/renderer/src/hooks'),
        },
      },
      plugins: [
        AutoImport({
          imports: ['vue'],
          dts: path.join(dir, 'src/renderer/types/auto-import.d.ts'),
        }),
        UnoCSS(),
        Vue(),
      ],
    },
  }
})
