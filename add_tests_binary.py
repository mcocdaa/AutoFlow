import os
import sys

test_file = r'C:\Users\20211\.openclaw\workspace-coord\__eval\AutoFlow\plugins\openclaw\tests\test_openclaw_plugin.py'

new_tests = b'''

class TestExecSecurity:
    """\\xe6\\xb5\\x8b\\xe8\\xaf\\x95 exec_command \\xe5\\xae\\x89\\xe5\\x85\\xa8\\xe7\\x89\\xb9\\xe6\\x80\\xa7"""

    def test_safe_mode_normal_command(self):
        """safe_mode=True \\xe6\\x97\\xb6\\xe6\\x99\\xae\\xe9\\x80\\x9a\\xe5\\x91\\xbd\\xe4\\xbb\\xa4\\xe5\\x8f\\xaf\\xe6\\xad\\xa3\\xe5\\xb8\\xb8\\xe6\\x89\\xa7\\xe8\\xa1\\x8c"""
        plugin = OpenClawPlugin(config={"defaults": {"safe_mode": True}})
        result = plugin.exec_command(None, {"command": "echo hello"})
        assert result["exit_code"] == 0
        assert "hello" in result["stdout"]

    def test_safe_mode_false_default(self):
        """safe_mode \\xe9\\x bb\\x98\\xe8\\xae\\xa4\\xe4\\xb8\\xba False\\xef\\xbc\\x8c\\xe5\\x90\\x91\\xe5\\x90\\x8e\\xe5\\x85\\xbc\\xe5\\xae\\xb9"""
        plugin = OpenClawPlugin()
        assert plugin.defaults.get("safe_mode", False) is False
        result = plugin.exec_command(None, {"command": "echo compat"})
        assert result["exit_code"] == 0

    def test_allowed_commands_blocks_disallowed(self):
        """allowed_commands \\xe7\\x99\\xbd\\xe5\\x90\\x8d\\xe5\\x8d\\x95\\xef\\xbc\\x9a\\xe4\\xb8\\x8d\\xe5\\x8c\\xb9\\xe9\\x85\\x8d\\xe6\\x97\\xb6\\xe8\\xbf\\x94\\xe5\\x9b\\x9e command_not_allowed \\xe9\\x94\\x99\\xe8\\xaf\\xaf"""
        plugin = OpenClawPlugin(config={"defaults": {"allowed_commands": ["^echo\\\\s+"]}})
        result = plugin.exec_command(None, {"command": "rm -rf /"})
        assert result["exit_code"] == -1
        assert result["error"] == "command_not_allowed"
        assert "not allowed" in result["stderr"]

    def test_allowed_commands_permits_matching(self):
        """allowed_commands \\xe7\\x99\\xbd\\xe5\\x90\\x8d\\xe5\\x8d\\x95\\xef\\xbc\\x9a\\xe5\\x8c\\xb9\\xe9\\x85\\x8d\\xe6\\x97\\xb6\\xe6\\xad\\xa3\\xe5\\xb8\\xb8\\xe6\\x89\\xa7\\xe8\\xa1\\x8c"""
        plugin = OpenClawPlugin(config={"defaults": {"allowed_commands": ["^echo\\\\s+"]}})
        result = plugin.exec_command(None, {"command": "echo allowed"})
        assert result["exit_code"] == 0
        assert "allowed" in result["stdout"]

    def test_allowed_commands_empty_means_no_restriction(self):
        """allowed_commands \\xe4\\xb8\\xba\\xe7\\xa9\\xba\\xe5\\x88\\x97\\xe8\\xa1\\xa8\\xe6\\x97\\xb6\\xe4\\xb8\\x8d\\xe9\\x99\\x90\\xe5\\x88\\xb6\\xe4\\xbb\\xbb\\xe4\\xbd\\x95\\xe5\\x91\\xbd\\xe4\\xbb\\xa4"""
        plugin = OpenClawPlugin(config={"defaults": {"allowed_commands": []}})
        result = plugin.exec_command(None, {"command": "echo unrestricted"})
        assert result["exit_code"] == 0

    def test_args_mode(self):
        """args \\xe5\\x8f\\x82\\xe6\\x95\\xb0\\xe6\\xa8\\xa1\\xe5\\xbc\\x8f\\xef\\xbc\\x9acommand \\xe5\\x92\\x8c args \\xe5\\x88\\x86\\xe7\\xa6\\xbb"""
        plugin = OpenClawPlugin()
        result = plugin.exec_command(None, {"command": "echo", "args": ["from", "args"]})
        assert result["exit_code"] == 0
        assert "from" in result["stdout"]

    def test_config_exec_timeout(self):
        """config \\xe4\\xb8\\xad\\xe7\\x9a\\x84 exec_timeout \\xe4\\xbc\\x98\\xe5\\x85\\x88\\xe4\\xba\\x8e\\xe9\\xbb\\x98\\xe8\\xae\\xa4\\xe5\\x80\\xbc"""
        import sys
        plugin = OpenClawPlugin(config={"defaults": {"exec_timeout": 1}})
        if sys.platform == "win32":
            result = plugin.exec_command(None, {"command": "ping -n 5 127.0.0.1"})
        else:
            result = plugin.exec_command(None, {"command": "sleep 5"})
        assert result["exit_code"] == -1
        assert result.get("error") == "timeout"
'''

# 读取二进制内容
with open(test_file, 'rb') as f:
    data = f.read()

# 找到 b'if __name__ == "__main__":' 的位置
target = b'if __name__ == "__main__":'
idx = data.find(target)
if idx == -1:
    print("Target not found, appending at end")
    idx = len(data)

# 在目标之前插入新测试，并确保前面有一个空行
# 检查 idx 之前是否是换行符
if idx > 0 and data[idx-1:idx] != b'\n':
    new_tests = b'\n' + new_tests
else:
    # 如果前面已经是空行，确保只有一个空行
    pass

# 插入
new_data = data[:idx] + new_tests + data[idx:]

# 写回
with open(test_file, 'wb') as f:
    f.write(new_data)

print("Added security tests with binary mode.")