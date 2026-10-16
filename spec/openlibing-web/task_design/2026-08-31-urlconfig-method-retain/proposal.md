# 需求背景

## 业务场景

菜单管理 → 菜单 tab → 新增/修改弹窗中的 URL 配置组件（UrlConfig.vue）包含"请求方式"和"URL 地址"两个下拉项。URL 地址支持远程模糊搜索（allow-create 可输入自定义值），请求方式为 GET/POST 固定选项。

## 问题痛点

1. **手动切换请求方式不同步**：请求方式 select 仅通过 `v-model` 绑定 `data.requestMethod`，未触发 `change` 事件向父组件同步，导致用户手动切换请求方式后父组件保存的数据仍是旧值
2. **URL 选择强制重置请求方式**：`getUrlResult` 中 URL 在下拉选项命中时回填接口的 `httpMethod`（合理），但未命中（自定义输入）或清空时强制将 `requestMethod` 重置为 `'GET'`，覆盖用户已选的值

## 需求目标

1. 请求方式 select 增加 `change` 事件，手动切换时向父组件同步完整配置数据
2. URL 未命中下拉选项（自定义输入）或清空时，保留用户已选请求方式，仅无值时兜底 `GET`

## 验收标准

### 功能验收

1. **手动切换请求方式**
   - 用户切换 GET/POST 后，`change` 事件向父组件 emit 更新后的完整配置（含 requestMethod、menuUrl、flag）
   - 提交保存的数据使用切换后的请求方式

2. **URL 匹配回填**
   - URL 在下拉选项命中：请求方式按接口返回 `httpMethod` 回填（保持原逻辑）
   - URL 未命中（allow-create 自定义输入）：保留当前已选请求方式
   - URL 清空：保留当前已选请求方式，`menuUrl` 置空
   - 以上场景请求方式无值时兜底 `GET`

### 非功能验收

1. 不影响 URL 远程搜索、懒加载、下线接口标红等既有功能
2. 代码变更符合项目编码规范

## 关联Issue

[openlibing/openlibing-framework#83](https://gitcode.com/openlibing/openlibing-framework/issues/83)

## 期望交付时间

2026-08-31
