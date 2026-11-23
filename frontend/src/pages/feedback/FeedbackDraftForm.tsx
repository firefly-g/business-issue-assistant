/** @description 反馈草稿的人工校正、修订对照与审核表单，发布权限由服务端再次检查。 */
import { Alert, Button, Form, Select, Space, Tag } from 'antd'
import type { FeedbackDraft } from '../../api/services/feedbackDrafts'
import { CaseFieldsForm } from '../../components/CaseFieldsForm'
import { useSessionStore } from '../../store/session'
import { validityLabels } from '../../types'
import type { DraftFields } from '../../types'
import { DraftComparison } from './DraftComparison'
import { FeedbackDraftEvidence } from './FeedbackDraftEvidence'
import { FeedbackDraftTarget } from './FeedbackDraftTarget'
import type { FeedbackDraftEditor } from './useFeedbackDraftEditor'
import { editableFields, feedbackDraftStatus } from './draftFields'
import { useFeedbackDraftEditor } from './useFeedbackDraftEditor'

interface FeedbackDraftFormProps {
  /** 打开时已读取的服务端草稿，冲突恢复由编辑控制器保留本地输入。 */
  initial: FeedbackDraft
  /** 发布后在工作台查看正式案例，同时关闭当前草稿。 */
  openCase: (id: string) => void
  /** 编辑与成功保存时通知对话框是否需要关闭确认，不包含表单正文。 */
  onDirtyChange?: (value: boolean) => void
}

/** 新增与修订共享事实字段；只有保存提交的版本可审核，未保存改动阻止发布。 */
export function FeedbackDraftForm({ initial, openCase, onDirtyChange }: FeedbackDraftFormProps) {
  const editor = useFeedbackDraftEditor(initial, onDirtyChange)
  const role = useSessionStore((state) => state.user?.role)
  const watched = Form.useWatch<DraftFields>([], editor.form)
  const proposed = watched ?? editableFields(initial.content)
  const published = editor.saved.status === 'published'
  return (
    <div className="grid gap-4">
      <Space wrap>
        <Tag>{feedbackDraftStatus[editor.saved.status]}</Tag>
        <span>草稿 v{editor.saved.version}</span>
      </Space>
      <Alert
        type="info"
        showIcon
        title="问题已解决不代表方案已验证。请核对实际操作、适用条件和验证结果后再提交。"
      />
      <FeedbackDraftEvidence value={editor.saved} />
      {editor.error && <Alert type="error" showIcon title={editor.error} />}
      {editor.latestDraft && (
        <>
          <DraftComparison
            title={`核对最新草稿 v${editor.latestDraft.version}`}
            original={editableFields(editor.latestDraft.content)}
            proposed={proposed}
          />
          {editor.latestDraft.status === 'published' ? (
            <Alert type="warning" title="此草稿已被发布，请关闭后重新打开查看发布结果。" />
          ) : (
            <Button onClick={editor.adoptDraft}>
              已核对，采用草稿版本 v{editor.latestDraft.version} 并保留本地内容
            </Button>
          )}
        </>
      )}
      {editor.latestTarget && (
        <>
          <DraftComparison
            title={`核对目标案例最新版本 v${editor.latestTarget.version}`}
            original={editableFields(editor.latestTarget)}
            proposed={proposed}
          />
          {editor.latestTarget.publication === 'published' ? (
            <Button onClick={editor.adoptTarget}>
              已核对，采用目标版本 v{editor.latestTarget.version} 并保留本地内容
            </Button>
          ) : (
            <Alert type="warning" title="目标案例已撤回，请选择其他案例或改为新增。" />
          )}
        </>
      )}
      <Form
        form={editor.form}
        initialValues={editableFields(initial.content)}
        layout="vertical"
        disabled={published || editor.isBusy}
        onValuesChange={editor.changed}
      >
        <Form.Item label="整理用途">
          <Select
            aria-label="整理用途"
            value={editor.kind}
            onChange={editor.changeKind}
            options={[
              { value: 'create', label: '新增案例' },
              { value: 'revise', label: '修订已有案例' },
            ]}
          />
        </Form.Item>
        {editor.kind === 'revise' && <FeedbackDraftTarget editor={editor} proposed={proposed} />}
        <CaseFieldsForm />
        {!published && (
          <Space wrap>
            <Button loading={editor.isBusy} onClick={() => void editor.save('draft')}>
              保存草稿
            </Button>
            <Button
              type="primary"
              loading={editor.isBusy}
              onClick={() => void editor.save('pending')}
            >
              保存并提交人工确认
            </Button>
          </Space>
        )}
      </Form>
      {!published && role === 'maintainer' && <PublicationPanel editor={editor} />}
      {published && editor.saved.published_case_id && (
        <Alert
          type="success"
          title={`已发布到案例 v${editor.saved.published_case_version}`}
          action={
            <Button
              onClick={() => {
                if (editor.saved.published_case_id) openCase(editor.saved.published_case_id)
              }}
            >
              查看正式案例
            </Button>
          }
        />
      )}
    </div>
  )
}

function PublicationPanel({ editor }: { editor: FeedbackDraftEditor }) {
  return (
    <section className="grid gap-3">
      <h3>审核发布</h3>
      <label>
        方案有效性
        <Select
          className="w-full"
          aria-label="发布时的方案有效性"
          value={editor.validity}
          disabled={editor.isBusy}
          onChange={editor.setValidity}
          options={Object.entries(validityLabels).map(([value, label]) => ({ value, label }))}
        />
      </label>
      <p className="muted">选择“已验证”时，必须填写适用条件、处理步骤和实际验证结果。</p>
      <Button
        type="primary"
        disabled={editor.saved.status !== 'pending' || editor.isDirty || editor.isBusy}
        onClick={() => void editor.publish()}
      >
        确认并发布{editor.kind === 'revise' ? '修订' : '新案例'}
      </Button>
    </section>
  )
}
