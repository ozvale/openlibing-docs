# 2026-06 代码检查页面告警代码片段与实际代码不一致 技术设计

## 1. 技术方案

### 1.1 问题分析

代码检查页面告警详情中的代码片段使用 `<pre>` 标签展示，但外层 CSS 样式未设置 `white-space` 属性，导致浏览器按默认的 `white-space: normal` 规则将多个连续空格合并为单个空格。

#### 根因

```css
/* 问题：缺少 white-space 属性 */
.code-line {
  padding: 0px;
  padding-left: 20px;
  color: #333;
  /* 浏览器默认 white-space: normal，合并连续空格 */
}
```

### 1.2 修复方案

添加 `white-space: pre-wrap` 样式：

- `pre`: 保留空白字符序列
- `wrap`: 允许自动换行，避免长行溢出

```css
.code-line {
  padding: 0px;
  padding-left: 20px;
  color: #333;
  white-space: pre-wrap;
}
```

### 1.3 方案对比

| 属性值 | 保留空格 | 自动换行 | 适用性 |
|--------|---------|---------|--------|
| `normal`（默认） | 否 | 是 | 不适用 |
| `pre` | 是 | 否 | 长行会溢出 |
| `pre-wrap` | 是 | 是 | ✅ 适用 |

## 2. 变更详情

| 变更类型 | 文件 | 说明 |
|---------|------|------|
| 样式修复 | `CodeLine.vue` | 添加 `white-space: pre-wrap;` |

## 3. 影响范围

### 功能影响

- 代码片段展示保留原始空格和缩进
- 长行代码自动换行，不影响页面布局
- 不影响 API 接口和其他功能模块

### 副作用

- 无已知副作用，`pre-wrap` 是代码展示场景的标准做法

## 4. 实施步骤

1. 在 `CodeLine.vue` 的 `.code-line` 样式中添加 `white-space: pre-wrap;`
2. 验证告警代码片段展示正确
3. 提交代码并创建 PR
