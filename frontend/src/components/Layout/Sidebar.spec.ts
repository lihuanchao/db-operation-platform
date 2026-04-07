// @vitest-environment jsdom
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h, nextTick } from 'vue'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import Sidebar from './Sidebar.vue'
import { useAuthStore } from '@/stores/auth'
import { useLayoutStore } from '@/stores/layout'

const { pushSpy, routeState } = vi.hoisted(() => ({
  pushSpy: vi.fn(),
  routeState: {
    path: '/optimization-tasks'
  }
}))

vi.mock('vue-router', () => ({
  useRoute: () => routeState,
  useRouter: () => ({
    push: pushSpy
  })
}))

const ElMenuStub = defineComponent({
  name: 'ElMenu',
  props: {
    collapse: {
      type: Boolean,
      default: false
    },
    defaultActive: {
      type: String,
      default: ''
    }
  },
  setup(props, { slots, attrs }) {
    return () => h('nav', { ...attrs }, slots.default?.())
  }
})

const ElMenuItemStub = defineComponent({
  name: 'ElMenuItem',
  inheritAttrs: false,
  emits: ['click'],
  setup(_, { slots, attrs, emit }) {
    return () => h(
      'button',
      {
        ...attrs,
        type: 'button',
        onClick: () => emit('click')
      },
      slots.default?.()
    )
  }
})

const ElSubMenuStub = defineComponent({
  name: 'ElSubMenu',
  inheritAttrs: false,
  setup(_, { slots, attrs }) {
    return () => h('section', attrs, [
      h('div', { class: 'submenu-title' }, slots.title?.()),
      h('div', { class: 'submenu-content' }, slots.default?.())
    ])
  }
})

const ElIconStub = defineComponent({
  name: 'ElIcon',
  setup(_, { slots }) {
    return () => h('span', { class: 'el-icon-stub' }, slots.default?.())
  }
})

describe('Sidebar', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
    pushSpy.mockReset()
    routeState.path = '/optimization-tasks'
  })

  function mountSidebar(paths: string[]) {
    const authStore = useAuthStore()
    authStore.menus = paths.map((path) => ({
      path,
      label: path
    }))

    const wrapper = mount(Sidebar, {
      global: {
        stubs: {
          ElMenu: ElMenuStub,
          ElMenuItem: ElMenuItemStub,
          ElSubMenu: ElSubMenuStub,
          ElIcon: ElIconStub
        }
      }
    })

    return {
      wrapper,
      authStore,
      layoutStore: useLayoutStore()
    }
  }

  it('renders the permitted menu labels and keeps unauthorized entries hidden', () => {
    const { wrapper } = mountSidebar([
      '/optimization-tasks',
      '/archive-tasks',
      '/permissions'
    ])

    const text = wrapper.text()

    expect(text).toContain('SQL智能建议')
    expect(text).toContain('归档管理')
    expect(text).toContain('归档任务')
    expect(text).toContain('系统管理')
    expect(text).toContain('权限管理')
    expect(text).not.toContain('慢SQL管理')
    expect(text).not.toContain('连接管理')
  })

  it('pushes the matching path when a menu item is clicked', async () => {
    const { wrapper } = mountSidebar(['/slow-sqls'])

    await wrapper.get('[data-path="/slow-sqls"]').trigger('click')

    expect(pushSpy).toHaveBeenCalledWith('/slow-sqls')
  })

  it('maps active menu selection for nested routes', () => {
    routeState.path = '/slow-sql/abc'

    const slowSqlSidebar = mountSidebar(['/slow-sqls']).wrapper
    expect(slowSqlSidebar.getComponent(ElMenuStub).props('defaultActive')).toBe('/slow-sqls')

    routeState.path = '/optimization-tasks/123'

    const optimizationSidebar = mountSidebar(['/optimization-tasks']).wrapper
    expect(optimizationSidebar.getComponent(ElMenuStub).props('defaultActive')).toBe('/optimization-tasks')
  })

  it('passes the current layout collapsed state into ElMenu', async () => {
    const { wrapper, layoutStore } = mountSidebar(['/optimization-tasks'])

    expect(wrapper.getComponent(ElMenuStub).props('collapse')).toBe(false)

    layoutStore.collapsed = true
    await nextTick()

    expect(wrapper.getComponent(ElMenuStub).props('collapse')).toBe(true)
  })

  it('navigates to the clicked menu item path for top-level and nested entries', async () => {
    const { wrapper } = mountSidebar([
      '/optimization-tasks',
      '/execution-logs'
    ])

    await wrapper.get('[data-path="/optimization-tasks"]').trigger('click')
    await wrapper.get('[data-path="/execution-logs"]').trigger('click')

    expect(pushSpy).toHaveBeenNthCalledWith(1, '/optimization-tasks')
    expect(pushSpy).toHaveBeenNthCalledWith(2, '/execution-logs')
  })
})
