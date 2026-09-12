# 【openlibing-cicd-web】流水线列表筛选分页缓存与安全编译选项新增 fstack-check 列 — 实现任务

## 进度: 5/5 complete

- [x] Task 1: pipeline.vue 新增 SessionStorage 缓存（getStorageKey / saveFilterCache / restoreFilterCache），key 按 projectId 隔离
- [x] Task 2: 统一监听筛选/分页/分组变化自动写入缓存，切换项目时恢复对应缓存
- [x] Task 3: 无缓存时先无条件重置分组/筛选/分页为默认值再覆盖缓存，避免上个项目状态残留
- [x] Task 4: SecurityOptions 概览表格新增 fstack-check 分组（总文件数/满足数/coverage，STACKCLASH 前）并注册列配置面板
- [x] Task 5: FileDetailDialog 新增 options.fstackCheck 列
