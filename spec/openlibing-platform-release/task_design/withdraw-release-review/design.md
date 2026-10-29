# 发布评审单撤回功能 — 技术方案

**日期**: 2026-08-04

## 状态枚举

复用既有 `ReleaseStatus` 枚举，不新增状态：

| 枚举            | value           | code | 说明        |
| --------------- | --------------- | ---- | ----------- |
| SAVE            | save            | -1   | 新建/编辑态 |
| IN_REVIEW       | submit          | 0    | 评审中      |
| IN_SIGNED       | signed          | 1    | 发布签发中  |
| RELEASE_FAILED  | release_failed  | 2    | 发布失败    |
| RELEASE_SUCCESS | release_success | 3    | 发布成功    |

撤回操作：将 `reviewStatus` 设为 `SAVE.code (-1)`。

## 接口设计

```
POST /base/withdrawReleaseReview
  userId   (RequestParam)
  projectId(RequestParam)
  id       (RequestParam, 评审单id)
返回 DataResult<Integer>（评审单id）
```

## 核心流程

```
1. releaseReviewDao.selectById(id)
2. 校验存在性 → 不存在返回"该评审单不存在"
3. 校验权限 → creatorId != userId 返回"无修改权限"
4. reviewEntityOld.setReviewStatus(SAVE.code)
5. releaseReviewDao.updateById(reviewEntityOld)
6. return successData(id)
```

## 影响范围

| 文件                        | 改动                            |
| --------------------------- | ------------------------------- |
| ReleaseBaseController.java  | 新增 withdrawReleaseReview 接口 |
| ReleaseBaseService.java     | 新增方法声明                    |
| ReleaseBaseServiceImpl.java | 新增方法实现                    |

不涉及：数据库 schema 变更、对外契约变更（新接口不破坏既有）、评审项表、发布流程。

## 设计约束

- 复用 deleteReleaseReview 的权限与存在性校验模式，保持一致性
- 不限制来源状态（所有状态可撤回）
- 不重置评审项状态，避免评审人重复工作
- 无新增依赖
