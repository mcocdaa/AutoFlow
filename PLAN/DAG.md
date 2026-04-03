# AutoFlow DAG工作流核心模型结构还原

## 一、端口模型（节点数据的输入/出口）

### 通用端口基础属性
包含唯一标识、名称、数据类型、是否必填、默认值，是所有输入输出端口的基础规范。

### 输入端口
仅用于接收上游节点传递的数据，遵循基础端口属性，无额外扩展属性。

### 输出端口
用于向外发送数据，除基础属性外，额外支持条件配置，可控制数据是否向下游传递。
- `condition`: 条件表达式，满足条件时数据才向下游传递
- `case`: Switch节点使用的值匹配条件
- `index`: 数组索引，用于Split节点按索引分发
- `field`: 字段名，用于Split节点按字段分发

### 支持的数据类型
包含任意类型、字符串、数字、布尔值、对象、数组，覆盖自动化流程所需的全部数据格式。

```python
PortDataType = Literal["any", "string", "number", "boolean", "object", "array"]
```

---

## 二、节点模型（DAG的核心执行单元）

### 节点基础属性
包含唯一标识、节点名称、节点类型、自定义配置、元数据，是所有流程节点的通用基础。

### 重试配置
支持设置重试次数、重试间隔时间，用于节点执行失败后的自动重试。
```python
class RetrySpec:
    attempts: int = 0          # 重试次数
    backoff_seconds: float = 0.0  # 重试间隔（秒）
```

### 固定内置端口
所有节点默认自带一个**错误输出端口**，专门用于传递节点执行失败的异常信息。

### 端口集合
每个节点可配置多个输入端口、多个输出端口，实现多进多出的数据交互。

### 生命周期钩子
包含执行前、执行后、执行出错三个阶段的触发节点，用于流程的前置校验、后置处理、异常兜底。

---

## 三、连线模型（节点间的数据流连接）

### 连线核心属性
拥有唯一标识，用于区分不同的数据流连接关系。

### 连接规则
仅支持**源节点的输出端口 → 目标节点的输入端口**的单向连接，通过「节点ID.端口ID」的格式精准定位连接端点。
```python
class Edge:
    id: str
    source: str  # 格式: "node_id.port_id"
    target: str  # 格式: "node_id.port_id"
```

### 核心作用
作为数据传输的通道，承载消息在不同节点端口间的传递，构建节点间的依赖关系。

---

## 四、消息模型（端口间传输的数据包）

### 执行状态标识
标记消息是否为成功执行的结果，区分正常数据与异常数据。

### 核心数据载体
存储节点输出的实际业务数据，支持任意格式的数据内容。

### 错误信息
仅在执行失败时填充，记录异常描述，正常执行时为空。

### 元数据信息
包含消息生成时间、来源节点ID、来源端口ID，用于追溯数据流转轨迹。
```python
class MessageMetadata:
    timestamp: str      # ISO格式时间戳
    source_node: str    # 来源节点ID
    source_port: str    # 来源端口ID

class Message:
    success: bool
    data: Any
    error: Optional[str]
    metadata: MessageMetadata
```

---

## 五、DAG工作流整体结构

### 顶层基础信息
包含版本号、工作流名称、描述信息，以及工作流全局的输入端口定义。

### 核心组成部分
由所有流程节点、所有节点间连线构成完整的有向无环图结构。
```python
class DAGWorkflow:
    version: str = "2.0"
    name: str
    description: Optional[str]
    inputs: Dict[str, Any]
    nodes: Dict[str, BaseNode]
    edges: List[Edge]
```

### 内置核心能力

#### 1. 流程验证
- **循环依赖检测**: 使用DFS深度优先搜索检测图中是否存在环
- **端口连接合法性检查**: 验证源端口和目标端口是否存在、类型是否匹配
- **起始/结束节点检查**: 确保工作流包含Start节点和End节点

#### 2. 拓扑排序
基于Kahn算法生成无环的节点执行顺序，保障流程按依赖关系执行：
```python
def topological_sort(self) -> List[str]:
    # 1. 计算每个节点的入度
    # 2. 将入度为0的节点加入队列
    # 3. 依次处理队列中的节点，更新邻接节点的入度
    # 4. 重复直到所有节点处理完毕
```

#### 3. 就绪节点获取
实时筛选出依赖已满足、可立即执行的节点：
```python
def get_ready_nodes(self, available_inputs: Dict[str, Dict[str, Any]]) -> List[str]:
    # 检查节点的所有必填输入端口是否已有数据
    # 返回所有依赖已满足的节点ID列表
```

---

## 六、后端DAG系统架构实现

### 6.1 核心模块结构

```
backend/app/runtime/
├── dag_models.py          # DAG核心数据模型
├── execution_state.py     # 执行状态管理
├── scheduler.py           # DAG调度器（拓扑排序、就绪队列）
├── executor.py            # 节点执行器
├── workflow_runner.py     # 工作流运行器
├── data_router.py         # 数据路由与分发
├── actions.py             # Action注册与内置Actions
├── yaml_loader.py         # YAML工作流加载器
├── yaml_exporter.py       # YAML工作流导出器
├── builtins.py            # 内置Action/Check
├── models.py              # 数据库模型（SQLAlchemy）
├── nodes/                 # 节点类型实现
│   ├── base.py            # 基础节点（Start/End/Action/Pass）
│   ├── control.py         # 控制流节点（If/Switch/For/While/Retry）
│   ├── data.py            # 数据处理节点（Merge/Split）
│   └── composite.py       # 复合节点（Group/Subflow）
└── store/                 # 数据持久化层
    ├── workflow_store.py  # 工作流存储
    └── run_store.py       # 执行记录存储
```

### 6.2 执行引擎架构

#### 6.2.1 状态管理 (execution_state.py)
```python
class ExecutionState:
    workflow_status: WorkflowStatus    # 工作流整体状态
    history: ExecutionHistory          # 节点执行历史记录
    variables: VariableScope           # 变量作用域（支持父子作用域）
    available_inputs: Dict[str, Any]   # 当前可用的输入数据

class NodeExecutionRecord:
    node_id: str
    status: NodeStatus                 # pending/running/completed/failed/skipped
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    error: Optional[str]
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
    retry_count: int
```

#### 6.2.2 调度器 (scheduler.py)
调度器负责任务的调度管理：
- **图构建**: 构建邻接表和入度表
- **入度计算**: 基于节点必填输入端口计算入度
- **就绪队列**: 维护可执行节点的队列
- **拓扑排序**: 提供DAG的拓扑排序能力
- **循环检测**: 检测工作流是否存在循环依赖

#### 6.2.3 执行器 (executor.py)
执行器负责单个节点的执行：
- **输入收集**: 从available_inputs收集节点所需输入
- **重试逻辑**: 支持配置重试次数和退避时间
- **节点执行**: 根据节点类型调用相应的执行逻辑
- **错误处理**: 捕获异常并记录到错误端口
- **生命周期钩子**: before_execute / after_execute / on_error

#### 6.2.4 数据路由器 (data_router.py)
数据路由器负责节点间数据传输：
- **条件评估**: 评估输出端口的condition表达式
- **消息创建**: 封装数据为Message对象
- **数据分发**: 将输出数据分发到下游节点的输入端口
- **端口映射**: 管理"node_id.port_id"到数据的映射

#### 6.2.5 工作流运行器 (workflow_runner.py)
运行器整合各组件，提供完整的工作流执行能力：
```python
def run(self, inputs: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    # 1. 初始化工作流状态
    # 2. 循环执行就绪节点
    # 3. 处理节点执行结果，更新就绪队列
    # 4. 直到所有节点处理完毕
    # 5. 返回工作流输出
```

### 6.3 节点类型实现

#### 6.3.1 基础节点 (nodes/base.py)
| 节点类型 | 职责 |
|---------|------|
| StartNode | 工作流起点，接收初始输入并传递到输出端口 |
| EndNode | 工作流终点，收集输入作为最终输出 |
| ActionNode | 执行注册的Action处理器，支持自定义动作 |
| PassNode | 直接传递数据，可选数据转换 |

#### 6.3.2 控制流节点 (nodes/control.py)
| 节点类型 | 职责 |
|---------|------|
| IfNode | 条件分支，根据condition表达式选择输出路径 |
| SwitchNode | 值匹配分支，根据case值匹配选择输出路径 |
| ForNode | 循环遍历，遍历列表并对每个元素执行处理 |
| WhileNode | 条件循环，条件满足时持续执行 |
| RetryNode | 重试包装，失败时自动重试指定次数 |

#### 6.3.3 数据处理节点 (nodes/data.py)
| 节点类型 | 职责 |
|---------|------|
| MergeNode | 合并多个输入，支持list_concat/object_merge策略 |
| SplitNode | 拆分单个输入，支持by_index/by_field策略 |

#### 6.3.4 复合节点 (nodes/composite.py)
| 节点类型 | 职责 |
|---------|------|
| GroupNode | 分组节点，包含内部子图，通过port_mapping映射内外端口 |
| SubflowNode | 子流程节点，引用并执行其他工作流，支持递归深度限制 |

### 6.4 Action系统

#### 6.4.1 Action注册器 (actions.py)
```python
class ActionRegistry:
    _actions: Dict[str, ActionHandler]

    def register(self, action_type: str, handler: ActionHandler)
    def get(self, action_type: str) -> ActionHandler
    def list_actions(self) -> list[str]
```

#### 6.4.2 内置Actions
- `log`: 日志记录
- `set_var`: 设置变量
- `wait`: 等待指定秒数

#### 6.4.3 核心Registry集成 (builtins.py)
- `core.log`: 核心日志Action
- `core.sleep`: 核心睡眠Action
- `core.always_true`: 始终返回True的Check
- `text.contains`: 文本包含检查

### 6.5 数据持久化

#### 6.5.1 工作流存储 (store/workflow_store.py)
使用SQLAlchemy持久化工作流定义：
- `save_workflow`: 保存/更新工作流
- `get_workflow`: 获取工作流
- `list_workflows`: 列表查询（支持分页、搜索）
- `delete_workflow`: 删除工作流

#### 6.5.2 执行记录存储 (store/run_store.py)
持久化工作流执行记录：
- `save_run`: 保存执行记录
- `get_run`: 获取执行记录
- `list_runs`: 列表查询（支持分页、状态过滤）
- `update_run_status`: 更新执行状态
- `update_node_state`: 更新节点状态

### 6.6 YAML序列化

#### 6.6.1 YAML加载器 (yaml_loader.py)
支持从YAML格式加载工作流：
- 版本验证（仅支持2.0）
- 节点类型映射（12种节点类型）
- 端口引用解析（"node_id.port_id"格式）
- 工作流验证（循环检测、端口连接检查）

#### 6.6.2 YAML导出器 (yaml_exporter.py)
支持将工作流导出为YAML格式：
- 节点序列化
- 端口序列化
- 复合节点特殊处理（Group/Subflow的内部子图）

---

## 七、前端状态管理结构（Pinia Store）

### 核心状态数据
存储当前工作流的所有节点、所有连线数据，作为前端渲染与操作的数据源。

### 选中状态管理
记录当前被选中的节点ID、连线ID，支持可视化编辑的单选操作。

### 撤销/重做机制
通过历史栈、未来栈分别存储操作历史与回退记录，实现流程编辑的撤销与重做功能。
