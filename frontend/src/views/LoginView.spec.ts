// @vitest-environment jsdom
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus, { ElMessage } from 'element-plus'

const replaceMock = vi.fn()
const loginMock = vi.fn()
const fetchAuthorizedConnectionsMock = vi.fn()

vi.mock('vue-router', () => ({
  useRouter: () => ({
    replace: replaceMock
  })
}))

vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({
    login: loginMock,
    fetchAuthorizedConnections: fetchAuthorizedConnectionsMock,
    homePath: '/optimization-tasks'
  })
}))

import LoginView from './LoginView.vue'

describe('LoginView', () => {
  const warningSpy = vi.spyOn(ElMessage, 'warning').mockImplementation(() => null as any)
  const errorSpy = vi.spyOn(ElMessage, 'error').mockImplementation(() => null as any)

  function mountView() {
    return mount(LoginView, {
      global: {
        plugins: [ElementPlus]
      }
    })
  }

  beforeEach(() => {
    vi.clearAllMocks()
    loginMock.mockResolvedValue(undefined)
    fetchAuthorizedConnectionsMock.mockResolvedValue(undefined)
  })

  it('shows inline field errors when submitting empty form', async () => {
    const wrapper = mountView()

    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()

    expect(wrapper.text()).toContain('请输入工号')
    expect(wrapper.text()).toContain('请输入密码')
    expect(loginMock).not.toHaveBeenCalled()
    expect(warningSpy).toHaveBeenCalledWith('请输入工号和密码')
  })

  it('submits trimmed employee number and redirects on success', async () => {
    const wrapper = mountView()
    const inputs = wrapper.findAll('input')
    await inputs[0].setValue(' U1001 ')
    await inputs[1].setValue('Passw0rd!')

    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()

    expect(loginMock).toHaveBeenCalledWith({
      employee_no: 'U1001',
      password: 'Passw0rd!'
    })
    expect(fetchAuthorizedConnectionsMock).toHaveBeenCalled()
    expect(replaceMock).toHaveBeenCalledWith('/optimization-tasks')
  })

  it('shows authentication error message for invalid credentials', async () => {
    loginMock.mockRejectedValueOnce({ response: { status: 401 } })
    const wrapper = mountView()
    const inputs = wrapper.findAll('input')
    await inputs[0].setValue('U1001')
    await inputs[1].setValue('wrong-pass')

    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()

    expect(errorSpy).toHaveBeenCalledWith('您输入的用户名或密码错误，请重新输入')
    expect(wrapper.text()).not.toContain('请检查密码后重试')
  })
})
