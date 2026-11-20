/** @description 维护原始材料输入界面，材料保存后保持只读，上传校验以后台为最终依据。 */
import { Alert, App, Button, Input, Upload } from 'antd'
import { ArrowRightOutlined, PaperClipOutlined } from '@ant-design/icons'
import type { IntakeController } from './useIntake'

interface MaterialFormProps {
  /** 收录页面独占的状态和动作。 */
  controller: IntakeController
}

/** 在上传前提示大小与格式错误，不将客户端校验当作实际文件安全检查。 */
export function MaterialForm({ controller }: MaterialFormProps) {
  const { message } = App.useApp()
  const { text, file, source, isBusy, updateText, updateFile, prepare } = controller
  return (
    <section className="panel source-panel">
      <div className="section-heading">
        <h2>原始材料</h2>
      </div>
      {!source && controller.error && (
        <Alert className="mb-4" type="error" title={controller.error} showIcon />
      )}
      <Input.TextArea
        aria-label="原始聊天材料"
        value={text}
        readOnly={source !== null}
        disabled={isBusy && !source}
        onChange={(event) => updateText(event.target.value)}
        rows={14}
        maxLength={20000}
        placeholder="粘贴群聊或处理记录，包含问题现象、排查过程和处理结果。"
      />
      {!source && (
        <div className="source-actions">
          <Upload
            accept="image/png,image/jpeg,image/webp"
            maxCount={1}
            fileList={file ? [{ uid: 'attachment', name: file.name, status: 'done' }] : []}
            beforeUpload={(value) => {
              if (
                !['image/png', 'image/jpeg', 'image/webp'].includes(value.type) ||
                value.size > 5 * 1024 * 1024
              ) {
                void message.warning('请选择 5 MB 以内的 PNG、JPEG 或 WebP 图片')
                return Upload.LIST_IGNORE
              }
              updateFile(value)
              return false
            }}
            onRemove={() => updateFile(null)}
          >
            <Button disabled={isBusy} icon={<PaperClipOutlined />}>
              添加截图
            </Button>
          </Upload>
          <Button type="primary" onClick={() => void prepare()} loading={isBusy}>
            整理草稿 <ArrowRightOutlined aria-hidden />
          </Button>
        </div>
      )}
      {source?.attachment_name && (
        <div className="attached-file mt-4">
          <PaperClipOutlined aria-hidden />
          <span>{source.attachment_name}</span>
        </div>
      )}
    </section>
  )
}
