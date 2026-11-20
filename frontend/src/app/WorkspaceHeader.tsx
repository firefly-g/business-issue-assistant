/** @description 显示工作台页面的主标题与业务选择，角色和数据权限不由头部选项授予。 */
import { Button, Select } from 'antd'
import { LogoutOutlined } from '@ant-design/icons'
import type { AnalysisMode, Business } from '../types'

interface WorkspaceHeaderProps {
  /** 当前路由标题。 */
  title: string
  /** 当前业务，来自合法 URL 参数或账号范围内的选择。 */
  business: Business
  /** 服务端账号允许的业务选项。 */
  businesses: Business[]
  /** 问题助手显示的分析方式，统计未就绪或失败时为空，避免误报。 */
  analysisMode?: AnalysisMode
  /** 模型配置为团队级页面，不受当前业务选择影响。 */
  showBusiness: boolean
  /** 选择业务时清理旧筛选并切换请求范围。 */
  onBusiness: (value: Business) => void
  /** 移动端同样提供真实退出操作。 */
  onLogout: () => void
}

/** 统一呈现页面主标题，通过回调切换业务范围并触发页面重新加载数据。 */
export function WorkspaceHeader({
  title,
  business,
  businesses,
  analysisMode,
  showBusiness,
  onBusiness,
  onLogout,
}: WorkspaceHeaderProps) {
  return (
    <header className="topbar">
      <div className="topbar-inner">
        <h1>{title}</h1>
        <div className="topbar-right">
          {analysisMode && (
            <span className="mode-label">{analysisMode === 'model' ? '模型辅助' : '本地规则'}</span>
          )}
          {showBusiness && (
            <Select
              aria-label="当前业务"
              value={business}
              onChange={onBusiness}
              options={businesses.map((value) => ({ value, label: value }))}
            />
          )}
          <Button
            className="mobile-logout"
            type="text"
            aria-label="退出登录"
            icon={<LogoutOutlined />}
            onClick={onLogout}
          />
        </div>
      </div>
    </header>
  )
}
