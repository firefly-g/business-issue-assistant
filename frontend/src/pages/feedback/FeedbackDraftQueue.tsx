/** @description 在待确认页面列出当前业务反馈草稿，工作台写入后刷新列表但保留已打开编辑。 */
import { useCallback, useState } from 'react'
import { Alert, Button, Empty, Segmented, Skeleton, Tag } from 'antd'
import { listFeedbackDrafts } from '../../api/services/feedbackDrafts'
import { useQuery } from '../../hooks/useQuery'
import { useWorkspaceStore } from '../../store/workspace'
import type { Business } from '../../types'
import { FeedbackDraftDialog } from './FeedbackDraftDialog'
import { feedbackDraftStatus } from './draftFields'

interface FeedbackDraftQueueProps {
  /** 当前账号选择的授权业务，切换时由工作台重新挂载。 */
  business: Business
  /** 查看发布后的案例，沿用工作台路由。 */
  openCase: (id: string) => void
}

/** 已发布项独立查看，普通成员和处理角色的可见范围由服务端决定。 */
export function FeedbackDraftQueue({ business, openCase }: FeedbackDraftQueueProps) {
  const revision = useWorkspaceStore((state) => state.revision)
  const load = useCallback(
    (signal: AbortSignal) => listFeedbackDrafts(business, signal),
    [business],
  )
  const query = useQuery({ key: `feedback-drafts:${business}:${revision}`, load })
  const [filter, setFilter] = useState('待处理')
  const [selected, setSelected] = useState<string | null>(null)
  const items =
    query.data?.filter((item) => (item.status === 'published') === (filter === '已发布')) ?? []
  return (
    <section className="panel mb-4">
      <div className="section-heading">
        <h2>处理反馈案例草稿</h2>
        <Segmented
          aria-label="反馈草稿状态"
          value={filter}
          onChange={setFilter}
          options={['待处理', '已发布']}
        />
      </div>
      {query.isLoading ? (
        <Skeleton active />
      ) : query.error ? (
        <Alert
          type="error"
          title={query.error}
          action={<Button onClick={query.reload}>重试</Button>}
        />
      ) : !items.length ? (
        <Empty
          description={filter === '已发布' ? '暂无已发布的反馈草稿' : '暂无待处理的反馈草稿'}
        />
      ) : (
        items.map((item) => (
          <button className="record-row" key={item.id} onClick={() => setSelected(item.id)}>
            <span>
              <strong>{item.content.title}</strong>
              <small>
                {item.kind === 'create' ? '新增案例' : '修订案例'} ·{' '}
                {new Date(item.updated_at).toLocaleString('zh-CN')}
              </small>
            </span>
            <Tag>{feedbackDraftStatus[item.status]}</Tag>
          </button>
        ))
      )}
      {selected && (
        <FeedbackDraftDialog
          key={selected}
          id={selected}
          onClose={() => setSelected(null)}
          openCase={openCase}
        />
      )}
    </section>
  )
}
