# Tasks: 合法合规批量分析弹窗审核人空状态提示

## 实现清单

### 1. 状态字段与请求容错（confirmBox.vue）

- [ ] `data` 新增 `committerLoadState`（`'init' | 'success' | 'error'`）
- [ ] `queryBranchCommiter()`：请求前置状态，`.then` 成功置 `success`，新增 `.catch` 置 `error`

### 2. prop 与下拉空状态插槽（confirmBox.vue）

- [ ] 新增 prop `enableCommitterEmptyTip`（Boolean，默认 false，控制空提示仅在合法合规入口生效）
- [ ] 「审核人」`el-select` 增加 `#empty` 插槽（仅 `enableCommitterEmptyTip` 开启时渲染自定义内容，未开启保持默认「无数据」）：
  - `committerLoadState === 'error'` → 「审核人列表获取失败，请稍后重试。」
  - 其余（success 且列表为空）→ 详细引导文案（sig-info.yaml committer 配置 / 平台代码合并者两个来源 + 账号前置条件）
- [ ] 空文案多行排版样式（次要灰，单行不超下拉宽度）

### 3. 合法合规入口开启（两个调用方各加一行传参）

- [ ] `PRComponentAnalysis/components/openSourceCompliance/analysisTable.vue`：confirm-box 调用处新增 `:enable-committer-empty-tip="true"`
- [ ] `softInformation/gitUrlList.vue`：confirm-box 调用处新增 `:enable-committer-empty-tip="true"`
- [ ] `personalScandTaskInfor/analysisTable.vue` **不改动**（非合法合规菜单，保持默认行为）

### 4. 验证

- [ ] 数据为空场景：合法合规两个入口（PR 扫描页签、版本扫描页签详情），mock/构造接口返回空列表，下拉空状态展示引导文案
- [ ] 失败场景：合法合规两个入口构造接口异常（断网/拦截），下拉空状态展示失败文案
- [ ] 个人扫描任务详情入口：空列表时仍为默认「无数据」，与改造前一致
- [ ] 正常场景：各入口审核人列表展示与改造前一致；禁用选项 tooltip 不受影响
- [ ] ESLint 通过（改动文件无新增告警）

## 交付记录

- （待填）业务仓分支 / commit
