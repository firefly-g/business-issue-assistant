/** @description 问题助手页面组合输入、历史经验及分析，服务端数据由业务 Hook 维护。 */
import { Alert, Button } from 'antd'
import { useWorkspaceStore } from '../../store/workspace'
import type { Business } from '../../types'
import { AnalysisResult } from './AnalysisResult'
import { QuestionComposer } from './QuestionComposer'
import { RecentCases } from './RecentCases'
import { useAssistant } from './useAssistant'

interface AssistantPageProps {
  /** 当前已验证属于账号范围的业务。 */
  business: Business
  /** 打开案例深链，由工作台维护定位。 */
  openCase: (id: string) => void
}

/** 跨页面复用是明确的新问题意图，nonce 改变时丢弃旧分析表单。 */
export function AssistantPage(props: AssistantPageProps) {
  const selection = useWorkspaceStore((state) => state.reuse)
  const reuse = selection?.business === props.business ? selection : null
  return <AssistantContent key={reuse?.nonce ?? 'new'} {...props} initialText={reuse?.text ?? ''} />
}
function AssistantContent({
  business,
  openCase,
  initialText,
}: AssistantPageProps & { initialText: string }) {
  const controller = useAssistant(business, initialText)
  return (
    <div className="assistant-main">
      <QuestionComposer controller={controller} />
      {controller.error && (
        <Alert
          className="mt-4"
          type="error"
          title={controller.error}
          showIcon
          action={<Button onClick={() => void controller.submit()}>重试</Button>}
        />
      )}
      {controller.result && (
        <AnalysisResult
          value={controller.result}
          openCase={openCase}
          onFeedback={controller.refreshResult}
        />
      )}
      <RecentCases business={business} openCase={openCase} />
    </div>
  )
}
