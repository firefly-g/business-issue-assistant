/** @description 展示保存的模型和唯一启用项，运行切换由页面统一提交。 */
import { Button, Empty, Tag } from 'antd'
import { CheckCircleOutlined, EditOutlined, ThunderboltOutlined } from '@ant-design/icons'
import type { ModelLibrary, ModelProfile } from '../../api/services/modelSettings'

interface ModelProfileListProps {
  /** 当前团队目录与实际启用的配置编号。 */
  library: ModelLibrary
  /** 切换期间禁用行操作，避免提交相互覆盖。 */
  switching: boolean
  /** 将选中的配置用于团队后续请求。 */
  onActivate: (id: string) => void
  /** 进入已有配置的编辑表单。 */
  onEdit: (profile: ModelProfile) => void
}

/** 原连接地址和模型名称同时展示，便于区分不同供应商的同名模型。 */
export function ModelProfileList({
  library,
  switching,
  onActivate,
  onEdit,
}: ModelProfileListProps) {
  if (!library.profiles.length)
    return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="还没有模型配置" />
  return (
    <ul className="model-profile-list">
      {library.profiles.map((profile) => {
        const active = profile.id === library.active_profile_id
        return (
          <li
            key={profile.id}
            className={active ? 'model-profile-row model-profile-active' : 'model-profile-row'}
          >
            <div className="model-profile-detail">
              <div className="model-profile-title">
                <strong>{profile.model}</strong>
                {active && (
                  <Tag color="success" icon={<CheckCircleOutlined />}>
                    已启用
                  </Tag>
                )}
                {profile.id === 'environment' && <Tag>环境变量</Tag>}
              </div>
              <span className="model-profile-address">{profile.address}</span>
            </div>
            <div className="model-profile-actions">
              {profile.id !== 'environment' && (
                <Button
                  type="text"
                  icon={<EditOutlined />}
                  disabled={switching}
                  onClick={() => onEdit(profile)}
                >
                  编辑
                </Button>
              )}
              {!active && (
                <Button
                  icon={<ThunderboltOutlined />}
                  disabled={switching}
                  onClick={() => onActivate(profile.id)}
                >
                  启用
                </Button>
              )}
            </div>
          </li>
        )
      })}
    </ul>
  )
}
