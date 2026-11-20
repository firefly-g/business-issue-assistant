/** @description 收录页面组合原始材料和可校正草稿，工作流与错误恢复由业务 Hook 维护。 */
import type { Business } from '../../types'
import { DraftPreviewForm } from './DraftPreviewForm'
import { MaterialForm } from './MaterialForm'
import { useIntake } from './useIntake'

interface IntakePageProps {
  /** 当前可信账号允许访问的业务。 */
  business: Business
  /** 待确认草稿成功提交后定位新案例。 */
  onSaved: (id: string) => void
}

/** 草稿就绪后展开编辑区，保留原文供人工核对。 */
export function IntakePage({ business, onSaved }: IntakePageProps) {
  const controller = useIntake(business, onSaved)
  return (
    <div className={controller.preview ? 'intake-grid' : 'intake-start'}>
      <MaterialForm controller={controller} />
      {controller.preview && (
        <DraftPreviewForm controller={controller} preview={controller.preview} />
      )}
    </div>
  )
}
