## ADDED Requirements

### Requirement: Float panel visibility and positioning

The system SHALL render a float panel component (`ExportFloatPanel`) fixed at the bottom-right corner of the viewport. The panel SHALL have two states: collapsed and expanded.

#### Scenario: Panel appears when first task is added

- **WHEN** the first export task is registered in the store
- **THEN** the float panel SHALL appear in collapsed state, showing a badge with the count of active (generating + failed) tasks

#### Scenario: Panel auto-expands on first task

- **WHEN** the first export task is registered and the panel was not previously collapsed by the user
- **THEN** the panel SHALL auto-expand for 3 seconds, then collapse back

#### Scenario: Panel hides when all tasks are removed

- **WHEN** all export tasks have been removed from the store
- **THEN** the float panel SHALL hide completely

### Requirement: Collapsed state display

In collapsed state, the panel SHALL display a compact bar with an icon, the text "导出任务", and a badge showing the count of tasks that are `generating` or `failed`.

#### Scenario: Badge updates in real-time

- **WHEN** a task status changes (e.g., from generating to ready)
- **THEN** the badge count SHALL update immediately to reflect only generating + failed tasks

#### Scenario: Click to expand

- **WHEN** user clicks the collapsed panel
- **THEN** the panel SHALL expand to show the task list

### Requirement: Expanded state task list

In expanded state, the panel SHALL display a scrollable list of all current export tasks, each showing: task name, status indicator, and action buttons.

#### Scenario: Generating task display

- **WHEN** a task has status `generating`
- **THEN** the task row SHALL show the task name with a spinning/loading icon and text "生成中..."

#### Scenario: Ready task display with auto-download indicator

- **WHEN** a task has status `ready` and `downloaded` is `true`
- **THEN** the task row SHALL show the task name with a success icon, text "已自动下载", and a "重新下载" link button

#### Scenario: Ready task display without auto-download

- **WHEN** a task has status `ready` and `downloaded` is `false`
- **THEN** the task row SHALL show the task name with a success icon, text "导出完成", and a "下载" primary button

#### Scenario: Failed task display

- **WHEN** a task has status `failed`
- **THEN** the task row SHALL show the task name with an error icon, the error message text, and a "重试" button

#### Scenario: Timeout task display

- **WHEN** a task has status `failed` due to timeout
- **THEN** the task row SHALL show the task name with an error icon, text "导出超时，请在导出历史中查看"

### Requirement: Task actions in float panel

The float panel SHALL provide action buttons for each task based on its status.

#### Scenario: Click download on ready task

- **WHEN** user clicks "下载" or "重新下载" on a ready task
- **THEN** the system SHALL trigger `triggerDownloadByAnchor` with the task's url and taskName

#### Scenario: Click retry on failed task

- **WHEN** user clicks "重试" on a failed task
- **THEN** the system SHALL remove the task from the store and emit a `retry` event with the task's source metadata

#### Scenario: Dismiss a task

- **WHEN** user clicks the close/dismiss icon on a task row
- **THEN** the task SHALL be removed from the store

### Requirement: Link to export history

The expanded panel SHALL include a "查看全部导出历史" link at the bottom.

#### Scenario: Click export history link

- **WHEN** user clicks "查看全部导出历史"
- **THEN** the existing DownloadCenterDialog SHALL open from the float panel context

#### Scenario: Export history dialog is not hidden by float panel or drawer

- **WHEN** DownloadCenterDialog is opened from the float panel
- **THEN** it SHALL be appended to body and rendered above the float panel and pipeline drawer

### Requirement: Auto-collapse after all tasks complete

The panel SHALL automatically collapse after all tasks reach a terminal state (ready or failed).

#### Scenario: Auto-collapse timing

- **WHEN** all tasks are in terminal state (no generating tasks remain)
- **THEN** the panel SHALL auto-collapse after 10 seconds

#### Scenario: User manual collapse

- **WHEN** the user manually clicks the collapse button or × button
- **THEN** the panel SHALL collapse immediately and SHALL NOT auto-expand for subsequent status changes (only badge updates)

### Requirement: Panel z-index and styling

The float panel SHALL have a z-index higher than the main content and pipeline drawer, but lower than el-dialog overlays opened from the float panel, ensuring it remains visible during log viewing and does not block modal interactions.

#### Scenario: Panel behind dialog

- **WHEN** an el-dialog is open
- **THEN** the float panel SHALL render behind the dialog overlay

#### Scenario: Panel above pipeline drawer

- **WHEN** the pipeline JobDrawer is open
- **THEN** the float panel SHALL remain visible and clickable above the drawer
