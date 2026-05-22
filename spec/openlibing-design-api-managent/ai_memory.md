# openlibing-design-api-managent AI Memory

本文档保存 `openlibing-design-api-managent` 代码仓可长期复用的 AI 开发规则。当前为初始版本，后续从需求 `archive.md` 中提炼。

## 仓库定位

`openlibing-design-api-managent` 为现代化开源管理平台后端框架，为 openlibing 生态提供基础服务能力，后续系统级职责、工具边界、任务执行链路、安全约束需在 `system_design/` 中逐步补齐。

## 稳定规则

- AI 开发前必须读取当前需求的 `design.md` 和 `task.md`。
- 涉及 Agent 工具调用、权限、安全边界、外部系统访问时，必须补充设计说明后再实现。
- 需求完成后，必须在 `archive.md` 记录 AI 错误、人工修正和可复用规则。

## 常见 AI 错误与规避

| 错误模式 | 规避规则 | 来源需求 |
| --- | --- | --- |


## 技术栈

| 技术 | 版本 | 说明 |
|------|------|------|
| Java | 21 | JDK 版本 |
| Spring Boot | 3.4.4 | 应用框架 |
| Spring Data JPA | - | ORM 框架 |
| MySQL | - | 主数据库 |
| MongoDB | - | 辅助数据库 |
| Redis | - | 缓存 |
| Liquibase | - | 数据库版本管理 |
| Jenkins | - | CI/CD 扫描引擎 |
| GitCode API | v1 | 代码仓平台集成 |
| Swagger/OpenAPI | 2.8.10 | API 文档 |
| Lombok | - | 代码简化 |
| JaCoCo | 0.8.11 | 测试覆盖率 |

## 项目结构

```
src/main/java/com/api/management/
├── config/                          # 配置类
│   ├── AuthHeaderUtil.java          # 认证头工具
│   ├── RedisConfig.java             # Redis 配置
│   └── RestTemplateConfig.java      # RestTemplate 配置
├── constant/                        # 常量定义
│   └── Constant.java
├── controller/                      # 控制器层
│   ├── BaselineController.java      # 基线管理
│   ├── CodeCheckController.java     # 代码检查/接口管理
│   ├── HealthcheckController.java   # 健康检查
│   ├── InterfaceManagementController.java  # 接口管理页面
│   ├── OrgInfoController.java       # 组织信息管理
│   ├── PRController.java            # PR 管理
│   ├── ProjectController.java       # 项目管理
│   ├── ScanPathConfigController.java # 扫描路径配置
│   └── WebhookController.java       # Webhook 接收
├── entity/                          # 实体类
│   ├── bo/                          # 业务对象
│   │   ├── maintainer/              # 维护者相关
│   │   ├── BaselineBo.java
│   │   ├── InterfaceBo.java
│   │   ├── InterfaceRequestBo.java
│   │   ├── PrOpinionBo.java
│   │   ├── RestResponse.java
│   │   └── ...
│   └── dbo/                         # 数据库对象
│       ├── BaselineDo.java
│       ├── InterfaceDo.java
│       ├── OpinionDo.java
│       ├── PRDo.java
│       ├── PrInterfaceDo.java
│       ├── ProjectDo.java
│       └── ...
├── repository/                      # 数据访问层
├── service/                         # 服务层
│   ├── gitcode/                     # GitCode 集成
│   │   ├── GitCodeService.java
│   │   └── MergeScanPoolQuery.java
│   ├── impl/                        # 服务实现
│   ├── jenkins/                     # Jenkins 集成
│   │   ├── JenkinsService.java
│   │   ├── JenkinsResultScheduledThreadPool.java
│   │   └── JenkinsThreadPoolQuery.java
│   ├── strategy/                    # 策略模式（语言匹配）
│   │   ├── LanguageStrategy.java
│   │   ├── LanguageStrategyFactory.java
│   │   └── impl/
│   │       ├── JavaLanguageStrategy.java
│   │       ├── PythonLanguageStrategy.java
│   │       ├── CLanguageStrategy.java
│   │       └── CppLanguageStrategy.java
│   ├── user/                        # 用户服务
│   │   └── GitCodeUserService.java
│   └── ...
└── utils/                           # 工具类
    ├── DiffUtil.java                # Git Diff 解析
    ├── GitUtil.java                 # Git URL 工具
    ├── InterfaceUtils.java          # 接口对比工具
    ├── PathPatternMatcher.java      # 路径模式匹配
    └── XmlUtil.java                 # XML 工具（防 XXE）
```
