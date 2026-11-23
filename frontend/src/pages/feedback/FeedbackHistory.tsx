/** @description 展示本人实际反馈并主动整理或打开案例草稿，生成失败保留反馈供重试。 */
import { useRef, useState } from 'react'
import { Alert, Button, Tag } from 'antd'
import { errorMessage, isCancelled } from '../../api/client'
import { generateFeedbackDraft } from '../../api/services/feedbackDrafts'
import { useRequestScope } from '../../hooks/useRequestScope'
import { useWorkspaceStore } from '../../store/workspace'
import type { Analysis } from '../../types'
import { outcomeLabels } from '../../types'
import { FeedbackDraftDialog } from './FeedbackDraftDialog'

interface FeedbackHistoryProps {
  /** 同一问题的服务端反馈记录，新增反馈后由调用方重新读取。 */
  value: Analysis
  /** 查看发布后的正式案例。 */
  openCase: (id: string) => void
}

/** 反馈整理由用户主动触发，保存反馈本身不调用模型或发布知识。 */
export function FeedbackHistory({ value, openCase }: FeedbackHistoryProps) {
  return (
    <section className="grid gap-3" aria-label="实际处理反馈">
      {value.feedback?.map((feedback) => (
        <FeedbackEntry
          key={feedback.id}
          questionId={value.question.id}
          feedback={feedback}
          openCase={openCase}
        />
      ))}
    </section>
  )
}

function FeedbackEntry({
  questionId,
  feedback,
  openCase,
}: {
  questionId: string
  feedback: NonNullable<Analysis['feedback']>[number]
  openCase: (id: string) => void
}) {
  const [draftId, setDraftId] = useState<string | null>(null)
  const [isOpen, setIsOpen] = useState(false)
  const [isBusy, setIsBusy] = useState(false)
  const [error, setError] = useState('')
  const key = useRef(crypto.randomUUID())
  const inFlight = useRef(false)
  const begin = useRequestScope()
  const refresh = useWorkspaceStore((state) => state.refresh)
  async function generate() {
    if (draftId) {
      setIsOpen(true)
      return
    }
    if (inFlight.current) return
    const scope = begin()
    inFlight.current = true
    setIsBusy(true)
    setError('')
    try {
      const value = await generateFeedbackDraft(questionId, feedback.id, key.current, scope.signal)
      if (!scope.signal.aborted) {
        setDraftId(value.id)
        setIsOpen(true)
        refresh()
      }
    } catch (reason: unknown) {
      if (!scope.signal.aborted && !isCancelled(reason)) setError(errorMessage(reason))
    } finally {
      scope.complete()
      inFlight.current = false
      if (!scope.signal.aborted) setIsBusy(false)
    }
  }
  return (
    <div className="feedback-note grid gap-3">
      <div>
        <Tag>{outcomeLabels[feedback.outcome]}</Tag>
        {new Date(feedback.created_at).toLocaleString('zh-CN')}
      </div>
      <p className="whitespace-pre-wrap break-words">{feedback.note}</p>
      <Button loading={isBusy} onClick={() => void generate()}>
        {draftId ? '打开案例草稿' : '整理为案例草稿'}
      </Button>
      {error && <Alert type="error" title={error} />}
      {isOpen && draftId && (
        <FeedbackDraftDialog
          key={draftId}
          id={draftId}
          onClose={() => setIsOpen(false)}
          openCase={openCase}
        />
      )}
    </div>
  )
}
