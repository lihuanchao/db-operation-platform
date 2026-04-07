// @vitest-environment jsdom
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import AppLayout from './AppLayout.vue'
import { HOME_TAB, useLayoutStore } from '@/stores/layout'
import { useAuthStore } from '@/stores/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/optimization-tasks',
    component: { template: '<div>home</div>' }
  },
  {
    path: '/slow-sqls',
    component: { template: '<div>slow</div>' }
  },
  {
    path: '/login',
    component: { template: '<div>login</div>' }
  }
]

describe('AppLayout', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
  })

  async function mountLayout(initialPath = '/optimization-tasks') {
    const router = createRouter({
      history: createMemoryHistory(),
      routes
    })

    await router.push(initialPath)
    await router.isReady()

    const authStore = useAuthStore()
    authStore.user = {
      id: 1,
      employee_no: 'A0001',
      real_name: '系统管理员',
      department: '平台组',
      role_code: 'admin',
      status: 'enabled'
    }

    const wrapper = mount(AppLayout, {
      slots: {
        default: '<div class="slot-content">content</div>'
      },
      global: {
        plugins: [router],
        stubs: {
          Sidebar: {
            template: '<aside class="sidebar-stub">sidebar</aside>'
          }
        }
      }
    })

    await flushPromises()

    return {
      wrapper,
      router,
      layoutStore: useLayoutStore(),
      authStore
    }
  }

  it('renders the topbar brand and current username', async () => {
    const { wrapper } = await mountLayout()

    expect(wrapper.find('[data-testid="brand-logo"]').exists()).toBe(true)
    expect(wrapper.get('[data-testid="brand-title"]').text()).toBe('中国重汽数据库运维平台')
    expect(wrapper.get('[data-testid="user-name"]').text()).toBe('系统管理员')
  })

  it('toggles layoutStore.collapsed after clicking the collapse control', async () => {
    const { wrapper, layoutStore } = await mountLayout()

    expect(layoutStore.collapsed).toBe(false)

    await wrapper.get('[data-testid="collapse-toggle"]').trigger('click')

    expect(layoutStore.collapsed).toBe(true)
  })

  it('pushes the matching route when a non-home tab is clicked', async () => {
    const { wrapper, router, layoutStore } = await mountLayout()
    const pushSpy = vi.spyOn(router, 'push')

    layoutStore.openTab('/slow-sqls', '慢SQL列表')
    await flushPromises()

    await wrapper.get('[data-tab-path="/slow-sqls"]').trigger('click')

    expect(pushSpy).toHaveBeenCalledWith('/slow-sqls')
  })

  it('returns to the home tab after closing the active non-home tab', async () => {
    const { wrapper, router, layoutStore } = await mountLayout('/slow-sqls')
    const pushSpy = vi.spyOn(router, 'push')

    layoutStore.openTab('/slow-sqls', '慢SQL列表')
    layoutStore.activateTab('/slow-sqls')
    await flushPromises()

    await wrapper.get('[data-close-path="/slow-sqls"]').trigger('click')
    await flushPromises()

    expect(pushSpy).toHaveBeenCalledWith('/optimization-tasks')
    expect(layoutStore.activePath).toBe(HOME_TAB.path)
    expect(layoutStore.tabs).toEqual([HOME_TAB])
  })

  it('does not render a close button for the home tab', async () => {
    const { wrapper } = await mountLayout()

    expect(wrapper.find('[data-close-path="/optimization-tasks"]').exists()).toBe(false)
  })
})
