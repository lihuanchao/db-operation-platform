# Archive Task Create Drawer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将“归档任务管理”的新增任务入口从弹窗改为右侧抽屉，并按确认方案落地“核心信息 + 高级配置（默认展开）+ 保存并执行”。

**Architecture:** 在现有 `ArchiveTaskWithCron.vue` 内替换任务表单容器（`el-dialog` -> `el-drawer`），保持 store/API 不变。新增任务提交走“两段式动作”：先创建任务，再立即调用 `executeTask`。编辑任务继续只执行更新逻辑，不触发执行。通过视图测试覆盖新增抽屉结构和“保存并执行”关键行为。

**Tech Stack:** Vue 3 (`<script setup lang="ts">`), Element Plus, Pinia, Vitest + Vue Test Utils

---

### Task 1: Add Failing Tests For Drawer + Save-And-Execute

**Files:**
- Modify: `frontend/src/views/ArchiveTaskWithCron.spec.ts`
- Test: `frontend/src/views/ArchiveTaskWithCron.spec.ts`

- [ ] **Step 1: Write failing test for drawer mode and action button text**

Add this test block after existing tests:

```ts
it('opens create drawer with core and advanced sections visible', async () => {
  const { wrapper } = mountView()
  await flushPromises()

  const addButton = wrapper.findAll('button').find((btn) => btn.text().includes('新增归档任务'))
  expect(addButton).toBeDefined()
  await addButton!.trigger('click')
  await flushPromises()

  expect(wrapper.text()).toContain('新增归档任务')
  expect(wrapper.text()).toContain('核心信息')
  expect(wrapper.text()).toContain('高级配置')
  expect(wrapper.text()).toContain('保存并执行')
})
```

- [ ] **Step 2: Write failing test for create path (add then execute)**

Add this test block:

```ts
it('creates task then executes immediately when submitting create drawer', async () => {
  const { wrapper, archiveStore } = mountView()
  await flushPromises()

  const addSpy = vi.spyOn(archiveStore, 'addTask').mockResolvedValue(buildArchiveTask({ id: 301 }))
  const executeSpy = vi.spyOn(archiveStore, 'executeTask').mockResolvedValue({
    log_id: 9,
    message: '任务已加入后台执行'
  } as any)
  const vm = wrapper.vm as any

  vm.formRef = {
    validate: vi.fn().mockResolvedValue(undefined)
  }
  vm.handleAddTask()
  vm.formData.task_name = '新归档任务'
  vm.formData.source_connection_id = 11
  vm.formData.source_database = 'sales'
  vm.formData.source_table = 'orders'
  vm.formData.where_condition = 'created_at < NOW()'

  await vm.handleFormSubmit()
  await flushPromises()

  expect(addSpy).toHaveBeenCalledTimes(1)
  expect(executeSpy).toHaveBeenCalledWith(301)
  expect(vm.formDialogVisible).toBe(false)
})
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd frontend && npm run test -- src/views/ArchiveTaskWithCron.spec.ts`

Expected: at least one new case fails because:
1) page still uses `el-dialog` title/structure
2) button text is still `确定`
3) create flow does not call `executeTask`

- [ ] **Step 4: Commit failing test**

```bash
git add frontend/src/views/ArchiveTaskWithCron.spec.ts
git commit -m "test: cover archive create drawer and save-execute flow"
```

### Task 2: Implement Drawer UI + Save-And-Execute Behavior

**Files:**
- Modify: `frontend/src/views/ArchiveTaskWithCron.vue`
- Test: `frontend/src/views/ArchiveTaskWithCron.spec.ts`

- [ ] **Step 1: Replace create form container with right drawer**

Replace task form container from `el-dialog` to `el-drawer` and keep the same `v-model` state:

```vue
<el-drawer
  v-model="formDialogVisible"
  :title="editingTask ? '编辑归档任务' : '新增归档任务'"
  direction="rtl"
  size="560px"
  destroy-on-close
  class="archive-task-drawer"
>
  <div class="archive-drawer-body">
    <!-- form here -->
  </div>
  <template #footer>
    <div class="drawer-footer">
      <el-button @click="formDialogVisible = false">取消</el-button>
      <el-button type="primary" @click="handleFormSubmit" :loading="store.formLoading">
        保存并执行
      </el-button>
    </div>
  </template>
</el-drawer>
```

- [ ] **Step 2: Restructure form into core + advanced sections (advanced expanded)**

Update the form body to render two titled blocks:

```vue
<el-form :model="formData" :rules="formRules" label-width="96px" ref="formRef" class="archive-task-form">
  <section class="drawer-section" data-testid="archive-core-section">
    <h3 class="drawer-section-title">核心信息</h3>
    <!-- task_name, source_connection_id, source_database, source_table, where_condition -->
  </section>

  <section class="drawer-section" data-testid="archive-advanced-section">
    <h3 class="drawer-section-title">高级配置</h3>
    <!-- dest_connection_id, dest_database, dest_table, is_enabled -->
  </section>
</el-form>
```

Keep all existing field bindings and validation props unchanged.

- [ ] **Step 3: Implement create-submit behavior as create then execute**

Update `handleFormSubmit` create branch:

```ts
async function handleFormSubmit() {
  await formRef.value?.validate()
  try {
    let savedTask: ArchiveTask | null = null
    if (editingTask.value?.id) {
      savedTask = await store.editTask(editingTask.value.id, formData.value) ?? null
    } else {
      savedTask = await store.addTask(formData.value) ?? null
      if (savedTask?.id) {
        await store.executeTask(savedTask.id)
      }
    }

    if (savedTask && locatedTask.value?.id === savedTask.id) {
      locatedTask.value = { ...savedTask }
      if (currentTask.value?.id === savedTask.id) {
        currentTask.value = { ...savedTask }
      }
    }
    formDialogVisible.value = false
  } catch (error) {
    console.error('提交失败:', error)
  }
}
```

- [ ] **Step 4: Add drawer styles for enterprise compact layout**

Add/replace styles:

```css
.archive-task-drawer :deep(.el-drawer__header) {
  margin-bottom: 0;
  padding: 16px 18px;
  border-bottom: 1px solid #e2e8f0;
}

.archive-drawer-body {
  padding: 14px 18px 6px;
  overflow-y: auto;
}

.drawer-section {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 12px;
  background: #ffffff;
}

.drawer-section + .drawer-section {
  margin-top: 12px;
}

.drawer-section-title {
  margin: 0 0 10px;
  color: #1e293b;
  font-size: 13px;
  font-weight: 600;
}

.drawer-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 10px 18px 14px;
  border-top: 1px solid #e2e8f0;
}
```

- [ ] **Step 5: Run targeted tests to verify green**

Run: `cd frontend && npm run test -- src/views/ArchiveTaskWithCron.spec.ts`

Expected:
1) new drawer and save-execute cases pass
2) existing route-context regression tests remain green

- [ ] **Step 6: Commit implementation**

```bash
git add frontend/src/views/ArchiveTaskWithCron.vue frontend/src/views/ArchiveTaskWithCron.spec.ts
git commit -m "feat: switch archive task create form to right drawer with save-and-execute"
```

### Task 3: Validate No Regressions In Related Screens

**Files:**
- Modify: none (verification-only unless failures require fixes)
- Test: `frontend/src/views/ArchiveTaskWithCron.spec.ts`
- Test: `frontend/src/views/ExecutionLogList.spec.ts`
- Test: `frontend/src/views/FlashbackTaskList.spec.ts`

- [ ] **Step 1: Run focused regression suite**

Run:

```bash
cd frontend
npm run test -- \
  src/views/ArchiveTaskWithCron.spec.ts \
  src/views/ExecutionLogList.spec.ts \
  src/views/FlashbackTaskList.spec.ts
```

Expected: all listed spec files pass.

- [ ] **Step 2: Run build to catch type/template regressions**

Run: `cd frontend && npm run build`

Expected:
1) no new error from `ArchiveTaskWithCron.vue` or its spec
2) if build still fails on existing unrelated baseline error, record it explicitly

- [ ] **Step 3: Commit verification notes if code changed during fixup**

If no additional code change: skip commit.

If regression fix was required:

```bash
git add <exact-fixed-files>
git commit -m "fix: address archive drawer regression after verification"
```

## Spec Coverage Self-Review

1. **右侧抽屉替代弹窗**：Task 2 Step 1 完整覆盖。
2. **核心区 + 高级配置分区**：Task 2 Step 2 覆盖。
3. **高级配置默认展开**：Task 2 Step 2 直接以常驻 section 落地，无折叠逻辑。
4. **主操作“保存并执行”**：Task 2 Step 1 + Step 3 覆盖（按钮文案 + 创建后执行）。
5. **企业级简洁高效视觉**：Task 2 Step 4 覆盖。
6. **可验证性与回归**：Task 1/2/3 的测试与构建命令覆盖。

## Placeholder Scan

1. 无 `TODO/TBD/implement later`。
2. 每个代码步骤均给出可落地代码块。
3. 每个验证步骤均给出明确命令与预期结果。

## Type Consistency Check

1. 统一使用 `formDialogVisible` 作为抽屉开关状态，不引入新状态名。
2. 新增流程使用 `store.addTask` 返回 `savedTask`，执行调用 `store.executeTask(savedTask.id)`，与 store 现有签名一致。
3. 编辑流程保持 `store.editTask(id, formData)` 不变，避免行为漂移。
