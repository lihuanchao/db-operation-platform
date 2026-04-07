# Main Layout Topbar + Tabs Navigation Design

## 1. 背景与目标

当前系统布局为“左侧栏 + 右侧内容”的单层结构，缺少固定顶栏、功能标签切换与侧栏收缩能力。  
本次改造目标是对齐参考图风格，提升导航效率与多页面切换体验，同时不改动业务 API 与页面业务逻辑。

### 目标

1. 新增固定顶栏：显示 Logo、系统名称、侧栏收缩按钮、用户名下拉（退出）。
2. 左侧导航支持收缩：收缩后仅保留图标。
3. 右侧内容区新增功能标签栏：支持打开、切换、关闭（首页标签不可关闭）。
4. 关闭当前标签后固定跳转首页 `/optimization-tasks`。
5. 标签状态刷新后保留（`localStorage` 持久化）。
6. 优化左侧导航图标风格，一致化视觉语义。

### 非目标

1. 不改动现有接口、鉴权逻辑、角色权限规则。
2. 不重写为父子嵌套路由架构（保持现有路由结构）。
3. 不调整各业务页面内部字段与提交流程。

## 2. 设计方案概览

采用“在现有 `AppLayout` 上做壳层增强 + 新增 UI 状态 store”的低风险改造：

1. 保留所有现有页面路由与视图组件。
2. 在 `AppLayout` 内形成统一骨架：`TopBar` + `Sidebar` + `TabsBar` + `MainContent`。
3. 新增 `layout` store 管理 UI 状态：
   - 侧栏收缩状态
   - 已打开标签列表
   - 当前激活标签
4. 利用路由变化驱动标签同步（避免手工维护多份状态）。

## 3. 信息架构与交互规则

### 3.1 顶栏（固定）

1. 左侧：Logo（使用用户提供图）+ 系统名称。
2. 侧栏收缩按钮：点击切换展开/收缩状态。
3. 右侧：用户名（`authStore.user.real_name`）点击弹出菜单，仅保留“退出登录”。
4. 顶栏固定在页面顶部，内容区随滚动滚动，顶栏不滚动。

### 3.2 左侧导航

1. 展开态：图标 + 文本。
2. 收缩态：仅图标，悬浮显示 Tooltip 文本。
3. 保持现有菜单可见性逻辑（按权限菜单路径过滤）。
4. 图标升级为语义一致的 Element Plus 图标组合，兼顾分组与叶子节点辨识度。

### 3.3 功能标签栏

1. 菜单点击后在标签栏打开或激活对应标签。
2. 同一路由仅保留一个标签，不重复打开。
3. 点击标签切换到对应路由。
4. 非首页标签支持关闭；首页标签固定不可关闭。
5. 关闭当前激活标签后，固定跳转首页 `/optimization-tasks`。

### 3.4 持久化与恢复

1. 持久化字段：
   - `collapsed`（侧栏收缩）
   - `tabs`（标签列表）
   - `activePath`（当前激活标签 path）
2. 刷新时恢复：
   - 若恢复数据合法，按持久化恢复标签并激活。
   - 若恢复数据非法/缺失，回退为仅首页标签。

## 4. 技术设计

## 4.1 新增状态层（Pinia）

新增 `frontend/src/stores/layout.ts`：

1. `collapsed: boolean`
2. `tabs: Array<{ path: string; title: string; closable: boolean }>`
3. `activePath: string`
4. actions：
   - `toggleCollapsed()`
   - `openTab(path, title, closable = true)`
   - `activateTab(path)`
   - `closeTab(path)`
   - `syncByRoute(path, title)`
   - `hydrateFromStorage()`
   - `persistToStorage()`
   - `resetToHomeTab()`

首页标签常量：
- `path: '/optimization-tasks'`
- `title: 'SQL优化建议'`
- `closable: false`

## 4.2 布局组件改造

### `AppLayout.vue`

1. 增加固定顶栏结构。
2. `el-aside` 宽度根据 `collapsed` 进行 220/64 切换。
3. 右侧主区域顶部插入标签栏，主体保留 `<slot />` 承载业务页面。
4. 监听路由变化，调用 `layoutStore.syncByRoute`。

### `Sidebar.vue`

1. 接收/读取 `collapsed` 状态并传给 `el-menu` 的 `collapse`。
2. 保留权限过滤逻辑与导航行为。
3. 替换菜单图标为统一风格组合（任务、慢 SQL、连接、归档、系统管理等）。
4. 在收缩态为菜单项补充 Tooltip。

## 4.3 资源接入

1. 将用户提供的 Logo 图引入前端静态资源目录（`src/assets`）。
2. 顶栏使用该 Logo，控制高度与间距，保证深色顶栏下对比度。

## 4.4 路由标题映射

在布局层维护 path -> title 映射（与标签显示文案一致）：

1. `/optimization-tasks` -> `SQL优化建议`
2. `/slow-sqls` -> `慢SQL列表`
3. `/connections` -> `连接管理`
4. `/archive-tasks` -> `归档任务`
5. `/execution-logs` -> `执行日志`
6. `/users` -> `用户管理`
7. `/roles` -> `角色管理`
8. `/permissions` -> `权限管理`
9. 其他路径回退到最近上级功能标题（如详情页归属列表页标题）。

## 5. 异常与边界处理

1. 用户直接输入无权限地址：保持现有路由守卫处理，不新增分支。
2. 持久化数据损坏：忽略并重置为首页标签。
3. 当前标签对应路由失效：自动回首页。
4. 退出登录时清理布局状态（避免下一个登录用户继承标签）。

## 6. 测试策略

新增/更新布局层测试，覆盖核心行为：

1. 顶栏渲染用户信息与退出操作触发。
2. 点击收缩按钮后侧栏宽度与菜单显示模式变化。
3. 菜单点击会新增/激活标签且不重复创建。
4. 标签点击可切换路由。
5. 关闭非首页标签后跳首页。
6. 首页标签不可关闭。
7. 刷新恢复（模拟 `localStorage`）后标签与激活项正确。

回归：

1. `npm test`
2. `npm run build`

## 7. 实施范围与交付

主要改动文件（计划）：

1. `frontend/src/components/Layout/AppLayout.vue`
2. `frontend/src/components/Layout/Sidebar.vue`
3. `frontend/src/stores/layout.ts`（新增）
4. `frontend/src/stores/index.ts`（若需导出）
5. `frontend/src/assets/*`（Logo 资源）
6. `frontend/src/components/Layout/*.spec.ts`（新增或更新）

交付标准：

1. 三项用户诉求全部实现（固定顶栏、标签切换/关闭、图标优化）。
2. 首页标签不可关闭。
3. 关闭当前标签固定回首页。
4. 刷新保留标签状态。
5. 测试与构建通过。
