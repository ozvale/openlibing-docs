## ADDED Requirements

### Requirement: Accept frontend sort parameters on query-project-user

The `POST /project/user/query-project-user` endpoint SHALL accept optional `sortColumn` and `sortOrder` fields in the request body (`UserDTO`), matching the payload sent by `projectUserManage.vue`.

#### Scenario: Request includes createTime descending sort

- **WHEN** the client sends `sortColumn: "createTime"` and `sortOrder: "descending"`
- **THEN** the service SHALL order results by `create_time` in descending order

#### Scenario: Request includes createTime ascending sort

- **WHEN** the client sends `sortColumn: "createTime"` and `sortOrder: "ascending"`
- **THEN** the service SHALL order results by `create_time` in ascending order

#### Scenario: Request omits sort parameters

- **WHEN** the client sends empty or missing `sortColumn` and `sortOrder` (initial page load)
- **THEN** the service SHALL default to ordering by `create_time DESC`

#### Scenario: Client clears column sort

- **WHEN** the client sends `sortColumn: "createTime"` and `sortOrder: null` (Element Plus sort cleared)
- **THEN** the service SHALL default to ordering by `create_time DESC`

### Requirement: Reject unsafe sort column values

The service MUST NOT use raw client-provided column names in SQL. Only whitelisted frontend column names SHALL be mapped to database columns.

#### Scenario: Unknown sort column

- **WHEN** the client sends `sortColumn: "userName"` with any `sortOrder`
- **THEN** the service SHALL ignore the unknown column and order by `create_time DESC`

#### Scenario: SQL injection attempt in sort column

- **WHEN** the client sends `sortColumn` containing SQL fragments (e.g. `"createTime; DROP TABLE"`)
- **THEN** the service SHALL NOT reflect the value in SQL and SHALL fall back to `create_time DESC`

### Requirement: Consistent sort across all query paths

Project user list queries SHALL apply the resolved sort order in all three mapper query paths: full UNION list, filter by openLiBing user id, and filter by third-party account.

#### Scenario: Sort with user id filter

- **WHEN** the query resolves to `queryProjectUserByUserIdLimit` and sort is `createTime` ascending
- **THEN** results SHALL be ordered by `create_time ASC` before pagination

#### Scenario: Sort with third-party account filter

- **WHEN** the query resolves to `queryProjectUserByAccountLimit` and sort is `createTime` descending
- **THEN** results SHALL be ordered by `create_time DESC` before pagination

#### Scenario: Sort on default UNION query

- **WHEN** the query resolves to `queryProjectUserByLimit` and sort is `createTime` ascending
- **THEN** the combined UNION result SHALL be ordered by `create_time ASC` with stable tie-breakers (`id DESC`, `user_identifier DESC`, `source_table DESC`)

### Requirement: Response createTime format unchanged

The `createTime` field in each list item SHALL remain a string in `yyyy-MM-dd HH:mm:ss` format (or null), compatible with the frontend display logic (`split('.')[0].replace(/[A-Z]/, ' ')`).

#### Scenario: Successful query returns createTime

- **WHEN** a project user record has a creation timestamp
- **THEN** the response item SHALL include `createTime` as a string matching `DateUtilsExt.formatDateTime` output
