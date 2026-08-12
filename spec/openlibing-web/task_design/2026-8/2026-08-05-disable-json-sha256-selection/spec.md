## ADDED Requirements

### Requirement: 行可选性过滤规则

`obsDetails.vue` 的 el-table 在发布评审嵌入模式下，SHALL 通过 `selectable` 属性与 `handleSelectionAllChange` 事件处理函数，统一过滤掉不可作为发布产物勾选的文件类型，确保回传父组件 `@getSelectedData` 的行集合不含伴生/校验类文件。

#### Scenario: 文件夹不可选

- **WHEN** `row.type === 'folder'`
- **THEN** 该行不可勾选

#### Scenario: json 扩展名不可选

- **WHEN** `row.type` 为 `json`（大小写不敏感，含 `JSON`/`Json`）
- **THEN** 该行不可勾选

#### Scenario: sha256 校验和文件不可选

- **WHEN** `row.type` 为 `sha256`/`sha256sum`/`sum`（大小写不敏感）
- **THEN** 该行不可勾选

#### Scenario: 全选过滤一致

- **WHEN** 用户点击全选
- **THEN** `handleSelectionAllChange` emit 的集合与 `selectable` 单选判定语义一致，均不含 `folder`/`json`/`sha256`/`sha256sum`/`sum`

#### Scenario: 取消全选

- **WHEN** 用户取消全选
- **THEN** emit 空集合，`getSelectedData` 第二参数为 `false`

#### Scenario: getFileExtension 不受影响

- **WHEN** 文件图标渲染调用 `getFileExtension`
- **THEN** 其大小写行为保持原状，图标映射 `v-if` 链不受本次改动影响
