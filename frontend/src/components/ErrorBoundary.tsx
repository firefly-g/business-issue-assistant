/** @description 为应用壳与懒加载页面提供可恢复的渲染失败状态，不记录用户输入内容。 */
import { Component } from 'react'
import type { ReactNode } from 'react'
import { Alert, Button } from 'antd'

interface ErrorBoundaryProps {
  /** 被保护的应用或页面内容。 */
  children: ReactNode
}
interface ErrorBoundaryState {
  failed: boolean
}

/** 渲染异常不清理服务端事实，用户可重新加载应用恢复。 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { failed: false }
  static getDerivedStateFromError(): ErrorBoundaryState {
    return { failed: true }
  }
  render(): ReactNode {
    if (this.state.failed)
      return (
        <div className="connection-error">
          <Alert
            type="error"
            title="页面暂时无法显示"
            showIcon
            action={<Button onClick={() => location.reload()}>重新加载</Button>}
          />
        </div>
      )
    return this.props.children
  }
}
