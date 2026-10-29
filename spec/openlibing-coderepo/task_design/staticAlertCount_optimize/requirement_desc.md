# 需求描述

目前分支管理页面的查询接口：[staticAlertCount](https://beta.openlibing.com/gateway/openlibing-coderepo/repo/branch/list) 的 staticAlertCount 字段来源于：
coderepo每次列表查询时通过Feigin实时调codecheck的Mongo聚合接口计算，无任何本地落库或缓存，这也是他必须走全量取回+内存排序的原因，导致性能较慢。

# 方案

1、建议：这个属性直接落表到repo_branch_info表里。写入侧在合适的时机写入数据，针对历史数据也要进行刷新处理.
这样查询侧可以直接基于SQL来排序，不再使用内存拼接。

# 要求

1、请你先给出详细的方案设计(md文档)，输出到当前文件夹下。
