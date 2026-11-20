/** @description 管理团队已保存的模型，列表切换运行状态，编辑弹窗保管临时凭证。 */
import { useRef, useState } from 'react'
import { Alert, Button, Modal, Spin } from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import { errorMessage } from '../../api/client'
import { activateModelProfile, readModelLibrary } from '../../api/services/modelSettings'
import type { ModelLibrary, ModelProfile } from '../../api/services/modelSettings'
import { useQuery } from '../../hooks/useQuery'
import { useRequestScope } from '../../hooks/useRequestScope'
import { ModelProfileList } from './ModelProfileList'
import { ModelSettingsForm } from './ModelSettingsForm'
import './modelSettings.css'

interface ModelSettingsPageProps {
  /** 保存或切换后刷新工作台页头的运行模式。 */
  onSaved: () => void
}

/** 列表为主要入口，新增与启用分别提交，防止添加备用模型改变团队运行。 */
export function ModelSettingsPage({ onSaved }: ModelSettingsPageProps) {
  const { data, isLoading, error, reload } = useQuery({
    key: 'team-model-library',
    load: readModelLibrary,
  })
  const [editing, setEditing] = useState<{
    profile?: ModelProfile
    credential?: ModelProfile
  } | null>(null)
  const [latest, setLatest] = useState<ModelLibrary | null>(null)
  const [switching, setSwitching] = useState(false)
  const [switchError, setSwitchError] = useState('')
  const inFlight = useRef(false)
  const begin = useRequestScope()
  const library = latest ?? data
  const active = library?.profiles.find((item) => item.id === library.active_profile_id)

  function accept(next: ModelLibrary) {
    setLatest(next)
    setSwitchError('')
    setEditing(null)
    onSaved()
  }

  function refresh() {
    setLatest(null)
    setEditing(null)
    setSwitchError('')
    reload()
  }

  async function activate(id: string | null) {
    if (!library || inFlight.current) return
    const scope = begin()
    inFlight.current = true
    setSwitching(true)
    setSwitchError('')
    try {
      const next = await activateModelProfile(id, library.version, scope.signal)
      if (!scope.signal.aborted) accept(next)
    } catch (reason: unknown) {
      if (!scope.signal.aborted) setSwitchError(errorMessage(reason))
    } finally {
      scope.complete()
      inFlight.current = false
      if (!scope.signal.aborted) setSwitching(false)
    }
  }

  return (
    <div className="model-settings">
      {(error || switchError) && (
        <Alert
          className="mb-5"
          type="error"
          showIcon
          title={error || switchError}
          action={<Button onClick={refresh}>重新加载</Button>}
        />
      )}
      {isLoading && <Spin description="正在读取模型配置" />}
      {library && (
        <div className="model-settings-grid">
          <section className="panel min-w-0" aria-labelledby="model-list-title">
            <div className="model-list-heading">
              <h2 id="model-list-title">已保存的模型</h2>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                disabled={switching}
                onClick={() => setEditing({ credential: active ?? library.profiles[0] })}
              >
                新增模型
              </Button>
            </div>
            <ModelProfileList
              library={library}
              switching={switching}
              onActivate={(id) => void activate(id)}
              onEdit={(profile) => setEditing({ profile, credential: profile })}
            />
          </section>
          <aside
            className="model-context panel"
            aria-labelledby="model-status-title"
            aria-live="polite"
          >
            <h2 id="model-status-title">团队运行模式</h2>
            <strong className="model-live-mode">
              {library.mode === 'model' ? '模型辅助' : '本地规则'}
            </strong>
            {active && <p className="model-active-name">{active.model}</p>}
            {library.mode === 'model' && (
              <Button block disabled={switching} onClick={() => void activate(null)}>
                切换为本地规则
              </Button>
            )}
          </aside>
          <Modal
            open={editing !== null}
            title={editing?.profile ? '编辑模型配置' : '新增模型配置'}
            onCancel={() => setEditing(null)}
            footer={null}
            destroyOnHidden
          >
            {editing && (
              <ModelSettingsForm
                profile={editing.profile}
                credential={editing.credential}
                version={library.version}
                onSaved={accept}
                onReload={refresh}
              />
            )}
          </Modal>
        </div>
      )}
    </div>
  )
}
