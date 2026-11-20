/** @description 维护工作台稳定导航，界面入口不承担服务端授权。 */
import {
  BookOutlined,
  CheckSquareOutlined,
  HistoryOutlined,
  MessageOutlined,
  PlusOutlined,
  SettingOutlined,
} from '@ant-design/icons'

/** 工作台支持的稳定路由路径。 */
export type PagePath =
  '/assistant' | '/cases' | '/intake' | '/records' | '/review' | '/settings/model'
interface NavigationItem {
  path: PagePath
  title: string
  /** 页面含义需要展开时使用，导航仍显示简短名称。 */
  pageTitle?: string
  icon: typeof MessageOutlined
}
/** 路由名称与导航图标的唯一配置，权限始终由后台核对。 */
export const navigation: NavigationItem[] = [
  { path: '/assistant', title: '问题助手', icon: MessageOutlined },
  { path: '/cases', title: '团队案例库', icon: BookOutlined },
  { path: '/intake', title: '收录经验', icon: PlusOutlined },
  { path: '/records', title: '我的提问', icon: HistoryOutlined },
  { path: '/review', title: '待确认', pageTitle: '待确认经验', icon: CheckSquareOutlined },
]

/** 模型配置作用于整个团队，入口独立于按业务工作的主导航。 */
export const modelSettings: NavigationItem = {
  path: '/settings/model',
  title: '模型配置',
  icon: SettingOutlined,
}
