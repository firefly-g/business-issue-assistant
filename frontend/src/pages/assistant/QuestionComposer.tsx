/** @description 渲染问题输入及截图选择，分析状态与写入流程由所属业务 Hook 维护。 */
import { useId, useRef } from 'react'
import type { ComponentRef } from 'react'
import { Button, Input, Tooltip } from 'antd'
import { CopyOutlined, PaperClipOutlined, SendOutlined } from '@ant-design/icons'
import type { AssistantController } from './useAssistant'

interface QuestionComposerProps {
  /** 当前页面独占的表单与分析状态。 */
  controller: AssistantController
}

const exampleQuestions = [
  '客户已扣款，订单仍显示待支付',
  '优惠券满足门槛，但结算时无法使用',
  '后台登录后提示没有操作权限',
]

/** 示例填入文本后聚焦输入框供继续编辑，分析由用户主动发起。 */
export function QuestionComposer({ controller }: QuestionComposerProps) {
  const fileInput = useRef<HTMLInputElement>(null)
  const questionInput = useRef<ComponentRef<typeof Input.TextArea>>(null)
  const screenshotHintId = useId()
  const { text, file, isBusy, updateText, updateFile, submit } = controller
  return (
    <>
      <section className="question-box">
        <Input.TextArea
          ref={questionInput}
          aria-label="问题描述"
          aria-describedby={file ? screenshotHintId : undefined}
          variant="borderless"
          value={text}
          onChange={(event) => updateText(event.target.value)}
          disabled={isBusy}
          maxLength={10000}
          autoSize={{ minRows: 5, maxRows: 12 }}
          onPaste={(event) => {
            const image = Array.from(event.clipboardData.files).find((item) =>
              item.type.startsWith('image/'),
            )
            if (image) {
              event.preventDefault()
              updateFile(image)
            }
          }}
          placeholder="描述问题现象、报错和已尝试的操作，或直接粘贴处理记录。"
        />
        {file && (
          <div className="composer-attachment">
            <div className="attached-file">
              <PaperClipOutlined aria-hidden />
              <span>{file.name}</span>
              <Button disabled={isBusy} type="text" size="small" onClick={() => updateFile(null)}>
                移除
              </Button>
            </div>
            <p id={screenshotHintId} className="muted">
              请在描述中补充截图里的关键文字。
            </p>
          </div>
        )}
        <div className="composer-bottom">
          <div>
            <input
              ref={fileInput}
              type="file"
              accept="image/png,image/jpeg,image/webp"
              hidden
              onChange={(event) => {
                updateFile(event.target.files?.[0] ?? null)
                // 清空原生选择值，移除后重选同一张图也会触发 change。
                event.target.value = ''
              }}
            />
            <Tooltip title="也可直接粘贴图片">
              <Button
                type="text"
                disabled={isBusy}
                icon={<PaperClipOutlined />}
                onClick={() => fileInput.current?.click()}
              >
                添加截图
              </Button>
            </Tooltip>
          </div>
          <Button
            type="primary"
            icon={<SendOutlined />}
            loading={isBusy}
            onClick={() => void submit()}
          >
            开始分析
          </Button>
        </div>
      </section>
      {!controller.result && (
        <section className="prompt-examples" aria-labelledby="example-questions-title">
          <h2 id="example-questions-title">示例问题</h2>
          <div>
            {exampleQuestions.map((item) => (
              <button
                type="button"
                key={item}
                onClick={() => {
                  updateText(item)
                  questionInput.current?.focus({ cursor: 'end' })
                }}
                disabled={isBusy}
              >
                <CopyOutlined aria-hidden /> {item}
              </button>
            ))}
          </div>
        </section>
      )}
    </>
  )
}
