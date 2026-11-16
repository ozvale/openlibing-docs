# 63-fix-reviewer-permission — 需求背景与验收标准

## 背景

防投毒问题屏蔽申请支持添加审核对象，但接口仅校验 reviewerId 不能为当前用户 id，直接采用前端传入的用户信息，未校验被添加的审核人是否拥有对应仓库的权限，任意用户可被添加为审核对象，存在权限控制不当风险。

关联业务 Issue：openlibing/openlibing-anti-poison#63

## 需求范围

- 屏蔽申请新增审核人时校验其是否拥有相应仓库权限
- 拒绝无权限用户作为审核对象

## 验收标准

- [x] 无对应仓库权限的用户无法被添加为审核对象（已随业务 PR openlibing/openlibing-anti-poison#139 交付）

## 风险

无。
