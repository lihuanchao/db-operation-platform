# Optimization Task Create Pages UI Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 统一“创建 SQL 优化任务”和“创建 ORM XML 优化任务”两个页面为同一单卡片工作区，并去除介绍性文案，同时保持现有校验、提交和跳转行为不变。

**Architecture:** 不改 API、store 和路由，只在两个页面组件层做结构与样式收敛。新增一个页面级测试文件覆盖两个页面的返回、校验阻断和成功提交跳转，确保“去介绍化 + 结构统一”改造不引入行为回归。两页保持同构布局，只在标题、文本域 label、placeholder 和提交方法上保留业务差异。

**Tech Stack:** Vue 3 `<script setup>`, TypeScript, Vue Router, Element Plus, Vitest, Vue Test Utils

---

## File Structure

- Create: `frontend/src/views/OptimizationTaskCreatePages.spec.ts`
  责任：覆盖 SQL 与 MyBatis 创建页的关键行为（返回、校验、提交跳转）与文案收敛断言。
- Modify: `frontend/src/views/OptimizationTaskCreateSql.vue`
  责任：移除顶部介绍文案，统一到单卡片工作区样式，保留原提交流程与规则。
- Modify: `frontend/src/views/OptimizationTaskCreateMyBatis.vue`
  责任：与 SQL 页使用同一布局与样式体系，仅保留业务必要差异。

## Task 1: Add Failing View Tests For Both Create Pages

**Files:**
- Create: `frontend/src/views/OptimizationTaskCreatePages.spec.ts`
- Modify: `frontend/src/views/OptimizationTaskCreateSql.vue`
- Modify: `frontend/src/views/OptimizationTaskCreateMyBatis.vue`
- Test: `frontend/src/views/OptimizationTaskCreatePages.spec.ts`

- [ ] **Step 1: Write the failing page-level test file**

`frontend/src/views/OptimizationTaskCreatePages.spec.ts`

```ts
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'

const pushMock = vi.fn()
const createSqlTaskMock = vi.fn()
const createMyBatisTaskMock = vi.fn()
const fetchAuthorizedConnectionsMock = vi.fn()

const authStoreState = {
  authorizedConnections: [
    {
      id: 1,
      connection_name: '订单库',
      host: '10.0.0.11',
      port: 3306
    }
  ]
}

vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: pushMock
  })
}))

vi.mock('@/stores/optimizationTask', () => ({
  useOptimizationTaskStore: () => ({
    submitLoading: false,
    createSqlTask: createSqlTaskMock,
    createMyBatisTask: createMyBatisTaskMock
  })
}))

vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({
    authorizedConnections: authStoreState.authorizedConnections,
    fetchAuthorizedConnections: fetchAuthorizedConnectionsMock
  })
}))

import OptimizationTaskCreateSql from './OptimizationTaskCreateSql.vue'
import OptimizationTaskCreateMyBatis from './OptimizationTaskCreateMyBatis.vue'

describe('OptimizationTaskCreate pages', () => {
  function mountSqlPage() {
    return mount(OptimizationTaskCreateSql, {
      global: {
        plugins: [ElementPlus],
        stubs: {
          AppLayout: {
            template: '<div class="layout-stub"><slot /></div>'
          }
        }
      }
    })
  }

  function mountMyBatisPage() {
    return mount(OptimizationTaskCreateMyBatis, {
      global: {
        plugins: [ElementPlus],
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
    authStoreState.authorizedConnections = [
      {
        id: 1,
        connection_name: '订单库',
        host: '10.0.0.11',
        port: 3306
      }
    ]
    createSqlTaskMock.mockResolvedValue({ id: 301 })
    createMyBatisTaskMock.mockResolvedValue({ id: 401 })
  })

  it('sql page removes intro copy and supports back + submit flow', async () => {
    const wrapper = mountSqlPage()
    await flushPromises()

    expect(wrapper.text()).not.toContain('系统将自动获取执行计划和建表语句并异步优化')

    await wrapper.find('button.back-btn').trigger('click')
    expect(pushMock).toHaveBeenCalledWith('/optimization-tasks')

    await wrapper.find('button.submit-btn').trigger('click')
    await flushPromises()
    expect(createSqlTaskMock).not.toHaveBeenCalled()

    const select = wrapper.findComponent({ name: 'ElSelect' })
    select.vm.$emit('update:modelValue', 1)
    await wrapper.find('input').setValue('orders')
    await wrapper.find('textarea').setValue('SELECT id FROM orders LIMIT 10')

    await wrapper.find('button.submit-btn').trigger('click')
    await flushPromises()

    expect(createSqlTaskMock).toHaveBeenCalledWith({
      db_connection_id: 1,
      database_name: 'orders',
      sql_text: 'SELECT id FROM orders LIMIT 10'
    })
    expect(pushMock).toHaveBeenLastCalledWith('/optimization-tasks/301')
  })

  it('mybatis page removes intro copy and supports back + submit flow', async () => {
    const wrapper = mountMyBatisPage()
    await flushPromises()

    expect(wrapper.text()).not.toContain('系统会自动提取查询并进行索引与写法优化')

    await wrapper.find('button.back-btn').trigger('click')
    expect(pushMock).toHaveBeenCalledWith('/optimization-tasks')

    await wrapper.find('button.submit-btn').trigger('click')
    await flushPromises()
    expect(createMyBatisTaskMock).not.toHaveBeenCalled()

    const select = wrapper.findComponent({ name: 'ElSelect' })
    select.vm.$emit('update:modelValue', 1)
    await wrapper.find('input').setValue('orders')
    await wrapper.find('textarea').setValue('<select id=\"findOrders\">SELECT * FROM orders</select>')

    await wrapper.find('button.submit-btn').trigger('click')
    await flushPromises()

    expect(createMyBatisTaskMock).toHaveBeenCalledWith({
      db_connection_id: 1,
      database_name: 'orders',
      xml_text: '<select id=\"findOrders\">SELECT * FROM orders</select>'
    })
    expect(pushMock).toHaveBeenLastCalledWith('/optimization-tasks/401')
  })
})
```

- [ ] **Step 2: Run the new test to verify RED**

Run:

```bash
cd frontend && npm test -- src/views/OptimizationTaskCreatePages.spec.ts
```

Expected: FAIL（当前页面仍含介绍文案，且还没有 `.back-btn`、`.submit-btn` 这些稳定选择器）。

## Task 2: Refactor Both Pages To A Unified Single-Card Workspace

**Files:**
- Modify: `frontend/src/views/OptimizationTaskCreateSql.vue`
- Modify: `frontend/src/views/OptimizationTaskCreateMyBatis.vue`
- Test: `frontend/src/views/OptimizationTaskCreatePages.spec.ts`

- [ ] **Step 1: Update SQL create page structure and style**

`frontend/src/views/OptimizationTaskCreateSql.vue`

将文件替换为以下内容：

```vue
<template>
  <AppLayout>
    <div class="page-header">
      <h2>创建 SQL 优化任务</h2>
      <el-button class="ghost-btn back-btn" @click="goBack">返回列表</el-button>
    </div>

    <el-card shadow="never" class="form-shell">
      <template #header>
        <div class="card-title">任务配置</div>
      </template>

      <el-form
        ref="formRef"
        :model="formData"
        :rules="rules"
        label-width="96px"
        label-position="top"
      >
        <el-row :gutter="16">
          <el-col :xs="24" :sm="24" :md="12">
            <el-form-item label="数据库连接" prop="db_connection_id">
              <el-select
                v-model="formData.db_connection_id"
                placeholder="请选择数据库连接"
                filterable
                style="width: 100%"
              >
                <el-option
                  v-for="conn in authStore.authorizedConnections"
                  :key="conn.id"
                  :label="`${conn.connection_name} (${conn.host}:${conn.port})`"
                  :value="conn.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="24" :md="12">
            <el-form-item label="数据库名" prop="database_name">
              <el-input v-model="formData.database_name" placeholder="请输入数据库名" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="SQL 内容" prop="sql_text" class="content-area-item">
          <el-input
            v-model="formData.sql_text"
            type="textarea"
            :rows="15"
            resize="none"
            placeholder="请输入待优化 SQL"
          />
          <div class="text-counter">{{ formData.sql_text.length }} 字符</div>
        </el-form-item>

        <div class="action-row">
          <el-button class="ghost-btn" @click="goBack">取消</el-button>
          <el-button class="submit-btn" type="primary" :loading="store.submitLoading" @click="handleSubmit">
            开始优化
          </el-button>
        </div>
      </el-form>
    </el-card>
  </AppLayout>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance } from 'element-plus'
import AppLayout from '@/components/Layout/AppLayout.vue'
import { useOptimizationTaskStore } from '@/stores/optimizationTask'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const store = useOptimizationTaskStore()
const authStore = useAuthStore()
const formRef = ref<FormInstance>()

const formData = ref({
  db_connection_id: undefined as number | undefined,
  database_name: '',
  sql_text: ''
})

const rules = {
  db_connection_id: [{ required: true, message: '请选择数据库连接', trigger: 'change' }],
  database_name: [{ required: true, message: '请输入数据库名', trigger: 'blur' }],
  sql_text: [{ required: true, message: '请输入SQL内容', trigger: 'blur' }]
}

onMounted(async () => {
  if (!authStore.authorizedConnections.length) {
    await authStore.fetchAuthorizedConnections()
  }
})

function goBack() {
  router.push('/optimization-tasks')
}

async function handleSubmit() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  const task = await store.createSqlTask({
    db_connection_id: formData.value.db_connection_id as number,
    database_name: formData.value.database_name,
    sql_text: formData.value.sql_text
  })

  if (task?.id) {
    router.push(`/optimization-tasks/${task.id}`)
  } else {
    ElMessage.error('创建任务失败')
  }
}
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 18px;
}

.page-header h2 {
  margin: 0;
  color: #0f2a3d;
  font-size: 26px;
  font-weight: 700;
}

.form-shell {
  border: 1px solid #d9e6f2;
  border-radius: 20px;
  background: #ffffff;
  box-shadow: 0 18px 40px rgba(15, 42, 61, 0.06);
}

.card-title {
  font-size: 16px;
  font-weight: 700;
  color: #0f2a3d;
}

.content-area-item :deep(.el-textarea__inner) {
  font-family: 'Consolas', 'Monaco', 'SFMono-Regular', monospace;
  line-height: 1.6;
  border-radius: 12px;
}

.text-counter {
  margin-top: 8px;
  text-align: right;
  font-size: 12px;
  color: #74869a;
}

.action-row {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 14px;
}

.ghost-btn {
  border-color: #d7e3ef;
  color: #33546b;
}

@media (max-width: 768px) {
  .page-header {
    align-items: stretch;
    flex-direction: column;
    gap: 10px;
  }

  .back-btn {
    width: 100%;
  }

  .action-row {
    flex-direction: column;
  }

  .action-row .el-button {
    width: 100%;
  }
}
</style>
```

- [ ] **Step 2: Update MyBatis create page with the same structure and style system**

`frontend/src/views/OptimizationTaskCreateMyBatis.vue`

将文件替换为以下内容：

```vue
<template>
  <AppLayout>
    <div class="page-header">
      <h2>创建 ORM XML 优化任务</h2>
      <el-button class="ghost-btn back-btn" @click="goBack">返回列表</el-button>
    </div>

    <el-card shadow="never" class="form-shell">
      <template #header>
        <div class="card-title">任务配置</div>
      </template>

      <el-form
        ref="formRef"
        :model="formData"
        :rules="rules"
        label-width="96px"
        label-position="top"
      >
        <el-row :gutter="16">
          <el-col :xs="24" :sm="24" :md="12">
            <el-form-item label="数据库连接" prop="db_connection_id">
              <el-select
                v-model="formData.db_connection_id"
                placeholder="请选择数据库连接"
                filterable
                style="width: 100%"
              >
                <el-option
                  v-for="conn in authStore.authorizedConnections"
                  :key="conn.id"
                  :label="`${conn.connection_name} (${conn.host}:${conn.port})`"
                  :value="conn.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="24" :md="12">
            <el-form-item label="数据库名" prop="database_name">
              <el-input v-model="formData.database_name" placeholder="请输入数据库名" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="MyBatis XML 内容" prop="xml_text" class="content-area-item">
          <el-input
            v-model="formData.xml_text"
            type="textarea"
            :rows="15"
            resize="none"
            placeholder="请输入 MyBatis XML"
          />
          <div class="text-counter">{{ formData.xml_text.length }} 字符</div>
        </el-form-item>

        <div class="action-row">
          <el-button class="ghost-btn" @click="goBack">取消</el-button>
          <el-button class="submit-btn" type="primary" :loading="store.submitLoading" @click="handleSubmit">
            开始优化
          </el-button>
        </div>
      </el-form>
    </el-card>
  </AppLayout>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance } from 'element-plus'
import AppLayout from '@/components/Layout/AppLayout.vue'
import { useOptimizationTaskStore } from '@/stores/optimizationTask'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const store = useOptimizationTaskStore()
const authStore = useAuthStore()
const formRef = ref<FormInstance>()

const formData = ref({
  db_connection_id: undefined as number | undefined,
  database_name: '',
  xml_text: ''
})

const rules = {
  db_connection_id: [{ required: true, message: '请选择数据库连接', trigger: 'change' }],
  database_name: [{ required: true, message: '请输入数据库名', trigger: 'blur' }],
  xml_text: [{ required: true, message: '请输入XML内容', trigger: 'blur' }]
}

onMounted(async () => {
  if (!authStore.authorizedConnections.length) {
    await authStore.fetchAuthorizedConnections()
  }
})

function goBack() {
  router.push('/optimization-tasks')
}

async function handleSubmit() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  const task = await store.createMyBatisTask({
    db_connection_id: formData.value.db_connection_id as number,
    database_name: formData.value.database_name,
    xml_text: formData.value.xml_text
  })

  if (task?.id) {
    router.push(`/optimization-tasks/${task.id}`)
  } else {
    ElMessage.error('创建任务失败')
  }
}
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 18px;
}

.page-header h2 {
  margin: 0;
  color: #0f2a3d;
  font-size: 26px;
  font-weight: 700;
}

.form-shell {
  border: 1px solid #d9e6f2;
  border-radius: 20px;
  background: #ffffff;
  box-shadow: 0 18px 40px rgba(15, 42, 61, 0.06);
}

.card-title {
  font-size: 16px;
  font-weight: 700;
  color: #0f2a3d;
}

.content-area-item :deep(.el-textarea__inner) {
  font-family: 'Consolas', 'Monaco', 'SFMono-Regular', monospace;
  line-height: 1.6;
  border-radius: 12px;
}

.text-counter {
  margin-top: 8px;
  text-align: right;
  font-size: 12px;
  color: #74869a;
}

.action-row {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 14px;
}

.ghost-btn {
  border-color: #d7e3ef;
  color: #33546b;
}

@media (max-width: 768px) {
  .page-header {
    align-items: stretch;
    flex-direction: column;
    gap: 10px;
  }

  .back-btn {
    width: 100%;
  }

  .action-row {
    flex-direction: column;
  }

  .action-row .el-button {
    width: 100%;
  }
}
</style>
```

- [ ] **Step 3: Run the new view test and confirm GREEN**

Run:

```bash
cd frontend && npm test -- src/views/OptimizationTaskCreatePages.spec.ts
```

Expected: PASS（2 个用例通过，说明两页的返回、校验阻断与成功提交跳转行为保持正确，同时介绍文案已移除）。

- [ ] **Step 4: Run full frontend verification**

Run:

```bash
cd frontend && npm test
cd frontend && npm run build
```

Expected:
- `npm test` PASS
- `npm run build` PASS
- 若仍出现 chunk size / dynamic import 警告，记录为项目现有告警，不阻塞本次页面重构

- [ ] **Step 5: Commit the create-pages refresh**

Run:

```bash
git add frontend/src/views/OptimizationTaskCreateSql.vue frontend/src/views/OptimizationTaskCreateMyBatis.vue frontend/src/views/OptimizationTaskCreatePages.spec.ts
git commit -m "style: unify optimization task create pages workspace"
```
