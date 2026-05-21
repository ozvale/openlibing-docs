## ADDED Requirements

### Requirement: Export task registration

The system SHALL provide a Pinia store (`useExportTaskStore`) that allows components to register export tasks. Each task SHALL contain: id (exportId from backend), taskName, status (generating/ready/failed), url, message, createTime, autoDownload flag, downloaded flag, and source type with sourceMetadata.

#### Scenario: Register a new export task with ID from backend

- **WHEN** a component calls `addTask()` with a task ID (extracted from the export API response) and task metadata
- **THEN** the task SHALL be added to the store with the given ID, status `generating`, autoDownload `true`, downloaded `false`, and the global polling SHALL start if not already running

#### Scenario: Reject duplicate task registration

- **WHEN** `addTask()` is called with an id that already exists in the store
- **THEN** the existing task SHALL NOT be duplicated; the store SHALL remain unchanged

#### Scenario: Concurrent task limit

- **WHEN** `addTask()` is called while there are already 10 tasks in the store
- **THEN** the system SHALL show an ElMessage warning "导出任务过多，请稍候" and SHALL NOT add the task

### Requirement: Global polling for export status

The system SHALL maintain a single global polling instance that periodically checks the status of all `generating` tasks. In logged-in mode, the polling SHALL call `exportPipelineLogList` and match records by `id`. In simpleAuth mode, the polling SHALL call `exportPipelineLogListById` per generating task using `projectId`, `pipelineId`, and task `id`.

#### Scenario: Start polling when first task is added

- **WHEN** the first task with status `generating` is added and no polling timer is active
- **THEN** the system SHALL immediately fetch the status once and start a 3-second interval poll

#### Scenario: Match and update task by ID

- **WHEN** the polling response contains a record with `id` matching a task in the store
- **THEN** the system SHALL update that task's status, url, and message based on the record data (url non-empty → ready, message contains failure keywords → failed, otherwise → generating)

#### Scenario: Poll in simpleAuth mode by task ID

- **WHEN** the app is in simpleAuth mode and there are one or more `generating` tasks
- **THEN** the system SHALL call `exportPipelineLogListById` for each generating task with the task's `pipelineId` and `id`, and update the matching task from the returned record

#### Scenario: Skip polling when page is hidden

- **WHEN** `document.hidden` is `true` during a poll tick
- **THEN** the system SHALL skip that poll iteration without resetting the timer

#### Scenario: Stop polling when no generating tasks remain

- **WHEN** all tasks have transitioned to `ready` or `failed` status
- **THEN** the system SHALL stop the polling timer automatically

#### Scenario: Polling timeout

- **WHEN** a task has been in `generating` status for more than 5 minutes
- **THEN** the system SHALL mark that task as `failed` with message "导出超时，请在导出历史中查看"

### Requirement: Automatic download on export ready

The system SHALL automatically trigger a browser download when an export task transitions to `ready` status and has `autoDownload` set to `true`.

#### Scenario: Auto-download on status change to ready

- **WHEN** a task's status changes from `generating` to `ready` and `autoDownload` is `true` and `downloaded` is `false`
- **THEN** the system SHALL call `triggerDownloadByAnchor` with the task's url and taskName, and set `downloaded` to `true`

#### Scenario: Auto-download blocked by browser

- **WHEN** the auto-download is triggered but the browser blocks it (no way to detect programmatically)
- **THEN** the task SHALL still show `downloaded: true` in the store; the float panel SHALL always display a "下载" button for ready tasks as a fallback

### Requirement: Persistent export tasks

The system SHALL persist export task snapshots to browser local storage so tasks can be restored after a page refresh or sub-application remount. The persisted snapshot SHALL contain only serializable non-sensitive fields: id, taskName, pipelineId, status, url, message, createTime, createdAtMs, autoDownload, downloaded, source, and sourceMetadata.

#### Scenario: Persist a newly registered task

- **WHEN** a task is successfully added to the export task store
- **THEN** the task snapshot SHALL be written to local storage

#### Scenario: Persist status changes

- **WHEN** a task status, url, message, downloaded flag, or removal state changes
- **THEN** the persisted snapshot SHALL be updated so a future refresh restores the latest state

#### Scenario: Do not persist unsafe data

- **WHEN** the system serializes tasks for persistence
- **THEN** it SHALL NOT persist functions, component refs, tokens, request headers, user credentials, or other non-serializable/sensitive data

#### Scenario: Enforce persistence retention

- **WHEN** persisted tasks are older than the retention window
- **THEN** the system SHALL discard them during restore; the retention window SHALL align with the export history window of 3 days

### Requirement: Restore export tasks after refresh

The system SHALL restore persisted export tasks when the sub-application starts, then resume tracking unfinished tasks.

#### Scenario: Restore generating task after refresh

- **WHEN** the page is refreshed while a task is `generating`
- **THEN** the system SHALL restore the task in the float panel and restart polling for that task

#### Scenario: Auto-download after restored task becomes ready

- **WHEN** a restored task transitions from `generating` to `ready` and `downloaded` is `false`
- **THEN** the system SHALL trigger automatic download and persist `downloaded: true`

#### Scenario: Avoid duplicate auto-download after refresh

- **WHEN** a restored task is already `ready` and has `downloaded: true`
- **THEN** the system SHALL NOT auto-download it again, but SHALL provide a manual "重新下载" action

#### Scenario: Recover from corrupted persistence data

- **WHEN** the persisted task payload is invalid, missing required fields, or cannot be parsed
- **THEN** the system SHALL ignore the corrupted payload and continue loading the page normally

### Requirement: Continue tracking across sub-application switches

The system SHALL preserve export task tracking when the user switches away from and back to the pipeline sub-application.

#### Scenario: Sub-application remains mounted while hidden

- **WHEN** the host switches away from the pipeline sub-application but keeps it mounted
- **THEN** the store SHALL keep the existing task state and the tracking loop SHALL continue according to the page visibility policy

#### Scenario: Sub-application is unmounted and remounted

- **WHEN** the host destroys the pipeline sub-application and the user later enters it again
- **THEN** the store SHALL restore persisted tasks and resume polling for unfinished tasks

#### Scenario: Task becomes ready while sub-application was unmounted

- **WHEN** a task becomes ready while the pipeline sub-application has no running JavaScript context
- **THEN** the system SHALL detect readiness on the first restored poll after remount and trigger automatic download if `downloaded` is `false`

#### Scenario: Page becomes visible again

- **WHEN** the document changes from hidden to visible and there are generating tasks
- **THEN** the system SHALL perform an immediate status check instead of waiting for the next interval tick

### Requirement: Task removal

The system SHALL allow removal of individual tasks from the store.

#### Scenario: Remove a completed task

- **WHEN** a user dismisses a task from the float panel
- **THEN** the task SHALL be removed from the store

### Requirement: Task retry

The system SHALL allow re-triggering the export for a failed task by emitting an event with the task's source information, so the parent component can re-call the original export API.

#### Scenario: Retry a failed task

- **WHEN** a user clicks "重试" on a failed task in the float panel
- **THEN** the system SHALL remove the failed task and emit a `retry` event with the task's source metadata, allowing the triggering component to re-execute the export API call

#### Scenario: Retry a restored task without live callback

- **WHEN** a failed task was restored from persistence and no live retry callback is available
- **THEN** the system SHALL NOT throw an error; it SHALL either show a message asking the user to re-trigger export from the log page or guide the user to export history/manual download
