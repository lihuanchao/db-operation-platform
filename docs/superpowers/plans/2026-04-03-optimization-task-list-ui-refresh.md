# Optimization Task List UI Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将优化任务列表页改造成“新建任务入口优先”的轻量工作台，在保留列表筛选、刷新、分页和详情跳转的前提下补齐首屏状态概览与更统一的浅色后台视觉。

**Architecture:** 继续沿用现有 `frontend/src/views/OptimizationTaskList.vue` 单文件组件入口，不改 Pinia store 契约，只在页面层增加入口卡片、状态概览和新的列表工具区。新增一个页面级 Vitest 文件，通过真实 store + API mock 验证入口跳转、状态统计、类型筛选、刷新、分页与空状态，从而把改造范围严格限制在 UI 层。

**Tech Stack:** Vue 3 `<script setup>`, TypeScript, Pinia, Vue Router, Element Plus, Vitest, Vue Test Utils

---

## File Structure

- Modify: `frontend/src/views/OptimizationTaskList.vue`
  责任：将当前“按钮 + 表格”页面重构为“入口优先型”任务工作台，新增状态概览、入口卡片、工具条与空状态布局。
- Create: `frontend/src/views/OptimizationTaskList.spec.ts`
  责任：覆盖页面级行为，包括入口跳转、状态卡统计、类型筛选、刷新、分页和空状态文案。

## Task 1: Lock The New Task Workspace Behavior With A View Test

**Files:**
- Create: `frontend/src/views/OptimizationTaskList.spec.ts`
- Modify: `frontend/src/views/OptimizationTaskList.vue`
- Test: `frontend/src/views/OptimizationTaskList.spec.ts`

- [ ] **Step 1: Write the failing page-level test**

`frontend/src/views/OptimizationTaskList.spec.ts`

```ts
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ElementPlus from 'element-plus'
import type { OptimizationTask } from '@/types'

const pushMock = vi.fn()

const { getOptimizationTaskListMock } = vi.hoisted(() => ({
  getOptimizationTaskListMock: vi.fn()
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: pushMock
  })
}))

vi.mock('@/api/optimizationTask', () => ({
  getOptimizationTaskList: getOptimizationTaskListMock,
  getOptimizationTaskDetail: vi.fn(),
  createSqlOptimizationTask: vi.fn(),
  createMyBatisOptimizationTask: vi.fn()
}))

import OptimizationTaskList from './OptimizationTaskList.vue'

function buildTask(overrides: Partial<OptimizationTask> = {}): OptimizationTask {
  return {
    id: 101,
    task_type: 'sql',
    object_preview: 'SELECT * FROM orders WHERE id = 1',
    db_connection_id: 1,
    database_name: 'orders',
    database_host: '10.0.0.11',
    status: 'queued',
    progress: 0,
    created_at: '2026-04-03 10:00:00',
    updated_at: '2026-04-03 10:00:00',
    ...overrides
  }
}

function buildListResponse(items: OptimizationTask[], total = items.length, page = 1, perPage = 10) {
  return {
    success: true,
    data: {
      items,
      total,
      page,
      per_page: perPage
    }
  }
}

describe('OptimizationTaskList', () => {
  function mountView() {
    const pinia = createPinia()
    setActivePinia(pinia)

    return mount(OptimizationTaskList, {
      global: {
        plugins: [pinia, ElementPlus],
        stubs: {
          AppLayout: {
            template: '<div class="layout-stub"><slot /></div>'
          }
        }
      }
    })
  }

  beforeEach(() => {
    vi.clearAllMocks()

    getOptimizationTaskListMock.mockResolvedValue(
      buildListResponse(
        [
          buildTask({ id: 101, task_type: 'sql', status: 'queued' }),
          buildTask({ id: 102, task_type: 'mybatis', status: 'running', object_preview: '<select id=\"findOrders\">...</select>' }),
          buildTask({ id: 103, task_type: 'sql', status: 'completed', object_preview: 'SELECT id, name FROM users' }),
          buildTask({ id: 104, task_type: 'mybatis', status: 'failed', object_preview: '<select id=\"findUsers\">...</select>' })
        ],
        14
      )
    )
  })

  it('renders the entry workspace and summary cards from fetched tasks', async () => {
    const wrapper = mountView()
    await flushPromises()

    expect(getOptimizationTaskListMock).toHaveBeenCalledWith({
      page: 1,
      per_page: 10,
      task_type: ''
    })
    expect(wrapper.text()).toContain('创建新的优化任务，并跟踪历史结果与状态')
    expect(wrapper.findAll('.entry-card')).toHaveLength(2)

    const summaryCards = wrapper.findAll('.summary-card')
    expect(summaryCards).toHaveLength(4)
    expect(summaryCards[0].text()).toContain('任务总数')
    expect(summaryCards[0].text()).toContain('14')
    expect(summaryCards[1].text()).toContain('优化中')
    expect(summaryCards[1].text()).toContain('2')
    expect(summaryCards[2].text()).toContain('已完成')
    expect(summaryCards[2].text()).toContain('1')
    expect(summaryCards[3].text()).toContain('失败')
    expect(summaryCards[3].text()).toContain('1')
  })

  it('navigates from both entry cards and the task object link', async () => {
    const wrapper = mountView()
    await flushPromises()

    await wrapper.find('button.entry-card--sql').trigger('click')
    await wrapper.find('button.entry-card--mybatis').trigger('click')
    await wrapper.find('button.task-link').trigger('click')

    expect(pushMock).toHaveBeenNthCalledWith(1, '/optimization-tasks/create/sql')
    expect(pushMock).toHaveBeenNthCalledWith(2, '/optimization-tasks/create/mybatis')
    expect(pushMock).toHaveBeenNthCalledWith(3, '/optimization-tasks/101')
  })

  it('filters, refreshes, and paginates with the existing store contract', async () => {
    const wrapper = mountView()
    await flushPromises()

    await wrapper.findAll('.filter-chip')[2].trigger('click')
    await flushPromises()
    expect(getOptimizationTaskListMock).toHaveBeenLastCalledWith({
      page: 1,
      per_page: 10,
      task_type: 'mybatis'
    })

    await wrapper.find('button.refresh-button').trigger('click')
    await flushPromises()
    expect(getOptimizationTaskListMock).toHaveBeenLastCalledWith({
      page: 1,
      per_page: 10,
      task_type: 'mybatis'
    })

    const pagination = wrapper.findComponent({ name: 'ElPagination' })
    pagination.vm.$emit('current-change', 2)
    await flushPromises()
    expect(getOptimizationTaskListMock).toHaveBeenLastCalledWith({
      page: 2,
      per_page: 10,
      task_type: 'mybatis'
    })

    pagination.vm.$emit('size-change', 20)
    await flushPromises()
    expect(getOptimizationTaskListMock).toHaveBeenLastCalledWith({
      page: 1,
      per_page: 20,
      task_type: 'mybatis'
    })
  })

  it('shows the guided empty state when there is no task data', async () => {
    getOptimizationTaskListMock.mockResolvedValueOnce(buildListResponse([], 0))

    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.text()).toContain('还没有优化任务，先从上方创建一个新任务')
    expect(wrapper.find('.task-table').exists()).toBe(false)
  })
})
```

- [ ] **Step 2: Run the view test to confirm the current page fails**

Run:

```bash
cd frontend && npm test -- src/views/OptimizationTaskList.spec.ts
```

Expected: FAIL，当前页面还没有 `.entry-card`、`.summary-card`、`.filter-chip`、`.refresh-button` 和引导式空状态，因此测试会因结构缺失或文案不匹配失败。

- [ ] **Step 3: Replace the page template and script with the new entry-first workspace**

`frontend/src/views/OptimizationTaskList.vue`

将现有 `<template>` 与 `<script setup>` 替换为以下内容，先保留旧的 `<style scoped>`，样式在 Task 2 中统一重写：

```vue
<template>
  <AppLayout>
    <div class="page-header">
      <div>
        <h2>优化任务列表</h2>
        <p>创建新的优化任务，并跟踪历史结果与状态</p>
      </div>
    </div>

    <section class="entry-grid" aria-label="创建优化任务">
      <button type="button" class="entry-card entry-card--sql" @click="goToCreateSql">
        <span class="entry-card__eyebrow">SQL 工作台</span>
        <strong class="entry-card__title">优化单个 SQL 查询</strong>
        <span class="entry-card__desc">适合快速分析单条查询语句的写法、执行计划与索引建议。</span>
        <span class="entry-card__cta">立即创建任务</span>
      </button>

      <button type="button" class="entry-card entry-card--mybatis" @click="goToCreateMyBatis">
        <span class="entry-card__eyebrow">XML 工作台</span>
        <strong class="entry-card__title">优化 MyBatis XML 文件</strong>
        <span class="entry-card__desc">适合对 ORM 映射片段进行查询提取、写法调整与索引检查。</span>
        <span class="entry-card__cta">进入 XML 优化</span>
      </button>
    </section>

    <section class="summary-grid" aria-label="任务状态概览">
      <article
        v-for="card in summaryCards"
        :key="card.key"
        class="summary-card"
        :class="`is-${card.tone}`"
      >
        <span class="summary-card__label">{{ card.label }}</span>
        <strong class="summary-card__value">{{ card.value }}</strong>
        <span class="summary-card__hint">{{ card.hint }}</span>
      </article>
    </section>

    <el-card shadow="never" class="table-card">
      <div class="table-shell">
        <div class="table-head">
          <div>
            <h3>历史任务</h3>
            <p>共 {{ store.total }} 条任务记录</p>
          </div>

          <div class="table-actions">
            <div class="filter-group" role="tablist" aria-label="任务类型筛选">
              <button
                v-for="option in filterOptions"
                :key="option.value || 'all'"
                type="button"
                class="filter-chip"
                :class="{ 'is-active': store.taskType === option.value }"
                @click="handleTypeChange(option.value)"
              >
                {{ option.label }}
              </button>
            </div>

            <el-button class="refresh-button" @click="store.fetchList">刷新</el-button>
          </div>
        </div>

        <div v-if="!store.loading && store.list.length === 0" class="table-empty">
          <strong>还没有优化任务，先从上方创建一个新任务</strong>
          <p>创建后，这里会显示任务状态、数据库信息和查看结果入口。</p>
        </div>

        <template v-else>
          <el-table :data="store.list" v-loading="store.loading" class="task-table">
            <el-table-column label="类型" width="110">
              <template #default="{ row }">
                <span class="type-pill" :class="`type-pill--${row.task_type}`">
                  {{ row.task_type === 'sql' ? 'SQL' : 'MyBatis' }}
                </span>
              </template>
            </el-table-column>

            <el-table-column label="对象" min-width="280" show-overflow-tooltip>
              <template #default="{ row }">
                <div class="task-object">
                  <el-button link type="primary" class="task-link" @click="goToDetail(row.id)">
                    {{ row.object_preview }}
                  </el-button>
                  <span class="task-subline">{{ row.database_name }} · {{ row.database_host }}</span>
                </div>
              </template>
            </el-table-column>

            <el-table-column label="状态" width="110">
              <template #default="{ row }">
                <span class="status-pill" :class="`status-pill--${row.status}`">
                  {{ statusText(row.status) }}
                </span>
              </template>
            </el-table-column>

            <el-table-column prop="database_name" label="库名" width="120" />
            <el-table-column prop="database_host" label="数据库IP" width="140" />
            <el-table-column prop="created_at" label="创建时间" width="170" />

            <el-table-column label="操作" width="90" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="goToDetail(row.id)">查看</el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-pagination
            class="task-pagination"
            v-model:current-page="store.page"
            v-model:page-size="store.perPage"
            :total="store.total"
            :page-sizes="[10, 20, 50]"
            layout="total, sizes, prev, pager, next"
            @current-change="handlePageChange"
            @size-change="handleSizeChange"
          />
        </template>
      </div>
    </el-card>
  </AppLayout>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import AppLayout from '@/components/Layout/AppLayout.vue'
import { useOptimizationTaskStore } from '@/stores/optimizationTask'
import type { OptimizationTaskStatus, OptimizationTaskType } from '@/types'

const router = useRouter()
const store = useOptimizationTaskStore()

const filterOptions: Array<{ label: string; value: OptimizationTaskType | '' }> = [
  { label: '全部', value: '' },
  { label: 'SQL', value: 'sql' },
  { label: 'MyBatis', value: 'mybatis' }
]

const summaryCards = computed(() => {
  const runningCount = store.list.filter(
    (item) => item.status === 'queued' || item.status === 'running'
  ).length
  const completedCount = store.list.filter((item) => item.status === 'completed').length
  const failedCount = store.list.filter((item) => item.status === 'failed').length

  return [
    {
      key: 'total',
      label: '任务总数',
      value: store.total,
      hint: '当前筛选范围',
      tone: 'neutral'
    },
    {
      key: 'running',
      label: '优化中',
      value: runningCount,
      hint: '当前页任务',
      tone: 'warning'
    },
    {
      key: 'completed',
      label: '已完成',
      value: completedCount,
      hint: '可查看结果',
      tone: 'success'
    },
    {
      key: 'failed',
      label: '失败',
      value: failedCount,
      hint: '需要复查',
      tone: 'danger'
    }
  ]
})

onMounted(() => {
  store.fetchList()
})

function goToCreateSql() {
  router.push('/optimization-tasks/create/sql')
}

function goToCreateMyBatis() {
  router.push('/optimization-tasks/create/mybatis')
}

function goToDetail(id: number) {
  router.push(`/optimization-tasks/${id}`)
}

function handleTypeChange(value: OptimizationTaskType | '') {
  if (store.taskType === value) return
  store.setTaskType(value || '')
  store.fetchList()
}

function handlePageChange(page: number) {
  store.setPage(page)
  store.fetchList()
}

function handleSizeChange(size: number) {
  store.setPerPage(size)
  store.fetchList()
}

function statusText(status: OptimizationTaskStatus) {
  if (status === 'queued') return '优化中'
  if (status === 'running') return '优化中'
  if (status === 'completed') return '完成'
  return '失败'
}
</script>
```

- [ ] **Step 4: Run the targeted view test to verify the new workspace passes**

Run:

```bash
cd frontend && npm test -- src/views/OptimizationTaskList.spec.ts
```

Expected: PASS，4 个用例通过，说明入口区、状态概览、详情跳转、筛选、刷新、分页与空状态行为都已经连通。

- [ ] **Step 5: Commit the tested workspace refactor**

Run:

```bash
git add frontend/src/views/OptimizationTaskList.vue frontend/src/views/OptimizationTaskList.spec.ts
git commit -m "feat: refresh optimization task list workspace"
```

## Task 2: Apply The Final Light Enterprise Visual Polish

**Files:**
- Modify: `frontend/src/views/OptimizationTaskList.vue`
- Test: `frontend/src/views/OptimizationTaskList.spec.ts`

- [ ] **Step 1: Replace the old scoped styles with the final polished layout**

`frontend/src/views/OptimizationTaskList.vue`

将现有 `<style scoped>` 整块替换为：

```vue
<style scoped>
.page-header {
  margin-bottom: 18px;
}

.page-header h2 {
  margin: 0;
  font-size: 26px;
  font-weight: 700;
  color: #0f2a3d;
}

.page-header p {
  margin: 6px 0 0;
  color: #5f7287;
  font-size: 14px;
}

.entry-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 16px;
}

.entry-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 10px;
  width: 100%;
  padding: 22px;
  border: 1px solid #d9e6f2;
  border-radius: 20px;
  background: #ffffff;
  box-shadow: 0 18px 40px rgba(15, 42, 61, 0.06);
  text-align: left;
  cursor: pointer;
  transition:
    border-color 0.18s ease,
    box-shadow 0.18s ease,
    background-color 0.18s ease,
    transform 0.18s ease;
}

.entry-card:hover {
  border-color: #7dd3fc;
  box-shadow: 0 18px 36px rgba(3, 105, 161, 0.1);
  transform: translateY(-1px);
}

.entry-card:focus-visible {
  outline: none;
  border-color: #0369a1;
  box-shadow: 0 0 0 3px rgba(3, 105, 161, 0.16);
}

.entry-card--sql {
  background: #ffffff;
}

.entry-card__eyebrow {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 5px 10px;
  border-radius: 999px;
  background: #e8f3fb;
  color: #075985;
  font-size: 12px;
  font-weight: 700;
}

.entry-card__title {
  color: #0f2a3d;
  font-size: 20px;
  font-weight: 700;
  line-height: 1.3;
}

.entry-card__desc {
  color: #5f7287;
  font-size: 14px;
  line-height: 1.7;
}

.entry-card__cta {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 8px 12px;
  border-radius: 999px;
  background: #f3f7fb;
  color: #0f2a3d;
  font-size: 13px;
  font-weight: 600;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.summary-card {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 18px;
  border: 1px solid #d9e6f2;
  border-radius: 18px;
  background: #ffffff;
}

.summary-card.is-neutral {
  background: #f8fbfd;
}

.summary-card.is-warning {
  background: #fff9eb;
  border-color: #f6d28b;
}

.summary-card.is-success {
  background: #f1fbf7;
  border-color: #b8e5d2;
}

.summary-card.is-danger {
  background: #fff4f4;
  border-color: #f2c8c8;
}

.summary-card__label {
  color: #5f7287;
  font-size: 12px;
  font-weight: 600;
}

.summary-card__value {
  color: #0f2a3d;
  font-size: 28px;
  line-height: 1;
}

.summary-card__hint {
  color: #73879b;
  font-size: 12px;
}

.table-card {
  border: 1px solid #d9e6f2;
  border-radius: 20px;
  background: #ffffff;
  box-shadow: 0 18px 40px rgba(15, 42, 61, 0.06);
}

.table-shell {
  padding: 22px;
}

.table-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.table-head h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: #0f2a3d;
}

.table-head p {
  margin: 4px 0 0;
  color: #6b7c8f;
  font-size: 13px;
}

.table-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px;
  border-radius: 999px;
  background: #f3f7fb;
}

.filter-chip {
  border: none;
  border-radius: 999px;
  padding: 8px 14px;
  background: transparent;
  color: #536779;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition:
    background-color 0.18s ease,
    color 0.18s ease,
    box-shadow 0.18s ease;
}

.filter-chip:hover {
  color: #0f2a3d;
}

.filter-chip.is-active {
  background: #ffffff;
  color: #0369a1;
  box-shadow: 0 6px 18px rgba(15, 42, 61, 0.08);
}

.filter-chip:focus-visible {
  outline: none;
  box-shadow: 0 0 0 3px rgba(3, 105, 161, 0.16);
}

.refresh-button.el-button {
  border-color: #d7e3ef;
  color: #33546b;
}

.table-empty {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
  padding: 32px;
  border: 1px dashed #d9e6f2;
  border-radius: 18px;
  background: #f8fbfd;
}

.table-empty strong {
  color: #0f2a3d;
  font-size: 16px;
}

.table-empty p {
  margin: 0;
  color: #64748b;
  font-size: 14px;
  line-height: 1.7;
}

.task-object {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.task-link.el-button {
  justify-content: flex-start;
  margin: 0;
  padding: 0;
  font-weight: 700;
}

.task-subline {
  color: #64748b;
  font-size: 12px;
}

.type-pill,
.status-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 76px;
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}

.type-pill--sql {
  background: #e0f2fe;
  color: #075985;
}

.type-pill--mybatis {
  background: #e9fdf3;
  color: #047857;
}

.status-pill--queued,
.status-pill--running {
  background: #fff7dd;
  color: #9a6700;
}

.status-pill--completed {
  background: #eafaf2;
  color: #047857;
}

.status-pill--failed {
  background: #feecec;
  color: #b42318;
}

.task-pagination {
  margin-top: 18px;
  justify-content: flex-end;
}

:deep(.el-table) {
  border-radius: 16px;
  overflow: hidden;
}

:deep(.el-table th.el-table__cell) {
  background: #f8fbfd;
  color: #0f2a3d;
}

:deep(.el-table .cell) {
  padding-left: 10px;
  padding-right: 10px;
}

@media (max-width: 960px) {
  .entry-grid,
  .summary-grid {
    grid-template-columns: 1fr 1fr;
  }

  .table-head,
  .table-actions {
    align-items: stretch;
    flex-direction: column;
  }
}

@media (max-width: 768px) {
  .entry-grid,
  .summary-grid {
    grid-template-columns: 1fr;
  }

  .table-shell {
    padding: 18px;
  }

  .filter-group {
    width: 100%;
    justify-content: space-between;
  }

  .filter-chip {
    flex: 1;
  }

  .task-pagination {
    overflow-x: auto;
  }
}
</style>
```

- [ ] **Step 2: Run the targeted test and the production build**

Run:

```bash
cd frontend && npm test -- src/views/OptimizationTaskList.spec.ts
cd frontend && npm run build
```

Expected:
- `npm test -- src/views/OptimizationTaskList.spec.ts` PASS
- `npm run build` PASS
- 如果仍出现 chunk size 或 dynamic import 警告，只记录为现有项目告警，不作为本次单页 UI 改造阻塞项

- [ ] **Step 3: Commit the finished visual refresh**

Run:

```bash
git add frontend/src/views/OptimizationTaskList.vue frontend/src/views/OptimizationTaskList.spec.ts
git commit -m "style: polish optimization task list page"
```
