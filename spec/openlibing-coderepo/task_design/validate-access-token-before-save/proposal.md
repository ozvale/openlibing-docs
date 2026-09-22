# 代码仓管理公共账号正确性校验前置

## 需求背景

在代码仓管理模块中，录入代码仓时（/add-repo接口），如果用户填写了accessToken（代码仓账号令牌），系统没有在保存前校验该token是否有效，而是等到后续查询仓库信息时（/query-repo接口）才通过getUserInfoByAccessToken方法验证token有效性及获取对应的gitcode/gitee账号名。

这导致以下问题：
1. 无效的token被保存到数据库，用户无法及时感知
2. 后续使用该token时才会发现无效，影响webhook设置、分支同步等功能
3. 错误提示不明确，用户难以定位问题

## 功能描述

在/add-repo和/update-repo接口中，当accessToken不为空时，前置校验token有效性：
- 调用Gitee/GitCode的/v5/user API验证token是否有效
- 如果token无效，直接返回失败并提示"该令牌无效，请重新填写"
- 不做：不修改其他校验逻辑，不影响accessToken为空时的行为

## 验收标准

- [ ] /add-repo接口：当accessToken不为空且无效时，返回失败并提示"该令牌无效，请重新填写"
- [ ] /update-repo接口：当isEditAccessToken为true且accessToken不为空且无效时，返回失败并提示"该令牌无效，请重新填写"
- [ ] accessToken为空时，行为不变
- [ ] accessToken有效时，正常保存

## 影响范围

- 模块：RepoServiceImpl（代码仓管理服务）
- 接口：/project-repo/add-repo、/project-repo/update-repo
- 关联Issue：openlibing/openlibing-coderepo#41
