/** @description 展示工作台导航和可信身份，路由和退出行为由应用壳统一处理。 */
import { Avatar, Badge, Button } from 'antd'
import { LogoutOutlined } from '@ant-design/icons'
import { NavLink } from 'react-router-dom'
import type { Business, User } from '../types'
import { roleLabels } from '../types'
import { modelSettings, navigation } from './navigation'

interface SidebarProps {
  /** 后台返回的当前账号。 */
  user: User
  /** 当前业务，跳转时保留该范围。 */
  business: Business
  /** 后台可见的待确认数量。 */
  pending: number
  /** 用户主动退出时调用，真实会话撤销由身份 Service 完成。 */
  onLogout: () => void
}

/** 导航保持业务参数，个人身份不持久化到浏览器存储。 */
export function Sidebar({ user, business, pending, onLogout }: SidebarProps) {
  const search = `?${new URLSearchParams({ business })}`
  const canManageModel = user.role === 'maintainer'
  const SettingsIcon = modelSettings.icon
  const settingsLink = (variant: string) => (
    <NavLink
      to={`${modelSettings.path}${search}`}
      className={({ isActive }) => `${variant}${isActive ? ' active' : ''}`}
    >
      <SettingsIcon aria-hidden />
      <span>{modelSettings.title}</span>
    </NavLink>
  )
  return (
    <aside className="sidebar flex flex-col">
      <div className="sidebar-brand flex items-center justify-between">
        <NavLink className="brand" to={`/assistant${search}`}>
          <span className="brand-mark" aria-hidden="true">
            知
          </span>
          业务问题助手
        </NavLink>
        {canManageModel && settingsLink('mobile-model-link')}
      </div>
      <nav aria-label="主导航">
        {navigation.map((item) => {
          const Icon = item.icon
          return (
            <NavLink
              key={item.path}
              to={`${item.path}${search}`}
              className={({ isActive }) => (isActive ? 'nav-item active' : 'nav-item')}
            >
              <Icon aria-hidden />
              <span>{item.title}</span>
              {item.path === '/review' && pending > 0 && <Badge count={pending} color="#176655" />}
            </NavLink>
          )
        })}
      </nav>
      {canManageModel && (
        <nav className="settings-nav" aria-label="团队管理">
          {settingsLink('nav-item')}
        </nav>
      )}
      <div className="profile">
        <Avatar style={{ background: '#e6ece5', color: '#34604d' }}>{user.name.slice(0, 1)}</Avatar>
        <span>
          <strong>{user.name}</strong>
          {user.name !== roleLabels[user.role] && <small>{roleLabels[user.role]}</small>}
        </span>
        <Button type="text" aria-label="退出登录" icon={<LogoutOutlined />} onClick={onLogout} />
      </div>
    </aside>
  )
}
