# Design: project-token-login-parsing

## 方案概览

1. **接口封装**：`url.ts` 增加 `PARSE_TOKEN_LOGIN` 常量，`api.ts` 增加 `parseTokenLogin` POST 封装。
2. **统一解析函数**：`projectAddEditForm.vue` 新增 `handleTokenChange(platform)`，三平台令牌输入框 `@change` 统一接入，解析成功后回显用户名。
3. **表单展示调整**：三个「公共账号用户名」表单项移除 `v-if="type === 'edit'"`，新增项目时也展示。
4. **附带修正**：`toolItem.vue` 图标上传接口两处补传 `projectId`。

## 实现逻辑

### 1. 接口定义

```ts
// url.ts
export const PARSE_TOKEN_LOGIN = FRAME_WORK + "/project/parse-token-login";

// api.ts
export const parseTokenLogin: RequestFunc = (a, s) =>
  apiClient.post(urls.PARSE_TOKEN_LOGIN, a, s);
```

请求 data：`{ token, platform }`；platform 取值 `gitee / gitcode / github`。

### 2. 统一解析函数（三平台共用）

```js
const handleTokenChange = (platform) => {
  const token = formData.value[`${platform}Token`];
  if (!token) return;
  parseTokenLogin({
    data: {
      token,
      platform,
    },
  }).then((res) => {
    if (res.code === 200) {
      formData.value[`${platform}Login`] = res.data?.login ?? res.data ?? "";
    }
  });
};
```

要点：

- **字段映射**：三平台表单字段命名规整——`{platform}Token`（giteeToken / gitcodeToken / githubToken）、`{platform}Login`（giteeLogin / gitcodeLogin / githubLogin），模板字符串直接索引，零分支。
- **空值直通**：令牌清空时直接返回，不发起解析。
- **返回结构兼容**：`res.data?.login ?? res.data ?? ''` 兼容 `data` 为对象（取 `.login`）与直接为字符串两种后端返回结构，联调确认后可简化。
- **静默失败**：非 200 时用户名保持原状，不额外弹错。

### 3. 场景接入与展示调整

```html
<!-- 三平台令牌输入框 -->
<el-input
  v-model="formData.giteeToken"
  show-password
  @change="() => handleTokenChange('gitee')"
/>

<!-- 用户名表单项移除编辑态限制（新增项目也展示） -->
<el-form-item label="Gitee公共账号用户名" prop="giteeLogin">
  <el-input v-model="formData.giteeLogin" disabled />
</el-form-item>
```

### 4. 附带修正（toolItem.vue）

工具图标上传接口两处补传 `projectId`：

- el-upload `:action` URL query：`&projectId=${app.projectInfo?.projectId}`
- 分片上传 `params`：`projectId: app.projectInfo?.projectId`

## 类与组件

| 文件                                                | 角色              | 变更                                                                                     |
| --------------------------------------------------- | ----------------- | ---------------------------------------------------------------------------------------- |
| `apps/web-openlibing/src/api/url.ts`                | 接口地址常量      | 新增 `PARSE_TOKEN_LOGIN`                                                                 |
| `apps/web-openlibing/src/api/api.ts`                | 接口封装          | 新增 `parseTokenLogin`                                                                   |
| `.../Project/projectAddEditForm.vue`                | 新增/修改项目表单 | 三平台令牌 `@change` 接入 `handleTokenChange`；用户名表单项移除 `v-if="type === 'edit'"` |
| `.../ToolManagement/MyTool/components/toolItem.vue` | 我的工具表单      | 图标上传接口两处补传 `projectId`（用户改动随本需求打包提交）                             |

## 数据模型

| 字段              | 来源/去向        | 说明                     |
| ----------------- | ---------------- | ------------------------ |
| `{platform}Token` | 表单 → 解析接口  | 令牌明文，仅传输         |
| `platform`        | 表单（固定枚举） | gitee / gitcode / github |
| `{platform}Login` | 解析接口 → 表单  | 回显公共账号用户名       |

## 安全

- 解析接口经网关既有鉴权链路，无新增权限暴露。
- 用户名输入框 disabled，仅作解析结果展示，防止手误篡改。
- 令牌明文仅在 change 时刻提交解析接口，不新增本地缓存。

## 影响范围

- 新增/修改项目表单：三平台令牌输入增加实时解析联动，用户名表单项新增态可见（交互变化）。
- 我的工具：图标上传补传 `projectId`，修正多项目图标归属。
- 不影响后端接口契约以外部分。

## 回滚策略

revert 业务 commit `06b5a6cb3` 即可整体回退（接口封装为增量新增，表单联动恢复原手动填写模式）。

Generated-by: GLM-5.3
