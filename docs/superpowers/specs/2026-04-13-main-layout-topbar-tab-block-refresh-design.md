# Main Layout Topbar Tab Block Refresh Design

## Goal

将主布局顶部任务栏导航中的标签改为彼此分离的独立方块，并统一为更紧凑的工业控制台风格。选中态使用浅灰底，同时保留顶部红色标识，提升层次和辨识度。

## Current Context

- 当前顶部任务栏位于 [AppLayout.vue](/data/claude-project/frontend/src/components/Layout/AppLayout.vue)。
- 标签当前已经是较硬朗的工业风方向，但仍然是连续拼接感较强的条状标签。
- 用户已经在浏览器视觉预览中确认使用 `A. 紧凑方块` 方案。

## Visual Direction

### Overall Style

- 保持现有后台工作台风格，不引入花哨阴影和高饱和大面积色块。
- 顶部任务栏标签调整为独立方块，每个方块之间留出清晰间距。
- 视觉关键词：`紧凑`、`方正`、`控制台`、`高信息密度`。

### Tab States

- 默认态：
  - 白底
  - 细边框
  - 深灰文字
  - 顶部保留细红条，作为统一状态标识
- 选中态：
  - 浅灰底
  - 边框略深于默认态
  - 保留顶部红色标识
  - 文本颜色保持深灰，不改为深色实底
- 悬停态：
  - 仅做轻微底色和边框变化
  - 不引入漂浮感或明显阴影

### Density And Geometry

- 标签维持紧凑尺寸，优先保证多标签情况下的横向可读性。
- 所有标签使用直角矩形。
- 方块间距需要明确可见，避免重新回到“连片”观感。
- 关闭按钮留在方块右侧，但整体与标签同风格，尺寸克制、边角为直角。

## Interaction

- 点击标签切换页面行为不变。
- 关闭按钮点击行为不变。
- 键盘 `Enter` / `Space` 触发关闭按钮行为保持可用。
- Home 标签继续不可关闭。

## Implementation Scope

### Files In Scope

- Modify: `frontend/src/components/Layout/AppLayout.vue`
- Modify: `frontend/src/components/Layout/AppLayout.spec.ts`

### Expected Changes

- 调整顶部标签容器和标签项样式，形成独立块状结构。
- 调整激活态颜色，从当前深色实底切换为浅灰选中。
- 保留并强调顶部红色标识条。
- 保持现有测试选择器和交互测试不回退。
- 新增一条语义测试，锁定“独立方块工业风”样式类名。

## Testing

- 运行 `npm test -- AppLayout.spec.ts`
- 确认顶部任务栏相关的 14 个测试全部通过。
- 手动检查要点：
  - 标签之间存在明确间距
  - 激活标签为浅灰底
  - 每个标签顶部保留红色标识
  - 关闭按钮视觉不突兀
  - 多标签时仍然保持紧凑可读

## Risks And Constraints

- 如果块间距过大，会压缩顶部可容纳标签数量。
- 如果浅灰选中态对比不足，当前标签可能不够醒目，因此需要依靠边框、字重和顶部红条共同建立层次。
- 不在本次改动中重构布局结构或引入新的组件拆分，保持修改聚焦在样式和少量交互钩子上。
