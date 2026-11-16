# 需求背景

## 业务场景

openlibing-web 管理中心（manageCenter）聚合漏洞挖掘（argus）子应用的管理页面，通过 Wujie 微前端方式嵌入。argus 子应用新增了「用户白名单」（access-control）能力，主应用需要为其注册路由与菜单入口。

## 问题痛点

1. argus 子应用的用户白名单页面已在子应用内上线，但主应用管理中心缺少路由与菜单入口，用户无法从 openlibing-web 导航进入。
2. 管理中心首页「漏洞挖掘」能力卡片的能力列表未包含该入口。

## 需求目标

1. 在 `manageRouter.ts` 的 argus 管理路由组下新增 `accessControl` 路由（`/manageCenter/argus-access-control`），以 Wujie 中间件加载 argus 子应用 `argus/access-control` 页面，鉴权沿用 `argus_manage`。
2. 在管理中心侧边菜单「漏洞挖掘」分组注册「用户白名单」菜单项。
3. 在管理中心首页「漏洞挖掘」能力卡片的能力路由列表中加入 `accessControl`。

## 验收标准

### 功能验收

1. 拥有 `argus_manage` 权限的用户在管理中心侧边栏「漏洞挖掘」分组看到「用户白名单」菜单项，点击进入 argus 子应用的用户白名单页面。
2. 管理中心首页「漏洞挖掘」能力卡片点击可跳转/覆盖用户白名单能力。
3. 无 `argus_manage` 权限的用户不展示该菜单入口（路由级权限守卫拦截）。

### 非功能验收

1. 路由配置与同组 argus 路由（dashboard/projects/schedules/system）风格一致。
2. 通过 Prettier / ESLint / pre-commit 检查。

## 关联 Issue

[openlibing/openlibing-vulnerability-hunting#85](https://gitcode.com/openlibing/openlibing-vulnerability-hunting/issues/85)（Argus 使用体验优化：增加用户白名单功能）

## 关联分支

openlibing-web `feat_argus_add_menu`（commit 955523787）

## 期望交付时间

2026-11-13
