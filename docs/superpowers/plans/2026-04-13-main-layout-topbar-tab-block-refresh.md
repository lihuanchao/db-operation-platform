# Main Layout Topbar Tab Block Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将主布局顶部任务栏标签改为彼此分离的紧凑独立方块，选中态为浅灰底，并保留顶部红色标识。

**Architecture:** 保持 `AppLayout` 的结构、路由同步和标签交互逻辑不变，仅调整顶部标签的 DOM 类名和样式层次。通过先写失败测试锁定“独立方块工业风”语义，再用最小样式修改实现视觉变更，最后回归现有交互与键盘可访问性测试。

**Tech Stack:** Vue 3 `<script setup>`, TypeScript, scoped CSS, Vitest, Vue Test Utils

---

## File Structure

- Modify: `frontend/src/components/Layout/AppLayout.spec.ts`
  - 职责：补充“独立方块工业风”语义测试，并维持顶部任务栏交互回归覆盖。
- Modify: `frontend/src/components/Layout/AppLayout.vue`
  - 职责：实现独立方块样式、浅灰选中态、顶部红色标识和关闭按钮的方正视觉。

### Task 1: Lock The Visual Semantics With A Failing Test

**Files:**
- Modify: `frontend/src/components/Layout/AppLayout.spec.ts`
- Test: `frontend/src/components/Layout/AppLayout.spec.ts`

- [ ] **Step 1: Add the failing tab chrome test**

`frontend/src/components/Layout/AppLayout.spec.ts`

```ts
  it('renders industrial rectangular tab chrome for task navigation', async () => {
    const { wrapper, layoutStore } = await mountLayout()

    layoutStore.openTab('/slow-sqls', 'SQL巡检')
    await flushPromises()

    const tabs = wrapper.findAll('.header-tab')
    expect(tabs.length).toBe(2)
    expect(tabs[0].classes()).toContain('header-tab--industrial')
    expect(tabs[1].classes()).toContain('header-tab--industrial')

    const closeButton = wrapper.get('.tab-close')
    expect(closeButton.classes()).toContain('tab-close--industrial')
  })
```

- [ ] **Step 2: Run the focused test to verify RED**

Run:

```bash
cd frontend && npm test -- AppLayout.spec.ts -t "renders industrial rectangular tab chrome for task navigation"
```

Expected: FAIL with `expected [ 'header-tab' ] to include 'header-tab--industrial'`.

### Task 2: Implement Compact Independent Tab Blocks

**Files:**
- Modify: `frontend/src/components/Layout/AppLayout.vue`
- Test: `frontend/src/components/Layout/AppLayout.spec.ts`

- [ ] **Step 1: Add the tab classes and preserve test selectors**

`frontend/src/components/Layout/AppLayout.vue`

```vue
        <div
          v-for="tab in layoutStore.tabs"
          :key="tab.path"
          class="header-tab header-tab--industrial"
          :class="{ 'is-active': layoutStore.activePath === tab.path }"
          :data-tab-path="tab.path"
          @click="openTab(tab.path)"
        >
          <span class="tab-title">{{ tab.title }}</span>
          <button
            v-if="tab.closable"
            class="tab-close tab-close--industrial"
            :data-close-path="tab.path"
            @click.stop="closeTab(tab.path)"
            @keydown.enter.stop.prevent="closeTab(tab.path)"
            @keydown.space.stop.prevent="closeTab(tab.path)"
          >
            ×
          </button>
        </div>
```

- [ ] **Step 2: Replace contiguous tab styling with independent blocks**

`frontend/src/components/Layout/AppLayout.vue`

```css
.header-tabs {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
  overflow-x: auto;
  padding: 0;
}

.header-tab {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 40px;
  padding: 0 14px;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 0;
  cursor: pointer;
  transition: background-color 0.15s ease, border-color 0.15s ease, color 0.15s ease;
  flex-shrink: 0;
  position: relative;
}

.header-tab::before {
  content: '';
  position: absolute;
  top: -1px;
  left: -1px;
  right: -1px;
  height: 3px;
  background: #dc2626;
}

.header-tab:hover {
  background: #f8fafc;
  border-color: #94a3b8;
}

.header-tab.is-active {
  background: #e5e7eb;
  border-color: #94a3b8;
  color: #1f2937;
  box-shadow: none;
}

.tab-title {
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.02em;
  color: #475569;
  white-space: nowrap;
}

.header-tab.is-active .tab-title {
  color: #1f2937;
}

.tab-close {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid transparent;
  background: transparent;
  color: #94a3b8;
  font-size: 13px;
  line-height: 1;
  cursor: pointer;
  border-radius: 0;
  transition: background-color 0.15s ease, border-color 0.15s ease, color 0.15s ease;
}

.tab-close:hover {
  background: #d1d5db;
  border-color: #94a3b8;
  color: #334155;
}
```

- [ ] **Step 3: Run the focused test to verify GREEN**

Run:

```bash
cd frontend && npm test -- AppLayout.spec.ts -t "renders industrial rectangular tab chrome for task navigation"
```

Expected: PASS.

### Task 3: Run Full AppLayout Regression

**Files:**
- Modify: `frontend/src/components/Layout/AppLayout.vue`
- Modify: `frontend/src/components/Layout/AppLayout.spec.ts`
- Test: `frontend/src/components/Layout/AppLayout.spec.ts`

- [ ] **Step 1: Run the full layout test suite**

Run:

```bash
cd frontend && npm test -- AppLayout.spec.ts
```

Expected: PASS with `14 passed`.

- [ ] **Step 2: Verify the requested visual outcome in code review**

Check these final selectors in `frontend/src/components/Layout/AppLayout.vue`:

```css
.header-tabs { gap: 8px; }
.header-tab { background: #ffffff; border-radius: 0; }
.header-tab::before { background: #dc2626; }
.header-tab.is-active { background: #e5e7eb; }
```

Expected: 独立方块、浅灰选中态、顶部红色标识都能从样式定义直接读出来。

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/Layout/AppLayout.vue frontend/src/components/Layout/AppLayout.spec.ts docs/superpowers/specs/2026-04-13-main-layout-topbar-tab-block-refresh-design.md docs/superpowers/plans/2026-04-13-main-layout-topbar-tab-block-refresh.md
git commit -m "feat: refresh topbar tab blocks"
```
