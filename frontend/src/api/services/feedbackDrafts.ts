/** @description 反馈案例草稿的生成、编辑、审核及依据接口，所有响应按 OpenAPI 校验。 */
import type { components } from '../generated'
import { request } from '../client'
import { decode } from '../decoder'
import type { Business } from '../../types'

/** 完整反馈草稿，仅本人及同业务处理角色可读。 */
export type FeedbackDraft = components['schemas']['FeedbackDraftRead']
/** 带预期版本的完整草稿编辑，不直接改写正式案例。 */
export type FeedbackDraftUpdate = components['schemas']['FeedbackDraftUpdate']
/** 维护人显式确认的发布参数，有效性不从反馈自动推断。 */
export type FeedbackDraftPublish = components['schemas']['FeedbackDraftPublish']

/** 主动整理本人反馈，同份反馈重复调用打开已有草稿，失败可使用原键重试。 */
export async function generateFeedbackDraft(
  questionId: string,
  feedbackId: string,
  key: string,
  signal?: AbortSignal,
) {
  return decode(
    'FeedbackDraftRead',
    await request(
      `/questions/${encodeURIComponent(questionId)}/feedback/${encodeURIComponent(feedbackId)}/draft`,
      { method: 'POST', idempotencyKey: key, signal },
    ),
  )
}

/** 按业务读取可见反馈草稿，普通成员的列表限定本人。 */
export async function listFeedbackDrafts(business: Business, signal?: AbortSignal) {
  return decode(
    'FeedbackDraftList',
    await request(`/feedback-drafts?${new URLSearchParams({ business })}`, { signal }),
  )
}

/** 读取最新版本及修改历史，调用方自行保留尚未保存的本地表单。 */
export async function readFeedbackDraft(id: string, signal?: AbortSignal) {
  return decode(
    'FeedbackDraftRead',
    await request(`/feedback-drafts/${encodeURIComponent(id)}`, { signal }),
  )
}

/** 保存编辑或提交审核，版本冲突由页面展示并人工核对。 */
export async function updateFeedbackDraft(
  id: string,
  data: FeedbackDraftUpdate,
  signal?: AbortSignal,
) {
  return decode(
    'FeedbackDraftRead',
    await request(`/feedback-drafts/${encodeURIComponent(id)}`, {
      method: 'PUT',
      data,
      signal,
    }),
  )
}

/** 发布新增或修订，同一发布请求重试复用原键，后端原子校验两种资源版本。 */
export async function publishFeedbackDraft(
  id: string,
  data: FeedbackDraftPublish,
  key: string,
  signal?: AbortSignal,
) {
  return decode(
    'FeedbackDraftRead',
    await request(`/feedback-drafts/${encodeURIComponent(id)}/publish`, {
      method: 'POST',
      data,
      idempotencyKey: key,
      signal,
    }),
  )
}

/** 正式案例仅公开已采用反馈的有限依据，不返回私人运行和草稿历史。 */
export async function listFeedbackEvidence(caseId: string, signal?: AbortSignal) {
  return decode(
    'PublishedFeedbackList',
    await request(`/cases/${encodeURIComponent(caseId)}/feedback-evidence`, { signal }),
  )
}
