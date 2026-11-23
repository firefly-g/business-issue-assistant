/** @description 为审核展示原问题、实际反馈、原始材料与生成及修改记录，模型建议与事实分开。 */
import { Collapse, Tag } from 'antd'
import type { FeedbackDraft } from '../../api/services/feedbackDrafts'
import { draftFields } from '../../components/caseFields'
import { outcomeLabels } from '../../types'
import { SourceEvidence } from '../cases/SourceEvidence'
import { feedbackDraftStatus } from './draftFields'

interface FeedbackDraftEvidenceProps {
  /** 由服务端授权并保存的整理输入及审计快照。 */
  value: FeedbackDraft
}

/** 审核使用整理时的快照，原附件仍通过独立授权接口读取。 */
export function FeedbackDraftEvidence({ value }: FeedbackDraftEvidenceProps) {
  const { question, feedback, run, source } = value.evidence
  return (
    <Collapse
      items={[
        {
          key: 'evidence',
          label: '查看问题与实际处理依据',
          children: (
            <>
              <h3>原问题</h3>
              <p className="whitespace-pre-wrap break-words">{question.text}</p>
              <h3>实际处理反馈</h3>
              <Tag>{outcomeLabels[feedback.outcome]}</Tag>
              <p className="whitespace-pre-wrap break-words">{feedback.note}</p>
              <p className="muted">
                记录于 {new Date(feedback.created_at).toLocaleString('zh-CN')}
              </p>
              {source && <SourceEvidence sourceId={source.id} />}
              <h3>当时的分析建议</h3>
              <p>{run.result.summary}</p>
              <small>分析建议不代表已经执行的操作，案例以实际反馈和人工核对结果为准。</small>
            </>
          ),
        },
        {
          key: 'generation',
          label: '查看最初整理内容与修改记录',
          children: (
            <>
              <p>
                {value.mode === 'model' ? '模型辅助整理' : '本地规则预填'} · {value.model}
              </p>
              <p className="muted">整理规则 {value.rule_version}</p>
              <Collapse
                items={[
                  {
                    key: 'original',
                    label: '最初整理内容',
                    children: draftFields.map(({ name, label }) => (
                      <p key={name}>
                        <strong>{label}：</strong>
                        {value.generated_content[name] || '未填写'}
                      </p>
                    )),
                  },
                  ...value.history.map((entry) => ({
                    key: String(entry.version),
                    label: `v${entry.version} · ${feedbackDraftStatus[entry.status]} · ${new Date(entry.created_at).toLocaleString('zh-CN')}`,
                    children: (
                      <>
                        <p>
                          {entry.kind === 'create'
                            ? '新增案例'
                            : `修订案例，基准 v${entry.target_version}`}
                        </p>
                        {draftFields.map(({ name, label }) => (
                          <p key={name}>
                            <strong>{label}：</strong>
                            {entry.content[name] || '未填写'}
                          </p>
                        ))}
                      </>
                    ),
                  })),
                ]}
              />
            </>
          ),
        },
      ]}
    />
  )
}
