/** @description 展示经后台复核的分析与引用，反馈交给独立交互维护，模型内容按纯文本渲染。 */
import { useState } from 'react'
import { Alert, App, Button, Tag } from 'antd'
import { CopyOutlined } from '@ant-design/icons'
import { CaseRow } from '../../components/CaseRow'
import type { Analysis } from '../../types'
import { progressLabels } from '../../types'
import { FeedbackDialog } from './FeedbackDialog'

interface AnalysisResultProps {
  /** 通过领域 Service 校验的提问与分析。 */
  value: Analysis
  /** 使用 URL 打开引用案例。 */
  openCase: (id: string) => void
  /** 实际反馈保存后刷新当前提问，失败时可继续重试读取。 */
  onFeedback?: () => void | Promise<void>
}

/** 原始模型文字保持纯文本，版本变化警告与当前服务端投影同步展示。 */
export function AnalysisResult({ value, openCase, onFeedback }: AnalysisResultProps) {
  const { message } = App.useApp()
  const [isFeedbackOpen, setIsFeedbackOpen] = useState(false)
  const result = value.run.result
  return (
    <section className="analysis-result panel" aria-live="polite">
      <div className="section-heading">
        <h2>排查参考</h2>
        <Tag>{progressLabels[value.question.progress]}</Tag>
      </div>
      <Alert type="info" title={result.notice} showIcon />
      <p className="analysis-summary">{result.summary}</p>
      <h3>建议排查顺序</h3>
      <ol className="step-list">
        {result.steps.map((step, index) => (
          <li key={`${index}-${step}`}>{step}</li>
        ))}
      </ol>
      {result.missing.length > 0 && (
        <>
          <h3>需要补充的信息</h3>
          <div className="missing-tags">
            {result.missing.map((item, index) => (
              <Tag key={`${index}-${item}`}>{item}</Tag>
            ))}
          </div>
        </>
      )}
      <h3>相关历史案例</h3>
      {result.citations.length ? (
        result.citations.map((item) => (
          <div key={item.id}>
            {item.currently_available === false && (
              <Alert type="warning" title="此引用已更新、归档或失效，请重新分析后选用当前方案。" />
            )}
            <CaseRow item={item} onClick={() => openCase(item.id)} />
          </div>
        ))
      ) : (
        <p className="muted">未找到相关案例，可补充背景后重新分析。</p>
      )}
      <div className="result-actions">
        <Button
          icon={<CopyOutlined />}
          onClick={() => {
            void navigator.clipboard
              .writeText(result.reply)
              .then(() => message.success('回复草稿已复制'))
              .catch(() => message.error('复制失败，请手动复制'))
          }}
        >
          复制回复
        </Button>
        <Button type="primary" onClick={() => setIsFeedbackOpen(true)}>
          记录处理结果
        </Button>
      </div>
      <details className="trace">
        <summary>查看分析记录</summary>
        <p>运行编号 {value.run.id}</p>
        <p>
          规则版本 {value.run.rule_version} · {value.run.model}
        </p>
      </details>
      <FeedbackDialog
        key={value.question.id}
        questionId={value.question.id}
        open={isFeedbackOpen}
        onClose={() => setIsFeedbackOpen(false)}
        onSaved={onFeedback}
      />
    </section>
  )
}
