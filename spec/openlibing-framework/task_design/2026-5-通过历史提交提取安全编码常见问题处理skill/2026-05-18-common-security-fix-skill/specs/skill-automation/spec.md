## ADDED Requirements

### Requirement: 日志文件解析
skill 必须支持用户直接提供 FindBugs/SpotBugs XML 日志文件作为输入，通过 `<BugInstance>` 标签的 `type` 属性识别问题类型，通过 `<SourceLine>` 标签定位文件和行号。

#### Scenario: XML 日志文件输入
- **WHEN** 用户提供 XML 格式的 FindBugs/SpotBugs 扫描报告
- **THEN** skill 解析所有 `<BugInstance>` 标签，提取 type、文件路径、行号信息

### Requirement: 分批执行机制
处理前必须统计 `<BugInstance>` 标签总数。总数 ≤ 20 时直接逐个处理完毕；总数 > 20 时按每批 20~40 个分批执行。每批处理完后向用户反馈进度（已处理数量/总数量）。

#### Scenario: 小批量直接处理
- **WHEN** 日志文件中 BugInstance 总数 ≤ 20
- **THEN** skill 直接逐个处理所有问题实例，不分批

#### Scenario: 大批量分批处理
- **WHEN** 日志文件中 BugInstance 总数 > 20
- **THEN** skill 按每批 20~40 个分批执行，每批完成后向用户反馈进度

#### Scenario: 批次间强化约束
- **WHEN** 一批处理完成
- **THEN** skill 自动再次调用自身强化约束，然后继续处理下一批

### Requirement: 未覆盖类型处理
当遇到 skill 索引中未列出的问题类型时，必须先向用户介绍该类型的成因和危害，提供修改建议，获得用户确认后才能进行修改。

#### Scenario: 未知问题类型
- **WHEN** skill 遇到索引中未列出的 BugInstance type
- **THEN** skill 向用户说明成因和危害，提供修改建议，等待用户确认后才执行修改

### Requirement: 调用点追溯
当修改了方法的签名或行为后，必须搜索该方法在项目中所有调用位置，逐一验证并做对应修改，确保编译通过。

#### Scenario: getter 返回类型变更
- **WHEN** skill 将 getter 从直接返回改为防御性复制（返回类型不变但行为变化）
- **THEN** skill 搜索该方法所有调用点，验证调用方是否需要同步修改
