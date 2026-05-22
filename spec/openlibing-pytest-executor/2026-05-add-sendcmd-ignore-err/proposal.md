# Proposal: Add `ignore_err` Parameter and Dict Return Type to SSH Command Execution

## Summary

Add an `ignore_err` parameter to SSH command execution methods (`sendcmd` and `sendcmd_interactive`) in pytest-testkit. Change the return type from string to dictionary `{'success': bool, 'stdout': str, 'stderr': str}`. **Never throw exceptions** - all status is reflected in the `success` field.

## Motivation

Currently, `ssh_cmd()` and `ssh_cmd_interactive()` methods throw exceptions when commands fail. This proposal changes to **never throw exceptions** and use the `success` field to indicate execution status.

Key changes:
- Add `ignore_err` parameter to control `success` behavior on failure
- Change return type to dictionary with `success`, `stdout`, `stderr`
- Track `matched_prompt` status in interactive mode
- **No exceptions thrown** - callers check `result['success']` instead

## Scope

### In Scope

- Add `ignore_err` parameter to `Ssh.ssh_cmd()` and `Ssh.ssh_cmd_interactive()`
- Add `ignore_err` parameter to `Device.sendcmd()` and `Device.sendcmd_interactive()`
- Change return type to dictionary: `{'success': bool, 'stdout': str, 'stderr': str}`
- **Never throw RuntimeError** - use `success` field to indicate failure
- Unify error handling logic between `_direct_exec_cmd()` and `_jump_exec_command()`
- Add `matched_prompt` tracking in interactive commands

### Out of Scope

- File transfer methods (`put_file`, `get_file`)
- Additional status reporting mechanism beyond the dictionary

## Impact

- **Backward Compatible**: **NO** - return type changes from `str` to `dict`
- **Breaking Changes**: 
  - Return type changes from string to dictionary
  - No exceptions thrown on failure - callers must check `result['success']`
- **Affected Modules**:
  - `pytest_testkit/lib/base/ssh.py`
  - `pytest_testkit/lib/common/environment/device.py`
  - All code that calls `sendcmd()` or `sendcmd_interactive()`

## Return Dictionary Structure

```python
{
    'success': bool,    # True if: (1) command succeeded, OR (2) ignore_err=True
    'stdout': str,      # stdout content (stripped)
    'stderr': str       # stderr content (stripped), empty string if no error
}
```

## Success Field Logic

| Condition | ignore_err | success |
|-----------|------------|---------|
| `exit_code == 0` (command succeeded) | Any | `True` |
| `exit_code != 0` (command failed) | `False` | `False` |
| `exit_code != 0` (command failed) | `True` | `True` (error ignored) |
| Prompt matched (interactive) | Any | `True` |
| Prompt not matched (interactive) | `False` | `False` |
| Prompt not matched (interactive) | `True` | `True` (error ignored) |

**Key insight**: When `ignore_err=True`, `success=True` regardless of command outcome (error was successfully ignored).

## Success Criteria

- **Never throw exceptions** on command failure
- Return dictionary contains `success`, `stdout`, `stderr` fields
- `success=True` when command succeeded OR when `ignore_err=True`
- `success=False` when command failed AND `ignore_err=False`
- stderr content is logged as warning when command fails
- `matched_prompt` is tracked correctly in interactive mode
- Error handling logic is unified between direct and jump modes

## Related Issue

- Issue #10: pytest-testkit插件能力增加 sendcmd部分