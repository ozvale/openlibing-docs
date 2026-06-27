## ADDED Requirements

### Requirement: API accepts optional isSuccess and isPass filter parameters

The scan result list APIs SHALL accept optional integer filter parameters `isSuccess` and `isPass` in the request body (`ParamModel`). Valid values are `0` (false) and `1` (true). When a parameter is omitted or null, the API MUST NOT filter by that field.

#### Scenario: No filter parameters

- **WHEN** client calls `POST /shield/getScanResult` or `POST /shield/get-scan-pr-result-group` without `isSuccess` or `isPass`
- **THEN** the response includes all records matching other criteria (project, repo, branch, time range, pagination)

#### Scenario: Filter by task success

- **WHEN** client sends `isSuccess: 1`
- **THEN** every item in `data` has task status equivalent to success (`is_success = true` in storage)

#### Scenario: Filter by task failure

- **WHEN** client sends `isSuccess: 0`
- **THEN** every item in `data` has task status equivalent to failure (`is_success = false` in storage)

#### Scenario: Filter by pass status

- **WHEN** client sends `isPass: 1`
- **THEN** every item in `data` has pass status equivalent to passed (`is_pass = true` in storage)

#### Scenario: Filter by not passed

- **WHEN** client sends `isPass: 0`
- **THEN** every item in `data` has pass status equivalent to not passed (`is_pass = false` in storage)

#### Scenario: Combined filters

- **WHEN** client sends both `isSuccess: 1` and `isPass: 0`
- **THEN** every item in `data` satisfies both conditions simultaneously

### Requirement: Filtered count matches filtered data

The `count` field in the list response SHALL reflect the total number of records matching all applied filters (including `isSuccess` and `isPass`), not the unfiltered total.

#### Scenario: Count with isPass filter on PR group list

- **WHEN** client calls `get-scan-pr-result-group` with `isPass: 1` and receives `count: N`
- **THEN** requesting all pages with the same filter returns exactly `N` grouped PR rows in aggregate

### Requirement: Frontend contract alignment

The web client (`PoisoningDetail.vue`) SHALL send filter values as field names `isSuccess` and `isPass` with integer values `0` or `1`, matching the backend `ParamModel` fields without renaming or boolean coercion at the HTTP layer.

#### Scenario: Incremental view filter request

- **WHEN** user selects「通过」on the isPass column in the entry-check (incremental) poisoning detail table
- **THEN** the client request to `get-scan-pr-result-group` includes `isPass: 1` in the JSON body

#### Scenario: Full view filter request

- **WHEN** user selects「失败」on the task status column in the version-check (full) poisoning detail table
- **THEN** the client request to `getScanResult` includes `isSuccess: 0` in the JSON body
