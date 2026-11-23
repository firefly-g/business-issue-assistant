/** @description 将契约中可省略的事实字段转换为受控表单，不推断缺失业务事实。 */
import type { DraftFields } from '../../types'
import type { FeedbackDraft } from '../../api/services/feedbackDrafts'

/** 缺失字段保持空白，人工编辑的值不被历史案例自动覆盖。 */
export function editableFields(content: FeedbackDraft['content']): DraftFields {
  return {
    title: content.title,
    symptom: content.symptom,
    conditions: content.conditions ?? '',
    investigation: content.investigation ?? '',
    cause: content.cause ?? '',
    solution: content.solution ?? '',
    verification: content.verification ?? '',
  }
}

/** 草稿状态与正式案例发布状态分别展示。 */
export const feedbackDraftStatus = { draft: '编辑中', pending: '待确认', published: '已发布' }
