/** @description 维护本人提问列表及详情定位，失败和空状态均提供明确入口。 */
import { useState } from 'react'
import { Alert, Button, Empty, Skeleton, Tag } from 'antd'
import { ArrowRightOutlined } from '@ant-design/icons'
import { Link } from 'react-router-dom'
import { listQuestions } from '../../api/services/analysis'
import { useQuery } from '../../hooks/useQuery'
import type { Business } from '../../types'
import { progressLabels } from '../../types'
import { QuestionDialog } from './QuestionDialog'

interface RecordsPageProps {
  /** 从工作台继承的合法业务，空状态导航时保留。 */
  business: Business
  /** 用工作台路由查看案例，后台核验真实权限。 */
  openCase: (id: string) => void
}

/** 个人列表不能借维护人角色扩大到其他同事的提问。 */
export function RecordsPage({ business, openCase }: RecordsPageProps) {
  const state = useQuery({ key: 'questions', load: listQuestions })
  const [selected, setSelected] = useState<string | null>(null)
  return (
    <>
      {state.error && (
        <Alert
          type="error"
          title={state.error}
          action={<Button onClick={state.reload}>重试</Button>}
        />
      )}
      {state.isLoading ? (
        <Skeleton active />
      ) : !state.data?.length ? (
        <Empty description="还没有提问记录">
          <Link to={`/assistant?${new URLSearchParams({ business })}`}>开始第一次提问</Link>
        </Empty>
      ) : (
        <div className="panel records-list">
          {state.data.map((item) => (
            <button className="record-row" key={item.id} onClick={() => setSelected(item.id)}>
              <span>
                <strong>{item.text}</strong>
                <small>
                  {item.business} · {new Date(item.created_at).toLocaleString('zh-CN')}
                </small>
              </span>
              <Tag color={item.progress === 'resolved' ? 'green' : 'default'}>
                {progressLabels[item.progress]}
              </Tag>
              <ArrowRightOutlined />
            </button>
          ))}
        </div>
      )}
      {selected && (
        <QuestionDialog
          key={selected}
          id={selected}
          onClose={() => setSelected(null)}
          openCase={openCase}
          onFeedback={state.reload}
        />
      )}
    </>
  )
}
