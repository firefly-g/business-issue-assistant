/** @description 展示目标案例或冲突草稿与本地提案的逐字段差异，采用原值必须显式操作。 */
import { Button, Collapse } from 'antd'
import { draftFields } from '../../components/caseFields'
import type { DraftFields } from '../../types'

interface DraftComparisonProps {
  /** 对照区域的可读名称。 */
  title: string
  /** 原案例或最新服务端草稿的事实字段。 */
  original: DraftFields
  /** 尚未保存的本地字段，差异按实际文本比较。 */
  proposed: DraftFields
  /** 省略时仅查看；提供时逐字段复制原值，不自动覆盖其他字段。 */
  onUseOriginal?: (name: keyof DraftFields, value: string) => void
}

/** 手机按纵向排列原值和提案，长原文换行，不扩大对话框宽度。 */
export function DraftComparison({
  title,
  original,
  proposed,
  onUseOriginal,
}: DraftComparisonProps) {
  return (
    <Collapse
      items={[
        {
          key: 'comparison',
          label: title,
          children: (
            <div className="grid gap-4">
              {draftFields.map(({ name, label }) => (
                <section key={name}>
                  <strong>
                    {label}
                    {original[name] === proposed[name] ? '（相同）' : '（有差异）'}
                  </strong>
                  <div className="grid gap-3 md:grid-cols-2">
                    <div>
                      <small>原值</small>
                      <p className="whitespace-pre-wrap break-words">
                        {original[name] || '未填写'}
                      </p>
                    </div>
                    <div>
                      <small>本地提案</small>
                      <p className="whitespace-pre-wrap break-words">
                        {proposed[name] || '未填写'}
                      </p>
                    </div>
                  </div>
                  {onUseOriginal && original[name] !== proposed[name] && (
                    <Button size="small" onClick={() => onUseOriginal(name, original[name])}>
                      采用原值：{label}
                    </Button>
                  )}
                </section>
              ))}
            </div>
          ),
        },
      ]}
    />
  )
}
