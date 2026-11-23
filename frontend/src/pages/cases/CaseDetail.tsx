/** @description 案例详情组合事实、授权原文、已采用反馈与历史版本，确认编辑由独立表单维护。 */
import { Alert, Button, Drawer, Tabs, Tag } from 'antd'
import type { Business, Case, User } from '../../types'
import { publicationLabels, validityLabels } from '../../types'
import { CaseEditForm } from './CaseEditForm'
import { RevisionHistory } from './RevisionHistory'
import { SourceEvidence } from './SourceEvidence'
import { FeedbackEvidence } from './FeedbackEvidence'
import { useCaseDetail } from './useCaseDetail'

interface CaseDetailProps {
  /** 路由中的案例定位，服务端核验权限和存在性。 */
  id: string
  /** 可信账号，仅用于展示角色和编辑入口。 */
  user: User
  /** 删除当前案例 URL 参数。 */
  onClose: () => void
  /** 服务端保存成功后刷新受影响的列表。 */
  onUpdated: () => void
  /** 复用为新问题时同时携带真实业务。 */
  onReuse: (text: string, business: Business) => void
}

/** 详情不缓存账号范围外的原文，Tab 在实际访问时读取对应材料。 */
export function CaseDetail({ id, user, onClose, onUpdated, onReuse }: CaseDetailProps) {
  const controller = useCaseDetail(id, onUpdated)
  const item = controller.query.data
  const canEdit =
    item &&
    (user.role === 'maintainer' ||
      (!['published', 'archived'].includes(item.publication) &&
        (item.owner_id === user.id || user.role === 'handler')))
  return (
    <Drawer
      open
      title="案例详情"
      size={740}
      onClose={onClose}
      destroyOnHidden
      loading={controller.query.isLoading}
    >
      {controller.query.error ? (
        <Alert
          type="error"
          title={controller.query.error}
          action={<Button onClick={controller.query.reload}>重试</Button>}
        />
      ) : (
        item && (
          <>
            <div className="detail-tags">
              <Tag>{item.business}</Tag>
              <Tag color={item.validity === 'verified' ? 'green' : 'default'}>
                {validityLabels[item.validity]}
              </Tag>
              <Tag>{publicationLabels[item.publication]}</Tag>
              {item.is_demo && <Tag>虚构示例</Tag>}
              <span className="muted">v{item.version}</span>
            </div>
            <h2 className="detail-title">{item.title}</h2>
            <div className="detail-actions">
              <Button onClick={() => onReuse(item.symptom, item.business)}>用于新问题</Button>
              {canEdit && (
                <Button
                  type="primary"
                  onClick={() => controller.setIsEditing(!controller.isEditing)}
                >
                  {controller.isEditing ? '取消编辑' : '编辑与确认'}
                </Button>
              )}
            </div>
            {controller.isEditing ? (
              <CaseEditForm value={item} role={user.role} onSave={controller.save} />
            ) : (
              <Tabs
                items={[
                  { key: 'content', label: '处理经验', children: <CaseContent item={item} /> },
                  {
                    key: 'source',
                    label: '原始依据',
                    children: (
                      <>
                        <SourceEvidence sourceId={item.source_id} />
                        <FeedbackEvidence caseId={item.id} version={item.version} />
                      </>
                    ),
                  },
                  {
                    key: 'history',
                    label: '版本记录',
                    children: <RevisionHistory caseId={item.id} />,
                  },
                ]}
              />
            )}
          </>
        )
      )}
    </Drawer>
  )
}
function CaseContent({ item }: { item: Case }) {
  const fields = [
    ['问题现象', item.symptom],
    ['适用条件', item.conditions],
    ['排查过程', item.investigation],
    ['原因说明', item.cause],
    ['处理步骤', item.solution],
    ['验证结果', item.verification],
  ]
  return (
    <div className="detail-content">
      {fields.map(([label, value]) => (
        <section key={label}>
          <h3>{label}</h3>
          <p>{value || '待补充'}</p>
        </section>
      ))}
      <p className="muted">更新于 {new Date(item.updated_at).toLocaleString('zh-CN')}</p>
    </div>
  )
}
