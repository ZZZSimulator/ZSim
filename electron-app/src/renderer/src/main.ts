import type { LocaleKeys, MessageSchema } from '@locales/index'
import { enUS, zhCN } from '@locales/index'
import { createApp } from 'vue'
import { createI18n } from 'vue-i18n'
import App from './App.vue'
import 'virtual:uno.css'
import '@unocss/reset/tailwind.css'
import '@unocss/reset/tailwind-compat.css'

const i18n = createI18n<[MessageSchema], LocaleKeys>({
  locale: 'zh-CN',
  fallbackLocale: 'zh-CN',
  messages: {
    'en-US': enUS,
    'zh-CN': zhCN,
  },
})

const app = createApp(App)
app.use(i18n)
app.mount('#app')
