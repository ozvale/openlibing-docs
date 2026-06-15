# fuzzy-query-account-login

## 需求背景

query-repo-user 接口入参 accountLogin 目前使用精确匹配（`=`）查询，输入带前后空格或部分内容时无法匹配到数据，用户体验差。

关联 Issue: openlibing/openlibing-coderepo#42

## 功能描述

- 对 accountLogin 入参在 Java 层做 trim 处理，去除前后空格
- SQL 查询从精确匹配（`=`）改为模糊匹配（`LIKE`），支持部分匹配搜索

不做：
- 不修改接口入参定义（UserDTO 字段不变）
- 不修改其他查询条件（accountPlatform、roles 等）的匹配逻辑

## 验收标准

- [ ] 输入 accountLogin 带前后空格时能正确查询到结果
- [ ] 输入 accountLogin 部分内容时能模糊匹配到结果
- [ ] 不传 accountLogin 时查询行为不变
- [ ] accountPlatform + accountLogin 组合查询正常工作

## 影响范围

- RepoUserRoleInfoMapper.xml（repoUserQueryWithConditions SQL 片段、countRepoUserByAccount）
- ThreePartyUserInfoMapper.xml（queryByLogin）
- RepoUserServiceImpl.java（queryRepoUser 方法中对 accountLogin 的 trim 处理）
