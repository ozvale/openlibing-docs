## 1. 配置与类型准备

- [x] 1.1 在 config.ts 中新增 pushStatusConfig（0→can_execute, 1→executing, 3→execute_failed, 4→executing, 5→execute_success）并导出
- [x] 1.2 在 reviewDetail.vue 中定义 VulnRepoItem 接口（id, repo, branch, pushStatus, pushStatusName, repoUrl, failReason）

## 2. vulnRepoTable 子组件

- [x] 2.1 创建 detail/components/vulnRepoTable.vue，声明 Props（repoList: VulnRepoItem[], disabled: boolean）和 Emits（update:repoList）
- [x] 2.2 实现 el-table 模板：6列（仓库名称、分支名、发布结果、发布地址、失败原因、操作），根据 pushStatus 和 editingIndex 渲染不同 UI
- [x] 2.3 实现行级状态渲染逻辑：null/3→可编辑+操作按钮，0/1/4→禁用+无操作，5→锁定+链接+无操作
- [x] 2.4 实现编辑态切换：editingIndex + editingBackup，点击编辑→深拷贝备份+进入编辑态，保存→退出编辑态，取消→恢复备份+退出编辑态
- [x] 2.5 实现互斥编辑约束：一行编辑时其他行的编辑按钮不可点击
- [x] 2.6 实现新增行：点击新增行按钮→取消当前编辑（如有）→追加空行→直接进入编辑态
- [x] 2.7 实现删除行：splice 移除行，若删除编辑行则重置 editingIndex 和 editingBackup
- [x] 2.8 实现保存校验：repo 不能为空（repo 名称允许重复，不做唯一性校验）
- [x] 2.9 实现发布结果列 statusIcon 渲染：使用 pushStatusConfig 映射 pushStatus 到 statusIcon 状态
- [x] 2.10 实现发布地址列：pushStatus===5 时渲染 `<a>` 链接，否则显示 "--"
- [x] 2.11 实现失败原因列：pushStatus===3 时显示 failReason 文本，否则显示 "--"
- [x] 2.12 实现 emit 通知：行数据变化时 emit update:repoList 通知父组件

## 3. reviewDetail.vue 父组件改造

- [x] 3.1 删除 vulnNoticeForm.repos 字段，新增 vulnRepoList ref（VulnRepoItem[]）
- [x] 3.2 删除 isVulnBulletinFormInitialized 相关的 repos 回填逻辑（L419-433 中 repos 部分）
- [x] 3.3 修改 getDetailData 回填逻辑：从 vulnerabilityBulletinList[0].repoStatusList 回填 vulnRepoList（忽略 retryCount）
- [x] 3.4 实现轮询合并函数 mergeRepoList：编辑行完全不动，非编辑行按 id 整行覆盖，新增后端行追加，消失行移除，null id 行保留
- [x] 3.5 在 getDetailData 轮询回调中调用 mergeRepoList 替代直接赋值 vulnRepoList
- [x] 3.6 修改 handlePublishVulnNotice：repos 参数从 string[] 改为 {repo: branch} object，从 vulnRepoList 转换
- [x] 3.7 修改模板：删除 textarea 和 showVulnBulletinUrls URL 列表，替换为 vulnRepoTable 子组件
- [x] 3.8 删除 showVulnBulletinUrls computed（已移入子组件逻辑）
- [x] 3.9 保留 vulnBulletinStatus、isVulnFormDisabled、currentVulnBulletin computed 不变
- [x] 3.10 发布公告按钮：增加编辑态检查，如有编辑行提示用户先保存或取消

## 4. 样式

- [x] 4.1 vulnRepoTable.vue 中添加表格样式（与项目现有 el-table 风格一致）
- [x] 4.2 编辑态 input 样式、操作按钮样式、新增行按钮样式
