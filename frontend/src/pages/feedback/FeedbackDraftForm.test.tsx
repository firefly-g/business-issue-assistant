/** @description 验证真实表单的版本冲突恢复与未保存发布保护，领域服务使用可控替身。 */
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { App } from 'antd'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../../api/client'
import * as cases from '../../api/services/cases'
import * as drafts from '../../api/services/feedbackDrafts'
import { useSessionStore } from '../../store/session'
import { FeedbackDraftForm } from './FeedbackDraftForm'
import { draftFixture, targetFixture } from './feedbackDraft.fixture'

vi.mock('../../api/services/cases')
vi.mock('../../api/services/feedbackDrafts')

afterEach(cleanup)
beforeEach(() => {
  vi.resetAllMocks()
  useSessionStore.setState({
    user: {
      id: 'maintainer',
      email: 'test@example.com',
      name: '合成维护人',
      role: 'maintainer',
      businesses: ['订单售后'],
    },
  })
  vi.mocked(cases.listCases).mockResolvedValue([targetFixture])
})

describe('反馈草稿人工校正', () => {
  it('目标版本冲突后保留输入，人工采用新版本并重新保存才能发布', async () => {
    const user = userEvent.setup()
    const draft = draftFixture('revise')
    vi.mocked(cases.readCase).mockResolvedValue({
      ...targetFixture,
      version: 3,
      conditions: '最新限制',
    })
    vi.mocked(drafts.updateFeedbackDraft)
      .mockRejectedValueOnce(new ApiError(409, 'TARGET_VERSION_CONFLICT', '目标案例已更新'))
      .mockImplementationOnce((_id, data) => Promise.resolve({ ...draft, ...data, version: 3 }))
    render(
      <App>
        <FeedbackDraftForm initial={draft} openCase={vi.fn()} />
      </App>,
    )
    const title = screen.getByLabelText('案例标题')
    await user.clear(title)
    await user.type(title, '人工合并后的标题')
    expect(screen.getByRole('button', { name: '确认并发布修订' }).hasAttribute('disabled')).toBe(
      true,
    )
    await user.click(screen.getByRole('button', { name: /保存并提交人工确认/ }))
    const adopt = await screen.findByRole('button', { name: /已核对，采用目标版本 v3/ })
    expect((title as HTMLInputElement).value).toBe('人工合并后的标题')
    await user.click(adopt)
    expect(screen.getByRole('button', { name: '确认并发布修订' }).hasAttribute('disabled')).toBe(
      true,
    )
    await user.click(screen.getByRole('button', { name: /保存并提交人工确认/ }))
    await waitFor(() => expect(drafts.updateFeedbackDraft).toHaveBeenCalledTimes(2))
    expect(vi.mocked(drafts.updateFeedbackDraft).mock.calls[1]?.[1]).toMatchObject({
      version: 2,
      target_version: 3,
      content: { title: '人工合并后的标题' },
    })
    await waitFor(() =>
      expect(screen.getByRole('button', { name: '确认并发布修订' }).hasAttribute('disabled')).toBe(
        false,
      ),
    )
  })

  it('其他人更新草稿时只读取对照内容，明确采用新版本后仍保存本地输入', async () => {
    const user = userEvent.setup()
    const draft = draftFixture()
    vi.mocked(drafts.updateFeedbackDraft)
      .mockRejectedValueOnce(new ApiError(409, 'VERSION_CONFLICT', '草稿已更新'))
      .mockImplementationOnce((_id, data) => Promise.resolve({ ...draft, ...data, version: 5 }))
    vi.mocked(drafts.readFeedbackDraft).mockResolvedValue({
      ...draft,
      version: 4,
      content: { ...draft.content, title: '其他人修改的标题' },
    })
    render(
      <App>
        <FeedbackDraftForm initial={draft} openCase={vi.fn()} />
      </App>,
    )
    const title = screen.getByLabelText('案例标题')
    await user.clear(title)
    await user.type(title, '我的未保存修改')
    await user.click(screen.getByRole('button', { name: /保存并提交人工确认/ }))
    await user.click(await screen.findByRole('button', { name: /已核对，采用草稿版本 v4/ }))
    expect((title as HTMLInputElement).value).toBe('我的未保存修改')
    await user.click(screen.getByRole('button', { name: /保存并提交人工确认/ }))
    await waitFor(() => expect(drafts.updateFeedbackDraft).toHaveBeenCalledTimes(2))
    expect(vi.mocked(drafts.updateFeedbackDraft).mock.calls[1]?.[1]).toMatchObject({
      version: 4,
      content: { title: '我的未保存修改' },
    })
  })

  it('发布网络失败后保持同一请求键，避免重试重复应用案例变更', async () => {
    const user = userEvent.setup()
    const draft = draftFixture()
    vi.mocked(drafts.publishFeedbackDraft)
      .mockRejectedValueOnce(new ApiError(0, 'NETWORK_ERROR', '网络中断'))
      .mockResolvedValueOnce({
        ...draft,
        status: 'published',
        version: 3,
        published_case_id: 'case',
        published_case_version: 1,
      })
    render(
      <App>
        <FeedbackDraftForm initial={draft} openCase={vi.fn()} />
      </App>,
    )
    await user.click(screen.getByRole('button', { name: '确认并发布新案例' }))
    await screen.findByText('网络中断')
    await user.click(screen.getByRole('button', { name: '确认并发布新案例' }))
    await screen.findByText('已发布到案例 v1')
    const calls = vi.mocked(drafts.publishFeedbackDraft).mock.calls
    expect(calls).toHaveLength(2)
    expect(calls[0]?.[2]).toBe(calls[1]?.[2])
    expect(calls[0]?.[1].validity).toBe('unverified')
  })
})
