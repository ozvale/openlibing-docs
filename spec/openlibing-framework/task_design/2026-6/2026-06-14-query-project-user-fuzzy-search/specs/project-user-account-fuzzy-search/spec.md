## ADDED Requirements

### Requirement: Fuzzy match accountLogin for non-uniportal platforms

The `POST /project/user/query-project-user` endpoint SHALL treat non-empty `accountLogin` as a **substring filter** (contains match), not an exact equality match, when `accountPlatform` is one of **`gitcode`**, **`gitee`**, or **`openubmc`**.

#### Scenario: Partial gitee account matches project_user_role_info

- **WHEN** the client sends `accountPlatform: "gitee"`, `accountLogin: "test"`, and a valid `projectId`
- **THEN** the service SHALL return project members from `project_user_role_info` whose `account_login` contains `"test"` and `account_platform` equals `"gitee"`

#### Scenario: Partial gitcode login matches logged-in user_role_info member

- **WHEN** the client sends `accountPlatform: "gitcode"`, `accountLogin: "abc"`, and a valid `projectId`
- **THEN** the service SHALL return project members from `user_role_info` whose bound `user_info_gitcode.account_login` contains `"abc"`

#### Scenario: Full third-party account login still returns results

- **WHEN** the client sends a complete `accountLogin` for gitcode, gitee, or openubmc that exactly matches a stored login
- **THEN** the service SHALL include that member in the paginated result list

#### Scenario: No matching third-party account returns empty list

- **WHEN** the client sends a gitcode/gitee/openubmc `accountLogin` that matches no project member
- **THEN** the service SHALL return success with `total: 0` and `data: []`

### Requirement: Non-uniportal account filter applies to UNION data sources

When `accountPlatform` is gitcode, gitee, or openubmc and `accountLogin` is non-empty, the project user list query SHALL apply the fuzzy account filter to **both** UNION branches: openLiBing users (`user_role_info` with platform binding tables) and non-logged-in third-party users (`project_user_role_info`).

#### Scenario: Gitee filter searches both branches

- **WHEN** the client filters with `accountPlatform: "gitee"` and a non-empty `accountLogin`
- **THEN** results MAY include members from `user_role_info` (via `user_info_gitee.account_login`) and from `project_user_role_info` (via `account_login`), merged in the existing UNION ordering

#### Scenario: OpenUBMC filter uses openubmc binding column

- **WHEN** the client filters with `accountPlatform: "openubmc"` and a non-empty `accountLogin`
- **THEN** the user branch SHALL match against `user_info_openubmc.account_login` with contains semantics

### Requirement: Uniportal retains exact-match behavior

For `accountPlatform: "uniportal"`, the endpoint SHALL **NOT** apply substring fuzzy matching. The existing exact-match flow SHALL be preserved unchanged.

#### Scenario: Uniportal exact login resolves via getUser

- **WHEN** the client sends `accountPlatform: "uniportal"`, a valid exact `accountLogin`, and a valid `projectId`
- **THEN** the service SHALL call `commonService.getUser()` with exact `queryByLogin` semantics
- **THEN** when a `userId` is resolved, the service SHALL query via `queryProjectUserByUserIdLimit` (exact user id filter)

#### Scenario: Uniportal login not found returns failure message

- **WHEN** the client sends `accountPlatform: "uniportal"` and an `accountLogin` that cannot be exactly resolved by `getUser`
- **THEN** the service SHALL return the existing business failure message (e.g. user not found / not logged in)
- **THEN** the service SHALL NOT return a fuzzy-matched member list

#### Scenario: Uniportal partial employee id does not fuzzy search

- **WHEN** the client sends `accountPlatform: "uniportal"` and a partial `accountLogin` such as `"x0012"`
- **THEN** the service SHALL NOT execute LIKE-based account filtering
- **THEN** the service SHALL behave as today (typically `failureMessage` from `getUser`, not a partial-match list)

### Requirement: No account filter preserves existing list behavior

When `accountLogin` is empty or missing, or `accountPlatform` is empty, the endpoint SHALL behave as before this change: return the paginated project member list without account substring filtering.

#### Scenario: Empty accountLogin returns full project member list

- **WHEN** the client omits `accountLogin` or sends an empty string
- **THEN** the service SHALL return all project members subject to `projectId`, `userRole`, pagination, and sort parameters

### Requirement: Request and response contract unchanged

The endpoint SHALL NOT add or remove request/response fields. Clients continue to send `accountLogin` and `accountPlatform` in `UserDTO`; response items retain existing fields including `createTime` format and sort behavior.

#### Scenario: projectUserManage.vue payload compatibility

- **WHEN** the client sends the same JSON body as `getCommunityUser` in `projectUserManage.vue`
- **THEN** the request SHALL be accepted without new required fields
- **THEN** the response structure SHALL remain `{ total, data: [...] }` with unchanged item shape

### Requirement: Non-uniportal list query bypasses exact getUser routing

For `query-project-user` list retrieval, when `accountPlatform` is gitcode, gitee, or openubmc and `accountLogin` is provided, the service SHALL NOT use `commonService.getUser()` exact `queryByLogin` resolution to select a single `userId` narrow query path.

#### Scenario: Partial gitcode login skips userId-only narrow query

- **WHEN** `accountPlatform` is `"gitcode"` and `accountLogin` is a partial string that does not exactly match any `queryByLogin` record
- **THEN** the service SHALL execute the fuzzy UNION list query
- **THEN** the service SHALL NOT restrict results to `userrole.user_id = <single id>` from exact lookup

### Requirement: Sort parameters remain effective with fuzzy filter

When `sortColumn` and `sortOrder` are sent together with fuzzy `accountLogin` on gitcode/gitee/openubmc, the service SHALL apply the same sort resolution as defined for project user query sort (default `create_time DESC`, whitelist `createTime` only).

#### Scenario: Fuzzy search with createTime descending

- **WHEN** the client sends fuzzy `accountLogin`, `accountPlatform: "gitee"`, `sortColumn: "createTime"`, `sortOrder: "descending"`
- **THEN** filtered results SHALL be ordered by `create_time DESC` before pagination
