# 【openlibing-web】代码仓模块改造 — 实现任务

## 进度: 6/6 complete

- [x] Task 1: index.vue tabs 化承载代码仓列表与分支管理，branchPaneKey 控制面板重建；入口进入重置条件、详情返回保留条件、切 tab 保持状态
- [x] Task 2: 新增分支管理 API、筛选与自动过滤，修复列排序/分页溢出/内边距
- [x] Task 3: 仓库入口冲突检测与全局配置弹窗 GlobalConfigDialog（平台分区、仅保存激活 tab、令牌必填校验）
- [x] Task 4: 保存配置失败时非法 sig 路径红色高亮（后端路径反引号/空格清洗）与错误提示，sig-path 提示补充示例
- [x] Task 5: 抽取 useSigSync 组合式函数（轮询 + 10 分钟超时），同步 issue 弹窗 go-modify 操作与路径示例
- [x] Task 6: 一键同步接口合并进同步仓库接口（保留校验失败返回），sig 路径批量校验，同步后刷新列表
