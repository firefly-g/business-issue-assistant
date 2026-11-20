/** @description React Router 维护工作台页面、默认跳转和不存在页面，保留 Hash 路由部署方式。 */
import { lazy, Suspense } from 'react'
import { Alert, Spin } from 'antd'
import { Link, Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import type { Business, User } from '../types'
import { modelSettings } from './navigation'

const Assistant = lazy(() =>
  import('../pages/assistant/AssistantPage').then((module) => ({ default: module.AssistantPage })),
)
const Cases = lazy(() =>
  import('../pages/cases/CaseLibraryPage').then((module) => ({ default: module.CaseLibraryPage })),
)
const Intake = lazy(() =>
  import('../pages/intake/IntakePage').then((module) => ({ default: module.IntakePage })),
)
const Records = lazy(() =>
  import('../pages/records/RecordsPage').then((module) => ({ default: module.RecordsPage })),
)
const ModelSettings = lazy(() =>
  import('../pages/settings/ModelSettingsPage').then((module) => ({
    default: module.ModelSettingsPage,
  })),
)
interface WorkspaceRoutesProps {
  /** 当前已验证属于账号范围的业务。 */
  business: Business
  /** 在 URL 中打开案例定位。 */
  openCase: (id: string) => void
  /** 用于控制团队管理界面入口，不能代替服务端授权。 */
  role: User['role']
  /** 团队配置成功保存后刷新页头运行状态。 */
  onModelSaved: () => void
}

/** 每个业务范围重新挂载页面，隔离旧表单和晚到请求。 */
export function WorkspaceRoutes({ business, openCase, role, onModelSaved }: WorkspaceRoutesProps) {
  const navigate = useNavigate()
  return (
    <Suspense fallback={<Spin description="正在加载页面" />}>
      <Routes>
        <Route
          path="/"
          element={<Navigate to={`/assistant?${new URLSearchParams({ business })}`} replace />}
        />
        <Route
          path="/assistant"
          element={<Assistant key={business} business={business} openCase={openCase} />}
        />
        <Route
          path="/cases"
          element={<Cases key={business} business={business} openCase={openCase} />}
        />
        <Route
          path="/review"
          element={<Cases key={business} review business={business} openCase={openCase} />}
        />
        <Route
          path="/intake"
          element={
            <Intake
              key={business}
              business={business}
              onSaved={(id) => {
                void navigate(`/review?${new URLSearchParams({ business, case: id })}`)
              }}
            />
          }
        />
        <Route path="/records" element={<Records business={business} openCase={openCase} />} />
        <Route
          path={modelSettings.path}
          element={
            role === 'maintainer' ? (
              <ModelSettings onSaved={onModelSaved} />
            ) : (
              <Alert type="warning" title="仅知识维护人可以访问模型配置" showIcon />
            )
          }
        />
        <Route
          path="*"
          element={<Link to={`/assistant?${new URLSearchParams({ business })}`}>返回问题助手</Link>}
        />
      </Routes>
    </Suspense>
  )
}
