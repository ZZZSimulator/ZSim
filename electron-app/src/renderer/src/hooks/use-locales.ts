import type { MessageSchema } from '@locales/index'
import { useI18n } from 'vue-i18n'

export const useLocales = () => {
  const { t, ...rest } = useI18n<{
    message: MessageSchema
  }, 'en-US' | 'zh-CN'>()

  return { t, ...rest }
}
