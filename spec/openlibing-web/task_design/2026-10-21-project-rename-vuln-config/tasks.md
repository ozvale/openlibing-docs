# Tasks: 项目名称变更与项目漏洞相关配置

## 实现清单

### 1. 表单扩展「对接漏洞视图」（需求①）

- [ ] `projectAddEditForm.vue`：恢复 L53-58 注释块为「对接漏洞视图」radio（是=1/否=0），置于「对接华为云项目」之后
- [ ] `formData.isCve` 默认值 `'0'`（默认选否，无必填符号、无非空校验，与其他 radio 项一致）
- [ ] 确认新增/修改 payload 中 `isCve` 传递正确（payload 已含字段，核对值类型与后端契约）
- [ ] 编辑态：`getProjectDetailInfo` 回填 `isCve`（详情接口已确认返回该字段）

### 2. 项目管理列表新增 3 列（需求②）

- [ ] `Project/index.vue`：项目名称列后新增 isHwProject / isHaveCommonAccount / isCve 三列，1→「是」、0→「否」、空→`--`，min-width 120
- [ ] 值类型归一（已定稿：`formatYesNo` 内 `Number()` 归一，1→「是」、0→「否」、其他→`--`）
- [ ] 树形懒加载子行渲染验证（loadProject 展开路径数据含新字段）

### 3. 项目名称修改（需求③）

- [ ] 新建 `views/Project/projectRenameDialog.vue`：弹窗（项目名称输入框 + 确认/取消），非空/长度(max 50，后端已确认)校验；重复校验由保存接口返回冲突错误，无独立接口
- [ ] `api/url.ts` + `api/api.ts` 新增 `updateProjectName` 接口（已确认：POST `/project/update-project-name`，参数拼接 URL query：projectId: Integer、projectName）
- [ ] `Project/index.vue` 操作列新增「修改名称」图标按钮：NoPermissionPopover + canHandle(`project_manage:rename`) + el-tooltip + v-uem-record，与编辑按钮同构
- [ ] `constants/permissions-meta.ts` 登记 `project_manage:rename` 元数据
- [ ] 保存成功后刷新表格并清空 el-table lazy 树缓存（`lazyTreeNodeMap` 整表重查方案）
- [ ] 无权限账号验证入口不可见；重复名称/超长/空值拦截提示正确

### 4. 漏洞视图「社区配置」二级页签（需求④）

- [ ] `cveAdaptation.vue` typeList 末尾新增 `communityConfig` 二级页签（label 走 i18n `cve.communityConfig`，激活样式复用 .tabItem.active）
- [ ] rightPart 新增 `v-show="activeName === 'communityConfig'"` 区块：3 个配置项（gitee 组织名称 / gitee 企业名称 / 接入漏洞的库表社区名称）el-input + el-form required 校验，configDisabled 查看/编辑/提交/取消模式与页签内既有配置项同构
- [ ] FRAME_WORK 前缀 `/project/*-cve-config` 四接口实现读取/保存（已确认：get/delete 走 URL query `projectId`，add/update 走 body `projectId、cveOrg、orgPath、enterpriseName`）
- [ ] 保存成功后重查配置实时生效；i18n 中英文 locale 补 key

### 5. 验证

- [ ] ESLint：改动文件 0 新增 error
- [ ] vue-tsc：无本次改动引入的类型错误
- [ ] 手工回归：新增项目（默认否、切换后提交正确）、编辑项目回填、列表 3 列展示与树形展开、改名全流程（权限/校验/刷新）、社区配置页签查看/编辑/保存
- [ ] pre-commit 钩子通过

## 后端依赖（已全部确认）

- [x] 项目名称修改接口：POST `/project/update-project-name`（参数拼接 URL query：`projectId: Integer`、`projectName`）
- [x] 重复校验：无独立接口，由保存接口校验名称重复并返回冲突错误信息
- [x] 项目列表接口返回 isHwProject / isHaveCommonAccount / isCve；详情接口返回 isCve
- [x] 社区配置四接口：GET `/project/get-cve-config`（query: projectId）、POST `/project/add-cve-config`、POST `/project/update-cve-config`（body: projectId、cveOrg、orgPath、enterpriseName）、POST `/project/delete-cve-config`（query: projectId），FRAME_WORK 前缀
- [x] `project_manage:rename` 权限码；社区配置页签不新增独立权限码，复用社区适配页既有权限

## 交付记录

- 业务仓分支：`feat-project-rename-vuln-config`（已创建）
- 2026-10-21 spec 文档生成，待用户评审与后端接口提供后进入编码
- 2026-10-27 后端接口契约全部确认，spec 文档同步更新（长度上限定稿 50、重复校验确认走保存接口冲突错误、社区配置接口参数形式确认）
