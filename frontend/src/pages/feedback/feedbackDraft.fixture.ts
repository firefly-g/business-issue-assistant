/** @description 反馈草稿交互测试的合成契约数据，不代表真实业务案例。 */
import type { FeedbackDraft } from '../../api/services/feedbackDrafts'
import type { Case } from '../../types'

const content = {
  title: '合成反馈草稿',
  symptom: '合成问题现象',
  conditions: '渠道甲',
  investigation: '已核对流水',
  cause: '',
  solution: '按流程恢复',
  verification: '处理人已确认恢复',
}

/** 供版本冲突对照使用的已发布合成案例。 */
export const targetFixture: Case = {
  ...content,
  id: 'target',
  business: '订单售后',
  publication: 'published',
  validity: 'verified',
  verified_by: 'maintainer',
  source_id: 'source',
  owner_id: 'member',
  version: 2,
  created_at: '2026-11-23T00:00:00Z',
  updated_at: '2026-11-23T00:00:00Z',
  rule_version: 'manual-v1',
  is_demo: false,
}

/** 只使用合成问题、反馈及本地分析，不需要模型或数据库连接。 */
export function draftFixture(kind: FeedbackDraft['kind'] = 'create'): FeedbackDraft {
  return {
    id: 'draft',
    question_id: 'question',
    feedback_id: 'feedback',
    run_id: 'run',
    business: '订单售后',
    owner_id: 'member',
    kind,
    status: 'pending',
    version: 2,
    target_case_id: kind === 'revise' ? targetFixture.id : null,
    target_version: kind === 'revise' ? targetFixture.version : null,
    base_snapshot: kind === 'revise' ? targetFixture : null,
    content,
    generated_content: content,
    evidence: {
      question: {
        id: 'question',
        text: '合成问题现象',
        business: '订单售后',
        source_id: null,
        owner_id: 'member',
        progress: 'resolved',
        created_at: '2026-11-23T00:00:00Z',
      },
      feedback: {
        id: 'feedback',
        question_id: 'question',
        author_id: 'member',
        outcome: 'resolved',
        note: '按流程处理后恢复',
        created_at: '2026-11-23T00:00:00Z',
      },
      run: {
        id: 'run',
        question_id: 'question',
        rule_version: 'analysis-v1',
        model: 'local-rules-v1',
        duration_ms: 1,
        created_at: '2026-11-23T00:00:00Z',
        result: {
          summary: '合成建议',
          steps: ['核对条件'],
          missing: [],
          citations: [],
          reply: '合成回复',
          mode: 'local_rules',
          notice: '合成测试',
        },
      },
      source: null,
    },
    history: [],
    rule_version: 'feedback-v1',
    model: 'local-rules-v1',
    mode: 'local_rules',
    duration_ms: 1,
    published_case_id: null,
    published_case_version: null,
    published_by: null,
    created_at: '2026-11-23T00:00:00Z',
    updated_at: '2026-11-23T00:00:00Z',
  }
}
