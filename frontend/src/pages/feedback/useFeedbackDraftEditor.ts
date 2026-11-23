/** @description 编排反馈草稿保存、目标核对和发布；失败保留表单，晚到响应随页面卸载隔离。 */
import { useRef, useState } from 'react'
import { App, Form } from 'antd'
import type { FormInstance } from 'antd'
import { ApiError, errorMessage, isCancelled } from '../../api/client'
import { readCase } from '../../api/services/cases'
import * as drafts from '../../api/services/feedbackDrafts'
import type { FeedbackDraft } from '../../api/services/feedbackDrafts'
import { useRequestScope } from '../../hooks/useRequestScope'
import { useWorkspaceStore } from '../../store/workspace'
import type { Case, DraftFields } from '../../types'

/** 草稿编辑的状态所有权，修改基准版本必须由用户明确触发。 */
export interface FeedbackDraftEditor {
  /** 服务端最后确认保存的草稿及版本。 */
  saved: FeedbackDraft
  /** 页面独占的表单，失败和冲突时不清空。 */
  form: FormInstance<DraftFields>
  /** 当前人工选择的新增或修订用途。 */
  kind: FeedbackDraft['kind']
  /** 当前核对的目标快照，不因后台更新自动切换。 */
  target: Case | null
  /** 选择新用途时保留输入，新增会清除目标。 */
  changeKind: (kind: FeedbackDraft['kind']) => void
  /** 读取指定目标当前版本，未保存正文保持原样。 */
  selectTarget: (id: string) => Promise<void>
  /** 页面写入或目标读取期间禁止重复操作。 */
  isBusy: boolean
  /** 表单或用途是否存在未保存改动，发布前必须先保存。 */
  isDirty: boolean
  /** 标记用户修改，不触发后台写入。 */
  changed: () => void
  /** 最近一次可恢复的错误。 */
  error: string
  /** 版本冲突后读取的目标，采用前不改变原基准。 */
  latestTarget: Case | null
  /** 草稿冲突后供人工对照的服务端内容。 */
  latestDraft: FeedbackDraft | null
  /** 核对后采用新目标版本，保留本地正文。 */
  adoptTarget: () => void
  /** 核对后采用最新草稿版本，保留本地正文及目标选择。 */
  adoptDraft: () => void
  /** 保存编辑或提交审核，成功后通知工作台刷新。 */
  save: (status: 'draft' | 'pending') => Promise<void>
  /** 显式选择的最终有效性，不从已解决反馈推断。 */
  validity: Case['validity']
  /** 修改发布选择时重新生成请求键。 */
  setValidity: (value: Case['validity']) => void
  /** 发布最近保存的待确认版本。 */
  publish: () => Promise<void>
}

/** 成功保存前表单是唯一正文来源，冲突恢复只更新版本，不覆盖用户输入。 */
export function useFeedbackDraftEditor(
  initial: FeedbackDraft,
  onDirtyChange?: (value: boolean) => void,
): FeedbackDraftEditor {
  // 长函数保留原因：此 Hook 独占同一编辑会话的表单、版本及冲突恢复，闭包动作共享生命周期。
  const { message } = App.useApp()
  const [form] = Form.useForm<DraftFields>()
  const [saved, setSaved] = useState(initial)
  const [kind, setKind] = useState(initial.kind)
  const [target, setTarget] = useState<Case | null>(initial.base_snapshot)
  const [latestTarget, setLatestTarget] = useState<Case | null>(null)
  const [latestDraft, setLatestDraft] = useState<FeedbackDraft | null>(null)
  const [isBusy, setIsBusy] = useState(false)
  const [isDirty, setIsDirty] = useState(false)
  const [error, setError] = useState('')
  const [validity, updateValidity] = useState<Case['validity']>('unverified')
  const publishKey = useRef(crypto.randomUUID())
  const inFlight = useRef(false)
  const begin = useRequestScope()
  const refresh = useWorkspaceStore((state) => state.refresh)

  async function execute(action: (signal: AbortSignal) => Promise<void>) {
    if (inFlight.current) return
    const scope = begin()
    inFlight.current = true
    setIsBusy(true)
    setError('')
    try {
      await action(scope.signal)
    } catch (reason: unknown) {
      if (scope.signal.aborted || isCancelled(reason)) return
      if (typeof reason === 'object' && reason !== null && 'errorFields' in reason) return
      setError(errorMessage(reason))
      // 冲突读取仅提供对照数据，不把新版本静默写入表单或目标基准。
      try {
        if (
          reason instanceof ApiError &&
          ['TARGET_VERSION_CONFLICT', 'INVALID_TARGET'].includes(reason.code) &&
          target
        ) {
          const latest = await readCase(target.id, scope.signal)
          if (!scope.signal.aborted) setLatestTarget(latest)
        } else if (reason instanceof ApiError && reason.code === 'VERSION_CONFLICT') {
          const latest = await drafts.readFeedbackDraft(saved.id, scope.signal)
          if (!scope.signal.aborted) setLatestDraft(latest)
        }
      } catch (readError: unknown) {
        if (!scope.signal.aborted && !isCancelled(readError))
          setError(`${errorMessage(reason)}；${errorMessage(readError)}`)
      }
    } finally {
      scope.complete()
      inFlight.current = false
      if (!scope.signal.aborted) setIsBusy(false)
    }
  }
  function changed() {
    setIsDirty(true)
    onDirtyChange?.(true)
  }
  function changeKind(value: FeedbackDraft['kind']) {
    setKind(value)
    if (value === 'create') setTarget(null)
    setLatestTarget(null)
    changed()
  }
  async function selectTarget(id: string) {
    await execute(async (signal) => {
      const value = await readCase(id, signal)
      if (!signal.aborted) {
        setTarget(value)
        setLatestTarget(null)
        changed()
      }
    })
  }
  async function save(status: 'draft' | 'pending') {
    await execute(async (signal) => {
      // 1. 校验本地正文与目标选择，再以最后确认的草稿和案例版本保存。
      const content = await form.validateFields()
      if (kind === 'revise' && !target) {
        setError('请选择需要修订的已发布案例')
        return
      }
      const value = await drafts.updateFeedbackDraft(
        saved.id,
        {
          version: saved.version,
          content,
          kind,
          status,
          target_case_id: kind === 'revise' ? target?.id : null,
          target_version: kind === 'revise' ? target?.version : null,
        },
        signal,
      )
      // 2. 只有服务端成功保存才清理脏标记和刷新工作台，失败保留全部输入。
      if (signal.aborted) return
      setSaved(value)
      setIsDirty(false)
      onDirtyChange?.(false)
      setLatestDraft(null)
      setLatestTarget(null)
      publishKey.current = crypto.randomUUID()
      refresh()
      void message.success(status === 'pending' ? '已提交人工确认' : '草稿已保存')
    })
  }
  async function publish() {
    if (isDirty) {
      setError('请先保存并提交当前修改，再审核发布')
      return
    }
    await execute(async (signal) => {
      const value = await drafts.publishFeedbackDraft(
        saved.id,
        { version: saved.version, validity },
        publishKey.current,
        signal,
      )
      if (!signal.aborted) {
        setSaved(value)
        refresh()
        void message.success('案例已发布')
      }
    })
  }
  return {
    saved,
    form,
    kind,
    target,
    isBusy,
    isDirty,
    changed,
    error,
    latestTarget,
    latestDraft,
    changeKind,
    selectTarget,
    save,
    publish,
    validity,
    setValidity: (value) => {
      updateValidity(value)
      publishKey.current = crypto.randomUUID()
    },
    adoptTarget: () => {
      if (latestTarget) {
        setTarget(latestTarget)
        setLatestTarget(null)
        setError('')
        changed()
      }
    },
    adoptDraft: () => {
      if (latestDraft && latestDraft.status !== 'published') {
        setSaved(latestDraft)
        setLatestDraft(null)
        setError('')
        changed()
      }
    },
  }
}
