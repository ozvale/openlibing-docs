# Design: release-artifacts-tag-validation

## 方案概览

在 `releaseArtifacts.vue` 中新增统一的 tag 名称校验函数 `handleTagNameChange`，替换两个 tag 输入场景（选择框 allow-create 与输入框）原直连的 `handleChange`，用一个正则 `TAG_NAME_REG` 完成 GitCode tag 命名规则校验；失败时提示并清空，通过后回落到原有 `handleChange`。

## 实现逻辑

### 1. 校验正则

```js
const TAG_NAME_REG =
  /^(?!.*\/\/)(?!.*\/$)(?!.*\.$)(?!.*\.lock$)[\u4e00-\u9fa5a-zA-Z0-9][\u4e00-\u9fa5a-zA-Z0-9_./-]{0,49}$/;
```

| 正则片段                             | 规则                      |
| ------------------------------------ | ------------------------- |
| `(?!.*\/\/)`                         | `/` 不能连续（禁止 `//`） |
| `(?!.*\/$)`                          | 不能以 `/` 结尾           |
| `(?!.*\.$)`                          | 不能以 `.` 结尾           |
| `(?!.*\.lock$)`                      | 不能以 `.lock` 结尾       |
| `[\u4e00-\u9fa5a-zA-Z0-9]`           | 首字符：中文/字母/数字    |
| `[\u4e00-\u9fa5a-zA-Z0-9_./-]{0,49}` | 字符集 + 总长 ≤ 50        |

### 2. 校验函数（两个输入场景共用）

```js
const handleTagNameChange = () => {
  const tagName = formInfo.value.tagName;
  if (tagName && !TAG_NAME_REG.test(tagName)) {
    formInfo.value.tagName = "";
    ElMessage.error(
      'tag名称只能以中文、字母或数字开头；由中文、字母、数字及_、.、-、/组成；"/"不能连续；最多可包含50个字符，且不能以"/"、"."、".lock"结尾',
    );
  }
  handleChange();
};
```

要点：

- **先清空再提示**：校验失败时在 `handleChange()` 之前清空 `formInfo.value.tagName`，避免非法值经 `handleChange` 同步到父组件/后续流程。
- **空值直通**：`tagName` 为空时不拦截，交由既有必填校验处理。
- **失败也走 `handleChange`**：保持与原直连行为一致，清空后的空值同步触发既有联动逻辑。

### 3. 场景接入

```html
<!-- 选择框 allow-create 场景 -->
<el-select ... @change="handleTagNameChange">
  <!-- 输入框场景 -->
  <el-input ... @change="handleTagNameChange"></el-input
></el-select>
```

## 类与组件

| 文件                                                       | 角色         | 变更                                                                               |
| ---------------------------------------------------------- | ------------ | ---------------------------------------------------------------------------------- |
| `.../publishReview/detail/components/releaseArtifacts.vue` | 制品信息表单 | 新增 `TAG_NAME_REG` + `handleTagNameChange`，两处 `@change` 由 `handleChange` 替换 |

## 数据模型

无新增数据模型；校验对象为既有 `formInfo.value.tagName`。

## 性能

- 单次正则校验（负向前瞻），输入 change 触发，开销可忽略。

## 安全

- 校验失败即清空输入，非法值不会进入后续提交链路。
- 字符白名单（中文/字母/数字/`_./-`）排除路径穿越、命令注入等特殊字符成分。

## 影响范围

- 仅影响发布评审详情页-制品信息的两个 tag 输入场景。
- `handleChange` 既有逻辑不变（校验通过/清空后照常调用）。
- 不影响后端接口、数据模型。

## 回滚策略

revert 业务 commit `c77e233bb` 即可整体回退，恢复两处 `@change="handleChange"` 直连。

Generated-by: GLM-5.3
