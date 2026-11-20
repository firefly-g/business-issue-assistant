/** @description 团队模型配置的同源接口，供应商目录与凭证操作通过服务端转发。 */
import { request } from '../client'
import { decode } from '../decoder'
import type { components } from '../generated'

/** 单套模型连接，只暴露地址、名称和密钥状态。 */
export type ModelProfile = components['schemas']['ModelProfileRead']
/** 团队模型列表及具备独立版本的启用状态。 */
export type ModelLibrary = components['schemas']['ModelLibraryRead']
/** 查询供应商目录只需要地址、密钥及现有配置版本。 */
export type ModelCatalogInput = components['schemas']['ModelCatalogInput']
/** 单次测试输入，空密钥仅允许复用相同地址的既有凭证。 */
export type ModelConnectionInput = components['schemas']['ModelConnectionInput']
/** 保存一套通过测试的连接所需参数。 */
export type ModelProfileInput = components['schemas']['ModelProfileInput']

/** 从后台读取当前配置，访问权限由服务端确认。 */
export async function readModelLibrary(signal?: AbortSignal) {
  return decode('ModelLibraryRead', await request('/settings/model/profiles', { signal }))
}

/** 读取当前密钥可见的模型，密钥只放在请求体内。 */
export async function fetchModelCatalog(data: ModelCatalogInput, signal: AbortSignal) {
  return decode(
    'ModelCatalogRead',
    await request('/settings/model/models', { method: 'POST', data, signal }),
  )
}

/** 用合成内容验证连接，成功后返回与此次输入绑定的凭证。 */
export async function testModelSettings(data: ModelConnectionInput, signal: AbortSignal) {
  return decode(
    'ModelTestRead',
    await request('/settings/model/test', { method: 'POST', data, signal }),
  )
}

/** 保存通过测试的配置，提供编号时更新该项。 */
export async function saveModelProfile(data: ModelProfileInput, signal: AbortSignal, id?: string) {
  return decode(
    'ModelLibraryRead',
    await request(
      id ? `/settings/model/profiles/${encodeURIComponent(id)}` : '/settings/model/profiles',
      {
        method: id ? 'PUT' : 'POST',
        data,
        signal,
      },
    ),
  )
}

/** 启用选定配置，空编号切换为本地规则。 */
export async function activateModelProfile(
  profileId: string | null,
  version: number,
  signal: AbortSignal,
) {
  return decode(
    'ModelLibraryRead',
    await request('/settings/model/active', {
      method: 'PUT',
      data: { profile_id: profileId, version },
      signal,
    }),
  )
}
