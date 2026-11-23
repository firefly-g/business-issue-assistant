/** @description 读取反馈草稿并挂载独立编辑表单，读取失败提供重试，不覆盖未保存编辑。 */
import { useCallback, useRef } from 'react'
import { Alert, App, Button, Modal, Skeleton } from 'antd'
import { readFeedbackDraft } from '../../api/services/feedbackDrafts'
import { useQuery } from '../../hooks/useQuery'
import { FeedbackDraftForm } from './FeedbackDraftForm'

interface FeedbackDraftDialogProps {
  /** 当前草稿编号，变更时由调用方重新挂载。 */
  id: string
  /** 关闭草稿，页面卸载会取消本地请求等待。 */
  onClose: () => void
  /** 查看发布结果时由工作台打开案例。 */
  openCase: (id: string) => void
}

/** 对话框关闭前提醒保存，用户明确关闭仍可稍后从待确认页面继续读取已保存内容。 */
export function FeedbackDraftDialog({ id, onClose, openCase }: FeedbackDraftDialogProps) {
  const { modal } = App.useApp()
  const dirty = useRef(false)
  const changed = useCallback((value: boolean) => {
    dirty.current = value
  }, [])
  const load = useCallback((signal: AbortSignal) => readFeedbackDraft(id, signal), [id])
  const query = useQuery({ key: `feedback-draft:${id}`, load })
  return (
    <Modal
      open
      title="处理反馈案例草稿"
      width={900}
      footer={null}
      onCancel={() => {
        if (!dirty.current) {
          onClose()
          return
        }
        modal.confirm({
          title: '关闭案例草稿？',
          content: '已保存的内容可以从“待确认”继续编辑；尚未保存的修改不会保留。',
          okText: '关闭草稿',
          cancelText: '继续编辑',
          onOk: onClose,
        })
      }}
      maskClosable={false}
      destroyOnHidden
    >
      {query.isLoading ? (
        <Skeleton active />
      ) : query.error ? (
        <Alert
          type="error"
          title={query.error}
          action={<Button onClick={query.reload}>重试</Button>}
        />
      ) : (
        query.data && (
          <FeedbackDraftForm
            key={id}
            initial={query.data}
            onDirtyChange={changed}
            openCase={(caseId) => {
              onClose()
              openCase(caseId)
            }}
          />
        )
      )}
    </Modal>
  )
}
