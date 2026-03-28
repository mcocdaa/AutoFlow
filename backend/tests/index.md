---
title: 测试目录
version: "1.0"
keywords: [tests, 测试, pytest]
description: 后端单元测试和集成测试
---

# Tests 测试目录

本目录包含后端的单元测试和集成测试。

## 📁 文件列表

- [test_hooks.py](test_hooks.py)：钩子测试
- [test_control_flow.py](test_control_flow.py)：控制流测试
- [test_variable_resolution.py](test_variable_resolution.py)：变量解析测试
- [test_condition.py](test_condition.py)：条件判断测试
- [test_foreach.py](test_foreach.py)：ForEach 循环测试
- [test_minimal_loop.py](test_minimal_loop.py)：最小循环测试
- [test_output_externalizer.py](test_output_externalizer.py)：输出外部化测试

## 🚀 运行测试

### 运行所有测试

```bash
pytest tests/ -v
```

### 运行特定测试

```bash
pytest tests/test_hooks.py -v
```

### 显示覆盖率

```bash
pytest tests/ --cov=app --cov-report=html
```
