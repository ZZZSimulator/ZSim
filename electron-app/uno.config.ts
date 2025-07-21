import { defineConfig } from 'unocss'
import presetWind4 from '@unocss/preset-wind4'
import { presetScrollbarHide } from 'unocss-preset-scrollbar-hide'

export default defineConfig({
  presets: [
    presetWind4(),
    presetScrollbarHide(),
  ],
})
