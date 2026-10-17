import { message } from 'ant-design-vue'
import { t } from '../i18n'

function fallbackCopy(text: string): boolean {
  try {
    const textarea = document.createElement('textarea')
    textarea.value = text
    textarea.style.position = 'fixed'
    textarea.style.opacity = '0'
    document.body.appendChild(textarea)
    textarea.select()
    const ok = document.execCommand('copy')
    document.body.removeChild(textarea)
    return ok
  } catch {
    return false
  }
}

export function useClipboard() {
  const copyToClipboard = async (text: string) => {
    try {
      let copied = false
      if (navigator.clipboard?.writeText) {
        try {
          await navigator.clipboard.writeText(text)
          copied = true
        } catch {
          copied = fallbackCopy(text)
        }
      } else {
        copied = fallbackCopy(text)
      }
      if (!copied) {
        throw new Error('clipboard unavailable')
      }
      message.success(t('common.copied'))
    } catch {
      message.error(t('common.copyFailed'))
    }
  }

  return { copyToClipboard }
}
