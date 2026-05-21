## MODIFIED Requirements

### Requirement: Export API returns task ID

The three export APIs (`/sched-log/export`, `/exec-log/export`, `/build-log/export`) SHALL return a unique task ID as the response `data` string, enabling the frontend to track individual export tasks.

#### Scenario: Export API returns task ID as string

- **WHEN** the frontend calls any of the three export APIs and the backend returns `{ code: 200, data: "abc123" }` (plain string)
- **THEN** the frontend SHALL treat the string value directly as the task ID and use it to register the task in the store

#### Scenario: Export API returns task ID as object during transition

- **WHEN** the frontend calls any of the three export APIs and the backend returns `{ code: 200, data: { id: "abc123" } }`
- **THEN** the frontend MAY extract `data.id` as a backward-compatible fallback, but the primary contract SHALL remain `data` as a string task ID

#### Scenario: Export API returns no usable ID

- **WHEN** the frontend calls any of the export APIs and the response `data` is null, undefined, or has no extractable ID
- **THEN** the frontend SHALL NOT register the task in the store and SHALL show an ElMessage error "导出任务创建失败"

### Requirement: Export list API includes task ID

The export list API (`/export/list`) SHALL include an `id` field in each record of the returned array, enabling the frontend to match records with registered tasks.

#### Scenario: List record contains id field

- **WHEN** the frontend polls the export list API and a record contains an `id` field
- **THEN** the frontend SHALL use `record.id` to match with registered tasks in the store and update their status

#### Scenario: List record missing id field (backward compatible)

- **WHEN** the frontend polls the export list API and a record does not contain an `id` field but contains a `taskId` field
- **THEN** the frontend SHALL fall back to `record.taskId` for matching

#### Scenario: List record has neither id nor taskId

- **WHEN** the frontend polls the export list API and a record has neither `id` nor `taskId`
- **THEN** the frontend SHALL skip that record for task matching (it will still display in the export history dialog as before)

### Requirement: Export history APIs support logged-in and simpleAuth modes

The system SHALL support both export history APIs: logged-in project-level list and simpleAuth task-by-id query.

#### Scenario: Logged-in history query

- **WHEN** the app is not in simpleAuth mode
- **THEN** the frontend SHALL call the project-level export list API with `projectId`

#### Scenario: simpleAuth history query

- **WHEN** the app is in simpleAuth mode
- **THEN** the frontend SHALL call the by-id export history API with `projectId`, `pipelineId`, and export task `id`
