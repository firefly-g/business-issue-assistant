/** @description 选择同业务已发布案例并逐字段对照，切换目标不会自动覆盖人工草稿。 */
import { useCallback } from 'react'
import { Alert, Button, Form, Select } from 'antd'
import { listCases } from '../../api/services/cases'
import { useQuery } from '../../hooks/useQuery'
import type { DraftFields } from '../../types'
import { DraftComparison } from './DraftComparison'
import { editableFields } from './draftFields'
import type { FeedbackDraftEditor } from './useFeedbackDraftEditor'

interface FeedbackDraftTargetProps {
  /** 当前表单及用途，公开编辑动作仍由控制器统一管理。 */
  editor: FeedbackDraftEditor
  /** 当前本地表单内容，仅用于对照。 */
  proposed: DraftFields
}

/** 同时展示关键词相似案例和其他可选案例，不自动选择或合并相似项。 */
export function FeedbackDraftTarget({ editor, proposed }: FeedbackDraftTargetProps) {
  const { business, evidence } = editor.saved
  const load = useCallback(
    async (signal: AbortSignal) => {
      const [all, similar] = await Promise.all([
        listCases(business, '', signal),
        listCases(business, evidence.question.text, signal),
      ])
      return { all: all.filter((item) => item.publication === 'published'), similar }
    },
    [business, evidence.question.text],
  )
  const cases = useQuery({ key: `feedback-targets:${business}`, load })
  const similarIds = new Set(cases.data?.similar.map((item) => item.id))
  const options = [true, false].map((similar) => ({
    label: similar ? '相似的已发布案例' : '其他已发布案例',
    options:
      cases.data?.all
        .filter((item) => similarIds.has(item.id) === similar)
        .map((item) => ({ value: item.id, label: item.title })) ?? [],
  }))
  return (
    <>
      <Form.Item label="需要修订的案例">
        <Select
          aria-label="需要修订的案例"
          showSearch
          optionFilterProp="label"
          placeholder="选择同一业务内已发布的案例"
          loading={cases.isLoading}
          value={editor.target?.id}
          options={options}
          onChange={(id: string) => void editor.selectTarget(id)}
        />
      </Form.Item>
      {cases.error && (
        <Alert
          type="error"
          title={cases.error}
          action={<Button onClick={cases.reload}>重试加载案例</Button>}
        />
      )}
      {editor.target && (
        <DraftComparison
          title={`对照目标案例：${editor.target.title}（v${editor.target.version}）`}
          original={editableFields(editor.target)}
          proposed={proposed}
          onUseOriginal={
            editor.saved.status === 'published'
              ? undefined
              : (name, value) => {
                  editor.form.setFieldValue(name, value)
                  editor.changed()
                }
          }
        />
      )}
    </>
  )
}
