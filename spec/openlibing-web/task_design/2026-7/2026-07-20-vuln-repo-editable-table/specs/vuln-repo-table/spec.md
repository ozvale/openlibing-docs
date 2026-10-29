## ADDED Requirements

### Requirement: VulnRepoTable displays 6-column editable table
The system SHALL display a table with 6 columns: 仓库名称 (repo), 分支名 (branch), 发布结果 (pushStatusName), 发布地址 (repoUrl), 失败原因 (failReason), 操作 (action buttons).

#### Scenario: Empty table with no rows
- **WHEN** vulnRepoList is empty and the vulnerability bulletin section is visible
- **THEN** the table displays no rows and shows a "新增行" button at the bottom

#### Scenario: Table with multiple rows of different statuses
- **WHEN** vulnRepoList contains rows with pushStatus values of null, 0, 1, 3, 4, 5
- **THEN** each row renders according to its pushStatus: null/3 rows show edit/delete buttons, 5 rows show repoUrl as clickable link, 0/1/4 rows show disabled repo/branch fields with no action buttons

### Requirement: Row-level status determines UI behavior
The system SHALL render each row based on its pushStatus value:
- null (new row): repo and branch as editable inputs, action column shows 编辑/删除
- 0 (待发布): repo and branch as disabled text, no action buttons
- 1 (执行中): repo and branch as disabled text, pushStatusName shown with statusIcon, no action buttons
- 3 (发布失败): repo and branch as editable inputs, failReason displayed, action column shows 编辑/删除
- 4 (发布中): repo and branch as disabled text, pushStatusName shown with statusIcon, no action buttons
- 5 (发布成功): repo and branch as locked text, repoUrl displayed as `<a>` link, no action buttons

#### Scenario: Successful row is locked
- **WHEN** a row has pushStatus === 5
- **THEN** repo and branch display as non-editable text, repoUrl renders as a clickable `<a>` link with target="_blank", the action column shows no buttons

#### Scenario: Failed row is editable
- **WHEN** a row has pushStatus === 3
- **THEN** failReason is displayed as text, the action column shows 编辑 and 删除 buttons

#### Scenario: Executing row is waiting
- **WHEN** a row has pushStatus === 1 or 4
- **THEN** repo and branch display as disabled text, pushStatusName shows with statusIcon, no action buttons

### Requirement: Inline editing with save/cancel toggle
The system SHALL support inline editing where clicking 编辑 on an eligible row (pushStatus === 3 or null) switches that row to edit mode. In edit mode, repo and branch become active inputs, and the action column switches from 编辑/删除 to 保存/取消. Only one row MAY be in edit mode at a time.

#### Scenario: Enter edit mode on a failed row
- **WHEN** user clicks 编辑 on a row with pushStatus === 3
- **THEN** the row enters edit mode: repo and branch become input fields with current values, action column shows 保存 and 取消 buttons, all other rows' edit buttons become unavailable

#### Scenario: Save edit
- **WHEN** user clicks 保存 in edit mode
- **THEN** the row exits edit mode, repo and branch values are written to the row data, editingIndex is set to null, editingBackup is cleared

#### Scenario: Cancel edit
- **WHEN** user clicks 取消 in edit mode
- **THEN** the row exits edit mode, repo and branch values are restored from editingBackup, editingIndex is set to null, editingBackup is cleared

#### Scenario: Attempt to edit another row while one is editing
- **WHEN** a row is already in edit mode and user clicks 编辑 on another eligible row
- **THEN** the system SHALL NOT allow the second row to enter edit mode; the first row remains in edit mode

### Requirement: Add new row in edit mode
The system SHALL allow adding a new row via a "新增行" button at the bottom of the table. The new row SHALL immediately enter edit mode with empty repo and branch fields. If another row is currently in edit mode, the current edit SHALL be cancelled first.

#### Scenario: Add new row when no row is editing
- **WHEN** user clicks 新增行 and no row is in edit mode
- **THEN** a new row with empty fields and pushStatus=null is appended to vulnRepoList, the new row immediately enters edit mode (editingIndex = last index)

#### Scenario: Add new row when another row is editing
- **WHEN** user clicks 新增行 and another row is in edit mode
- **THEN** the current editing row is cancelled (values restored from backup), then a new empty row is appended and enters edit mode

### Requirement: Delete row
The system SHALL allow deleting a row with pushStatus === 3 or null via the 删除 button. If the deleted row is the current editing row, editingIndex SHALL be reset to null.

#### Scenario: Delete a non-editing failed row
- **WHEN** user clicks 删除 on a row with pushStatus === 3 that is not in edit mode
- **THEN** the row is removed from vulnRepoList

#### Scenario: Delete the currently editing row
- **WHEN** user clicks 删除 on the row that is currently in edit mode
- **THEN** the row is removed from vulnRepoList, editingIndex is set to null, editingBackup is cleared

### Requirement: Repo name uniqueness is not enforced
The system SHALL NOT validate repo name uniqueness when adding or editing rows. Duplicate repo names are allowed.

#### Scenario: Add row with duplicate repo name
- **WHEN** user saves a new row with a repo name that already exists in another row
- **THEN** the row is saved successfully without any uniqueness validation error

### Requirement: Publish submission converts vulnRepoList to repos object
The system SHALL convert vulnRepoList to a `{repoName: branchName}` object when submitting via triggerVulnerabilityBulletin. Rows with empty repo SHALL be excluded from the submission.

#### Scenario: Submit with multiple rows
- **WHEN** user clicks 发布公告 with vulnRepoList containing [{repo:"repo1", branch:"branch1"}, {repo:"repo2", branch:"branch2"}]
- **THEN** the repos parameter is {"repo1": "branch1", "repo2": "branch2"}

#### Scenario: Submit with row in edit mode
- **WHEN** user clicks 发布公告 while a row is in edit mode
- **THEN** the system SHALL prompt the user to save or cancel the editing row before submitting

### Requirement: Polling merge preserves editing rows
The system SHALL NOT modify any row that is currently in edit mode during polling refresh. For non-editing rows, the system SHALL match by id field and overwrite with backend data. New rows from backend (no matching id in local list) SHALL be appended. Local rows with id that have no backend match SHALL be removed. Local rows with null id (newly added, not yet submitted) SHALL be preserved unchanged.

#### Scenario: Polling refresh with editing row
- **WHEN** polling returns new data and row at editingIndex is in edit mode
- **THEN** the editing row is completely untouched (no field updates), all other rows are updated with backend data by id matching

#### Scenario: Polling refresh adds new backend row
- **WHEN** polling returns a row with an id not present in local vulnRepoList
- **THEN** the new row is appended to vulnRepoList

#### Scenario: Polling refresh removes row no longer in backend
- **WHEN** a local row has an id that no longer exists in backend data
- **THEN** the row is removed from vulnRepoList (unless it is the editing row)

#### Scenario: Polling preserves unsubmitted new rows
- **WHEN** local vulnRepoList has a row with id === null (not yet submitted)
- **THEN** the row is preserved unchanged during polling merge

### Requirement: Bulletin-level status display remains unchanged
The system SHALL keep the existing vulnBulletinStatus and isVulnFormDisabled computed properties unchanged. The legend statusIcon and fixedProduct input disabled logic continue to use bulletin-level publishStatus.

#### Scenario: Bulletin-level statusIcon unchanged
- **WHEN** vulnerabilityBulletinList[0].publishStatus is 3, 5, or other
- **THEN** statusIcon displays execute_failed, execute_success, or executing respectively, same as current behavior

#### Scenario: fixedProduct disabled logic unchanged
- **WHEN** no bulletin data exists
- **THEN** fixedProduct input is editable
- **WHEN** publishStatus !== 3
- **THEN** fixedProduct input is disabled
