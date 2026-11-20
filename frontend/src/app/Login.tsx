/** @description 维护登录表单、演示账号预填和失败恢复，提交时由身份 Service 验证凭证。 */
import { useState } from 'react'
import { Alert, Button, Form, Input } from 'antd'
import { ArrowRightOutlined } from '@ant-design/icons'
import { useSessionStore } from '../store/session'
import { errorMessage } from '../api/client'
import type { LoginInput } from '../api/services/identity'

// 开发和本地预览使用 README 公开的演示凭证，常规生产构建保持空表单。
const demoLoginValues: LoginInput | undefined =
  import.meta.env.DEV || import.meta.env.MODE === 'local-preview'
    ? { email: 'admin@example.com', password: 'local-dev-2026' }
    : undefined

/** 演示凭证可编辑，用户提交后由会话 Store 登录，失败时保留输入。 */
export function Login() {
  const [isBusy, setIsBusy] = useState(false)
  const [error, setError] = useState('')
  const login = useSessionStore((state) => state.login)
  async function submit(values: LoginInput) {
    setIsBusy(true)
    setError('')
    try {
      await login(values)
    } catch (reason: unknown) {
      setError(errorMessage(reason))
    } finally {
      setIsBusy(false)
    }
  }
  return (
    <main className="login-page">
      <div className="login-story">
        <div className="brand">
          <span className="brand-mark">知</span>业务问题助手
        </div>
        <div>
          <span className="eyebrow">团队经验，持续生长</span>
          <h1>
            把一次解决，
            <br />
            变成共同经验。
          </h1>
          <p>连接分散的问题与答案，让下一次排查有迹可循。</p>
        </div>
        <span className="login-foot">案例收录 · 经验检索 · 协作确认</span>
      </div>
      <section className="login-form">
        <span className="eyebrow">团队工作台</span>
        <h2>欢迎回来</h2>
        <p className="muted">登录后，接续团队的解决经验。</p>
        {error && <Alert type="error" title={error} showIcon />}
        <Form
          layout="vertical"
          initialValues={demoLoginValues}
          onFinish={(values: LoginInput) => void submit(values)}
          requiredMark={false}
        >
          <Form.Item
            label="工作邮箱"
            name="email"
            rules={[{ required: true, type: 'email', message: '请输入有效邮箱' }]}
          >
            <Input autoComplete="username" placeholder="请输入工作邮箱" size="large" />
          </Form.Item>
          <Form.Item
            label="密码"
            name="password"
            rules={[{ required: true, message: '请输入密码' }]}
          >
            <Input.Password autoComplete="current-password" placeholder="请输入密码" size="large" />
          </Form.Item>
          <Button type="primary" htmlType="submit" loading={isBusy} block size="large">
            进入工作台 <ArrowRightOutlined />
          </Button>
        </Form>
        <p className="login-hint">首次本地启动的账号配置见项目 README。</p>
      </section>
    </main>
  )
}
