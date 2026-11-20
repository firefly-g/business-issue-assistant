/** @description 读取当前业务最近的有效经验，页面写入成功后通过工作台修订号刷新。 */
import { Alert, Button, Skeleton } from 'antd'
import { ArrowRightOutlined, FileTextOutlined } from '@ant-design/icons'
import { Link } from 'react-router-dom'
import { useCases } from '../../hooks/useCases'
import { CaseRow } from '../../components/CaseRow'
import type { Business } from '../../types'

interface RecentCasesProps {
  /** 当前合法业务范围。 */
  business: Business
  /** 通过工作台路由打开案例详情。 */
  openCase: (id: string) => void
}

/** 仅展示已发布并验证的案例，示例标记由案例摘要继续显示。 */
export function RecentCases({ business, openCase }: RecentCasesProps) {
  const recent = useCases(business)
  const verified = (recent.data ?? [])
    .filter((item) => item.publication === 'published' && item.validity === 'verified')
    .slice(0, 3)
  return (
    <section className="recent-section">
      <div className="section-heading">
        <h2>近期已验证案例</h2>
        <Link to={`/cases?${new URLSearchParams({ business })}`}>
          查看案例库 <ArrowRightOutlined aria-hidden />
        </Link>
      </div>
      {recent.isLoading ? (
        <Skeleton active />
      ) : recent.error ? (
        <Alert
          type="error"
          title={recent.error}
          action={<Button onClick={recent.reload}>重试</Button>}
        />
      ) : verified.length ? (
        verified.map((item) => (
          <CaseRow key={item.id} item={item} onClick={() => openCase(item.id)} />
        ))
      ) : (
        <div className="empty-inline">
          <FileTextOutlined className="empty-icon" aria-hidden />
          <p>暂无已验证的案例</p>
          <Link to={`/intake?${new URLSearchParams({ business })}`}>
            收录经验 <ArrowRightOutlined aria-hidden />
          </Link>
        </div>
      )}
    </section>
  )
}
