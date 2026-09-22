# Proposal: Add `cwd` Parameter to SSH Command Execution

## Summary

Add a `cwd` (current working directory) parameter to SSH command execution methods in pytest-testkit, allowing commands to be executed in a specified directory without manual `cd` prefixes.

## Motivation

Currently, `ssh_cmd()` and `ssh_cmd_interactive()` methods do not support specifying a working directory. Users must manually prefix commands with `cd /path/to/dir && ` to execute commands in a specific directory, which is:

1. **Error-prone**: Manual path quoting can lead to shell injection vulnerabilities
2. **Inconsistent**: Different from Python's `subprocess.run(cwd=...)` API convention
3. **Verbose**: Requires boilerplate for every directory-specific command

## Scope

### In Scope

- Add `cwd` parameter to `Ssh.ssh_cmd()` and `Ssh.ssh_cmd_interactive()`
- Add `cwd` parameter to `Device.sendcmd()` and `Device.sendcmd_interactive()`
- Update internal `_direct_exec_cmd()` and `_jump_exec_command()` to handle directory changes
- Ensure backward compatibility (default `cwd=None` preserves existing behavior)

### Out of Scope

- File transfer methods (`put_file`, `get_file`)
- Shell session management
- New connection types

## Impact

- **Backward Compatible**: Yes, all new parameters have default values
- **Breaking Changes**: None
- **Affected Modules**:
  - `pytest_testkit/lib/base/ssh.py`
  - `pytest_testkit/lib/common/environment/device.py`

## Success Criteria

- Commands can be executed in a specified directory via `cwd` parameter
- Paths with spaces and special characters are properly quoted
- Existing code continues to work without modification