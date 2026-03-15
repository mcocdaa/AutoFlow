import os

test_file = r'C:\Users\20211\.openclaw\workspace-coord\__eval\AutoFlow\plugins\openclaw\tests\test_openclaw_plugin.py'

new_tests = '''
class TestExecSecurity:
    """测试 exec_command 安全特性"""

    def test_safe_mode_normal_command(self):
        """safe_mode=True 时普通命令可正常执行"""
        plugin = OpenClawPlugin(config={"defaults": {"safe_mode": True}})
        result = plugin.exec_command(None, {"command": "echo hello"})
        assert result["exit_code"] == 0
        assert "hello" in result["stdout"]

    def test_safe_mode_false_default(self):
        """safe_mode 默认为 False，向后兼容"""
        plugin = OpenClawPlugin()
        assert plugin.defaults.get("safe_mode", False) is False
        result = plugin.exec_command(None, {"command": "echo compat"})
        assert result["exit_code"] == 0

    def test_allowed_commands_blocks_disallowed(self):
        """allowed_commands 白名单：不匹配时返回 command_not_allowed 错误"""
        plugin = OpenClawPlugin(config={"defaults": {"allowed_commands": ["^echo\\s+"]}})
        result = plugin.exec_command(None, {"command": "rm -rf /"})
        assert result["exit_code"] == -1
        assert result["error"] == "command_not_allowed"
        assert "not allowed" in result["stderr"]

    def test_allowed_commands_permits_matching(self):
        """allowed_commands 白名单：匹配时正常执行"""
        plugin = OpenClawPlugin(config={"defaults": {"allowed_commands": ["^echo\\s+"]}})
        result = plugin.exec_command(None, {"command": "echo allowed"})
        assert result["exit_code"] == 0
        assert "allowed" in result["stdout"]

    def test_allowed_commands_empty_means_no_restriction(self):
        """allowed_commands 为空列表时不限制任何命令"""
        plugin = OpenClawPlugin(config={"defaults": {"allowed_commands": []}})
        result = plugin.exec_command(None, {"command": "echo unrestricted"})
        assert result["exit_code"] == 0

    def test_args_mode_shell_false(self):
        """args 参数模式：command 和 args 分离"""
        plugin = OpenClawPlugin()
        result = plugin.exec_command(None, {"command": "echo", "args": ["from", "args"]})
        assert result["exit_code"] == 0
        assert "from" in result["stdout"]
        assert "args" in result["stdout"]

    def test_config_timeout_override(self):
        """config 中的 exec_timeout 优先于默认值"""
        plugin = OpenClawPlugin(config={"defaults": {"exec_timeout": 1}})
        # 超时 1 秒，执行一个会超时的命令
        import sys
        if sys.platform == "win32":
            result = plugin.exec_command(None, {"command": "ping -n 5 127.0.0.1"})
        else:
            result = plugin.exec_command(None, {"command": "sleep 5"})
        assert result["exit_code"] == -1
        assert result.get("error") == "timeout"
'''

with open(test_file, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 找到 if __name__ == "__main__": 的行号
insert_index = None
for i, line in enumerate(lines):
    if line.strip().startswith('if __name__ == "__main__":'):
        insert_index = i
        break

if insert_index is None:
    # 如果没找到，追加到文件末尾
    lines.append(new_tests)
else:
    # 在 if __name__ 之前插入，保留前面的空行
    # 检查 insert_index 前面是否有空行，如果没有，则添加一个空行
    if insert_index > 0 and lines[insert_index-1].strip() != '':
        lines.insert(insert_index, '\n')
        insert_index += 1
    lines.insert(insert_index, new_tests)

with open(test_file, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Added security tests successfully.")