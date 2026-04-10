// @vitest-environment jsdom
import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'

vi.mock('@/stores/dbConnection', () => ({
  useDbConnectionStore: () => ({
    testConnectionDirectAction: vi.fn(),
    editConnection: vi.fn(),
    addConnection: vi.fn()
  })
}))

import ConnectionForm from './ConnectionForm.vue'

describe('ConnectionForm', () => {
  it('renders with readable placeholder inputs and disables browser autofill', () => {
    const wrapper = mount(ConnectionForm, {
      global: {
        plugins: [ElementPlus]
      }
    })

    expect(wrapper.find('.connection-form').exists()).toBe(true)

    const nameInput = wrapper.find('input[placeholder="请输入连接名称"]')
    const hostInput = wrapper.find('input[placeholder="请输入主机地址"]')
    const usernameInput = wrapper.find('input[placeholder="请输入用户名"]')
    const passwordInput = wrapper.find('input[placeholder="请输入密码"]')

    expect(nameInput.exists()).toBe(true)
    expect(hostInput.exists()).toBe(true)
    expect(usernameInput.exists()).toBe(true)
    expect(passwordInput.exists()).toBe(true)

    expect(nameInput.attributes('autocomplete')).toBe('off')
    expect(hostInput.attributes('autocomplete')).toBe('off')
    expect(usernameInput.attributes('autocomplete')).toBe('off')
    expect(passwordInput.attributes('autocomplete')).toBe('new-password')
  })
})
