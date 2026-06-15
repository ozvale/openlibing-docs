# add-update-time

## 需求背景

/query-repo 接口返回的数据中缺少 updateTime（更新时间）字段，导致代码仓管理页面无法显示仓库的更新时间。

## 功能描述

- 在 `RepoServiceImpl.buildSpaceRepoDTO()` 方法中，参照 `createTime` 的设置方式，将 `updateAt`(Date) 格式化后赋值给 `updateTime` 字段
- 对 `updateAt` 为 null 的情况做安全处理

## 验收标准

- [ ] /query-repo 接口返回结果中包含 updateTime 字段
- [ ] updateTime 格式与 createTime 一致（yyyy-MM-dd HH:mm:ss）
- [ ] updateAt 为 null 时不会抛出 NullPointerException

## 影响范围

- 修改文件：RepoServiceImpl.java
- 影响接口：/project-repo/query-repo

## 关联 Issue

openlibing/openlibing-coderepo#40
