/** @description 从生成的 OpenAPI 类型导出业务别名与有限状态文案，避免手写重复响应结构。 */
import type { components } from './api/generated'

/** 支持的业务分类，实际访问范围由服务端账号返回。 */
export type Business = components['schemas']['CaseRead']['business']
/** 公开账号，认证秘密由 HttpOnly Cookie 和后台维护。 */
export type User = components['schemas']['UserRead']
/** 案例安全投影，可见性由服务端校验。 */
export type Case = components['schemas']['CaseRead']
/** 分析引用保留当时版本，并标记当前可用性。 */
export type Citation = components['schemas']['CitationRead']
/** 草稿可编辑业务字段，不包含服务端维护的编号和状态。 */
export type DraftFields = Pick<
  Case,
  'title' | 'symptom' | 'conditions' | 'investigation' | 'cause' | 'solution' | 'verification'
>
/** 原始材料的公开投影。 */
export type Source = components['schemas']['SourceRead']
/** 本人提问与实际处理进度。 */
export type Question = components['schemas']['QuestionRead']
/** 提问、运行和反馈组合，运行引用已由服务端复核。 */
export type Analysis = components['schemas']['AnalysisRead']
/** 生成的经验预览，尚未写入案例。 */
export type DraftPreview = components['schemas']['DraftPreview']
/** 案例每个历史版本的完整投影。 */
export type Revision = components['schemas']['RevisionRead']
/** 当前可访问案例与个人提问的统计。 */
export type Overview = components['schemas']['OverviewRead']
/** 后台实际用于问题分析和收录预览的运行模式。 */
export type AnalysisMode = Overview['analysis_mode']

/** 发布状态文案，与方案有效性分别显示。 */
export const publicationLabels = {
  draft: '草稿',
  pending: '待确认',
  published: '已发布',
  archived: '已归档',
}
/** 方案有效性文案，问题解决不自动等于已验证。 */
export const validityLabels = { unverified: '待验证', verified: '已验证', invalid: '已失效' }
/** 问题处理进度文案。 */
export const progressLabels = { processing: '处理中', resolved: '已解决', reopened: '重新打开' }
/** 服务端角色的展示名称，界面可见性不赋予写入权限。 */
export const roleLabels = { member: '业务同事', handler: '问题处理人', maintainer: '知识维护人' }
/** 反馈结果文案，单次不适用与案例整体失效分别处理。 */
export const outcomeLabels = {
  resolved: '已解决',
  unresolved: '仍未解决',
  not_applicable: '方案不适用',
}
