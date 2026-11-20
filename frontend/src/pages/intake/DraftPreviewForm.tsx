/** @description 校正结构化预览后提交草稿，缺失字段保留空白，不将预览作为验证结论。 */
import { useEffect, useRef } from 'react'
import { Alert, Button, Form } from 'antd'
import { CaseFieldsForm } from '../../components/CaseFieldsForm'
import type { DraftFields, DraftPreview } from '../../types'
import type { IntakeController } from './useIntake'

interface DraftPreviewFormProps {
  /** 收录控制器，保存失败时保持当前表单。 */
  controller: IntakeController
  /** 材料保存后返回的可校正预览，缺失的业务字段仍由人工填写。 */
  preview: DraftPreview
}

/** 预览就绪后才挂载表单，避免使用未连接的 Form 实例回填。 */
export function DraftPreviewForm({ controller, preview: value }: DraftPreviewFormProps) {
  const heading = useRef<HTMLHeadingElement>(null)
  useEffect(() => {
    // 草稿异步展开后把焦点交给新面板，窄屏和键盘用户可直接进入下一步。
    heading.current?.focus()
  }, [])
  const initial: DraftFields = {
    title: value.title,
    symptom: value.symptom,
    conditions: value.conditions ?? '',
    investigation: value.investigation ?? '',
    cause: value.cause ?? '',
    solution: value.solution ?? '',
    verification: value.verification ?? '',
  }
  return (
    <section className="panel draft-panel">
      <div className="section-heading">
        <h2 ref={heading} tabIndex={-1}>
          经验草稿
        </h2>
      </div>
      <Alert
        type="info"
        title={
          value.mode === 'local_rules'
            ? '本地规则已提取标题和原文，请补充其余字段。'
            : '请对照原文核对模型生成的内容。'
        }
        showIcon
      />
      {!!value.similar.length && (
        <div className="similar-notice">
          <strong>发现 {value.similar.length} 条相似经验</strong>
          {value.similar.map((item) => (
            <p key={item.id}>{item.title}</p>
          ))}
          <small>请核对是否已有同一条经验。</small>
        </div>
      )}
      <Form<DraftFields>
        initialValues={initial}
        layout="vertical"
        onFinish={(values) => void controller.save(values)}
        requiredMark={false}
        disabled={controller.isBusy}
        onValuesChange={controller.changed}
      >
        <CaseFieldsForm />
        {controller.error && (
          <Alert className="mb-4" type="error" title={controller.error} showIcon />
        )}
        <Button type="primary" htmlType="submit" loading={controller.isBusy}>
          提交人工确认
        </Button>
      </Form>
    </section>
  )
}
