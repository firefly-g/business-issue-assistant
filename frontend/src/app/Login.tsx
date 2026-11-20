/** @description 维护登录表单、演示账号预填和失败恢复，提交时由身份 Service 验证凭证。 */
import { useState } from 'react'
import { Alert, Button, Form, Input } from 'antd'
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
      <section className="login-form">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">
            知
          </span>
          <h1>业务问题助手</h1>
        </div>
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
            <Input autoComplete="username" size="large" />
          </Form.Item>
          <Form.Item
            label="密码"
            name="password"
            rules={[{ required: true, message: '请输入密码' }]}
          >
            <Input.Password autoComplete="current-password" size="large" />
          </Form.Item>
          <Button type="primary" htmlType="submit" loading={isBusy} block size="large">
            登录
          </Button>
        </Form>
      </section>
    </main>
  )
}
