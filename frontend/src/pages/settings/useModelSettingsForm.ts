/** @description 管理供应商目录、测试凭证和保存，连接变化时丢弃旧目录。 */
import { useRef, useState } from 'react'
import { App, Form } from 'antd'
import { ApiError, errorMessage } from '../../api/client'
import {
  fetchModelCatalog,
  saveModelProfile,
  testModelSettings,
} from '../../api/services/modelSettings'
import type {
  ModelCatalogInput,
  ModelLibrary,
  ModelProfile,
} from '../../api/services/modelSettings'
import { useRequestScope } from '../../hooks/useRequestScope'

interface ModelFields {
  address: string
  model?: string
  apiKey?: string
}

/** 目录只反映表单当前凭证，模型可用性仍须在发布前测试。 */
export function useModelSettingsForm(
  profile: ModelProfile | undefined,
  credential: ModelProfile | undefined,
  version: number,
  onSaved: (library: ModelLibrary) => void,
) {
  const { message } = App.useApp()
  const [form] = Form.useForm<ModelFields>()
  const address = Form.useWatch('address', form) ?? credential?.address ?? ''
  const model = Form.useWatch('model', form)
  const [catalog, setCatalog] = useState<string[] | null>(null)
  const [testToken, setTestToken] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [needsReload, setNeedsReload] = useState(false)
  const [pending, setPending] = useState<'catalog' | 'test' | 'save' | null>(null)
  const busy = useRef(false)
  const revision = useRef(0)
  const begin = useRequestScope()
  const canReuseKey =
    Boolean(credential?.has_api_key) &&
    address.trim().replace(/\/+$/, '') === credential?.address.replace(/\/+$/, '')

  function credentials(values: ModelFields): ModelCatalogInput {
    return {
      address: values.address.trim(),
      api_key: values.apiKey?.trim() || undefined,
      version,
      credential_profile_id: credential?.id,
    }
  }

  function changed(fields: Partial<ModelFields>) {
    // 地址或密钥变更后清除旧供应商的选择，单独换模型时仍可使用当前目录。
    if ('address' in fields || 'apiKey' in fields) {
      setCatalog(null)
      form.setFieldValue('model', undefined)
    }
    invalidateTest()
  }

  function invalidateTest() {
    revision.current += 1
    setTestToken(null)
    setError('')
  }

  async function perform(
    kind: 'catalog' | 'test' | 'save',
    operation: (signal: AbortSignal) => Promise<void>,
  ) {
    if (busy.current) return
    const scope = begin()
    busy.current = true
    setError('')
    setPending(kind)
    try {
      await operation(scope.signal)
    } catch (reason: unknown) {
      if (scope.signal.aborted) return
      setTestToken(null)
      setError(errorMessage(reason))
      setNeedsReload(reason instanceof ApiError && reason.code === 'MODEL_SETTINGS_CONFLICT')
    } finally {
      scope.complete()
      busy.current = false
      if (!scope.signal.aborted) setPending(null)
    }
  }

  async function loadCatalog() {
    if (busy.current) return
    const requestedRevision = revision.current
    const values = await form.validateFields(['address', 'apiKey']).catch(() => null)
    if (!values || requestedRevision !== revision.current) return
    await perform('catalog', async (signal) => {
      const { models } = await fetchModelCatalog(credentials(values), signal)
      if (signal.aborted || requestedRevision !== revision.current) return
      setCatalog(models)
      const selected = form.getFieldsValue().model
      if (selected && !models.includes(selected)) {
        form.setFieldValue('model', undefined)
        invalidateTest()
      }
    })
  }

  function test(values: ModelFields) {
    if (busy.current || !values.model) return
    const testedRevision = revision.current
    setTestToken(null)
    void perform('test', async (signal) => {
      const result = await testModelSettings(
        { ...credentials(values), model: values.model ?? '' },
        signal,
      )
      if (!signal.aborted && testedRevision === revision.current) setTestToken(result.test_token)
    })
  }

  function save() {
    if (busy.current || !testToken) return
    const values = form.getFieldsValue()
    void perform('save', async (signal) => {
      const library = await saveModelProfile(
        { ...credentials(values), model: values.model ?? '', test_token: testToken },
        signal,
        profile?.id,
      )
      if (!signal.aborted) {
        form.setFieldValue('apiKey', '')
        void message.success('模型配置已保存')
        onSaved(library)
      }
    })
  }

  return {
    form,
    model,
    catalog,
    canReuseKey,
    pending,
    error,
    needsReload,
    isTested: testToken !== null,
    changed,
    loadCatalog,
    test,
    save,
  }
}
