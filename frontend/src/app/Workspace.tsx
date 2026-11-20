/** @description 装配路由、页面标题、业务范围和案例定位，URL 保存可分享状态，Zustand 保存跨页面客户端选择。 */
import { lazy, Suspense, useCallback } from 'react'
import { Alert, App, Button, Spin } from 'antd'
import { matchPath, useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { errorMessage } from '../api/client'
import { readOverview } from '../api/services/overview'
import { useQuery } from '../hooks/useQuery'
import { useSessionStore } from '../store/session'
import { useWorkspaceStore } from '../store/workspace'
import type { Business, User } from '../types'
import { Sidebar } from './Sidebar'
import { WorkspaceHeader } from './WorkspaceHeader'
import { WorkspaceRoutes } from './WorkspaceRoutes'
import { modelSettings, navigation } from './navigation'

const CaseDetail = lazy(() =>
  import('../pages/cases/CaseDetail').then((module) => ({ default: module.CaseDetail })),
)
interface WorkspaceProps {
  /** 已由服务端会话校验的公开身份，账号改变时应用入口重新挂载。 */
  user: User
}

/** 工作台集中处理业务切换和写入后的查询失效，实际资源授权仍由后台执行。 */
export function Workspace({ user }: WorkspaceProps) {
  const { message } = App.useApp()
  const location = useLocation()
  const navigate = useNavigate()
  const [search, setSearch] = useSearchParams()
  const selectedBusiness = useWorkspaceStore((state) => state.business)
  const selectBusiness = useWorkspaceStore((state) => state.selectBusiness)
  const reuseCase = useWorkspaceStore((state) => state.reuseCase)
  const revision = useWorkspaceStore((state) => state.revision)
  const refresh = useWorkspaceStore((state) => state.refresh)
  const logout = useSessionStore((state) => state.logout)
  const business =
    user.businesses.find((item) => item === search.get('business')) ??
    selectedBusiness ??
    user.businesses[0]
  const overview = useQuery({ key: `overview:${user.id}:${revision}`, load: readOverview })
  const pathname = location.pathname === '/' ? '/assistant' : location.pathname
  const isModelSettings = matchPath(modelSettings.path, pathname) !== null
  const currentPage = isModelSettings
    ? modelSettings
    : navigation.find((item) => matchPath(item.path, pathname))
  const pageTitle = currentPage?.pageTitle ?? currentPage?.title ?? '页面不存在'
  const openCase = useCallback(
    (id: string) =>
      setSearch((previous) => {
        const next = new URLSearchParams(previous)
        next.set('case', id)
        return next
      }),
    [setSearch],
  )
  const onLogout = async () => {
    try {
      await logout()
    } catch (reason: unknown) {
      void message.error(errorMessage(reason))
    }
  }
  if (!business)
    return (
      <Alert
        type="warning"
        title="当前账号没有可访问业务，请联系维护人。"
        action={<Button onClick={() => void onLogout()}>退出登录</Button>}
      />
    )
  function changeBusiness(next: Business) {
    selectBusiness(next)
    setSearch(new URLSearchParams({ business: next }))
  }
  const selectedCase = isModelSettings ? null : search.get('case')
  return (
    <div className="workspace min-h-screen">
      <Sidebar
        user={user}
        business={business}
        pending={overview.data?.pending ?? 0}
        onLogout={() => void onLogout()}
      />
      <div className="main-shell min-h-screen flex flex-col">
        <WorkspaceHeader
          title={pageTitle}
          business={business}
          businesses={user.businesses}
          analysisMode={
            currentPage?.path === '/assistant' ? overview.data?.analysis_mode : undefined
          }
          showBusiness={!isModelSettings}
          onBusiness={changeBusiness}
          onLogout={() => void onLogout()}
        />
        <main className="main-content flex-1">
          <WorkspaceRoutes
            business={business}
            openCase={openCase}
            role={user.role}
            onModelSaved={refresh}
          />
        </main>
      </div>
      <Suspense fallback={<Spin fullscreen />}>
        {selectedCase && (
          <CaseDetail
            key={selectedCase}
            id={selectedCase}
            user={user}
            onClose={() =>
              setSearch(
                (previous) => {
                  const next = new URLSearchParams(previous)
                  next.delete('case')
                  return next
                },
                { replace: true },
              )
            }
            onUpdated={refresh}
            onReuse={(text, nextBusiness) => {
              reuseCase(text, nextBusiness)
              void navigate(`/assistant?${new URLSearchParams({ business: nextBusiness })}`)
            }}
          />
        )}
      </Suspense>
    </div>
  )
}
