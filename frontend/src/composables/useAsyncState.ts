import { ref } from 'vue'
import { getErrorMessage } from '../api'

export function useAsyncState<TArgs extends unknown[], TData>(
  fetcher: (...args: TArgs) => Promise<TData>,
) {
  const data = ref<TData | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const execute = async (...args: TArgs): Promise<TData> => {
    loading.value = true
    error.value = null
    try {
      const result = await fetcher(...args)
      data.value = result
      return result
    } catch (err) {
      error.value = getErrorMessage(err)
      throw err
    } finally {
      loading.value = false
    }
  }

  return { data, loading, error, execute }
}
