/** @description 读取案例已采用的反馈依据，公开视图不包含私人提问运行和草稿编辑历史。 */
import { useCallback } from 'react'
import { Alert, Button, Collapse, Skeleton, Tag } from 'antd'
import { listFeedbackEvidence } from '../../api/services/feedbackDrafts'
import { useQuery } from '../../hooks/useQuery'
import { outcomeLabels } from '../../types'
import { SourceEvidence } from './SourceEvidence'

interface FeedbackEvidenceProps {
  /** 当前已授权案例的稳定编号。 */
  caseId: string
  /** 案例更新后重新读取发布依据。 */
  version: number
}

/** 反馈与问题截图分别呈现，附件仍经过服务端当前案例状态和业务权限检查。 */
export function FeedbackEvidence({ caseId, version }: FeedbackEvidenceProps) {
  const load = useCallback((signal: AbortSignal) => listFeedbackEvidence(caseId, signal), [caseId])
  const query = useQuery({ key: `feedback-evidence:${caseId}:${version}`, load })
  if (query.isLoading) return <Skeleton active />
  if (query.error)
    return (
      <Alert
        type="error"
        title={query.error}
        action={<Button onClick={query.reload}>重试</Button>}
      />
    )
  if (!query.data?.length) return null
  return (
    <section className="mt-4">
      <h3>发布时采用的处理反馈</h3>
      <Collapse
        items={query.data.map((item) => ({
          key: item.draft_id,
          label: `案例 v${item.case_version} 的处理反馈`,
          children: (
            <>
              <h4>当时的问题</h4>
              <p className="whitespace-pre-wrap break-words">{item.question_text}</p>
              <Tag>{outcomeLabels[item.outcome]}</Tag>
              <p className="whitespace-pre-wrap break-words">{item.note}</p>
              {item.question_source_id && <SourceEvidence sourceId={item.question_source_id} />}
            </>
          ),
        }))}
      />
    </section>
  )
}
