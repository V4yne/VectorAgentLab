# VectorAgentLab

VectorAgentLab 是一个面向学习和实践的 Agent 框架项目。

当前阶段的目标不是一次性写出完整框架，而是先把代码仓库的结构、模块边界和演进路线设计清楚。后续可以按照章节逐步实现 Simple Agent、Tool Agent、ReAct Agent、Memory Agent、RAG Agent、Multi-Agent 等能力。

Python 包名为 `vector_agent_lab`。

## 项目目标

这个仓库希望帮助学习者理解一个 Agent 框架从 0 到 1 应该如何设计：

- 如何抽象 Agent、LLM、Message、Tool、Memory 等核心对象
- 如何让不同模型、不同工具、不同 Agent 策略可以自由组合
- 如何从简单问答逐步演进到工具调用、任务规划、记忆检索和多 Agent 协作
- 如何补齐开源框架需要的安全、观测、评测和测试能力

## 目录结构

```text
VectorAgentLab/
├── README.md
├── LICENSE
├── pyproject.toml
├── .gitignore
├── docs/
│   ├── architecture.md          # 架构设计说明
│   └── roadmap.md               # 实现路线
└── vector_agent_lab/
    ├── core/                    # 核心框架层
    │   ├── agent.py             # Agent 基类
    │   ├── llm.py               # LLM 统一接口
    │   ├── message.py           # 消息协议
    │   ├── prompt.py            # Prompt 模板
    │   ├── context.py           # 运行上下文
    │   ├── state.py             # Agent 状态
    │   ├── result.py            # 执行结果
    │   ├── config.py            # 配置管理
    │   └── exceptions.py        # 异常体系
    │
    ├── agents/                  # Agent 实现层
    │   ├── simple_agent.py      # 简单问答 Agent
    │   ├── react_agent.py       # ReAct Agent
    │   ├── reflection_agent.py  # 反思 Agent
    │   ├── plan_solve_agent.py  # 计划-执行 Agent
    │   ├── tool_agent.py        # 工具调用 Agent
    │   └── multi_agent.py       # 多 Agent 协作
    │
    ├── models/                  # 模型适配层
    │   ├── openai.py
    │   ├── anthropic.py
    │   ├── ollama.py
    │   └── mock.py
    │
    ├── tools/                   # 工具系统层
    │   ├── base.py              # Tool 基类
    │   ├── registry.py          # 工具注册中心
    │   ├── executor.py          # 工具执行器
    │   ├── schema.py            # 工具参数 Schema
    │   └── builtin/
    │       ├── calculator.py    # 计算工具
    │       ├── search.py        # 搜索工具
    │       ├── file.py          # 文件工具
    │       └── python_repl.py   # Python 执行工具
    │
    ├── memory/                  # 记忆系统
    │   ├── base.py
    │   ├── short_term.py        # 短期上下文记忆
    │   ├── long_term.py         # 长期记忆
    │   ├── vector_store.py      # 向量检索
    │   └── summarizer.py        # 对话压缩
    │
    ├── planning/                # 规划与任务分解
    │   ├── planner.py
    │   ├── task.py
    │   ├── step.py
    │   └── scheduler.py
    │
    ├── runtime/                 # 运行时与编排
    │   ├── runner.py            # Agent 执行入口
    │   ├── loop.py              # Agent 循环
    │   ├── events.py            # 事件流
    │   ├── callbacks.py         # 回调机制
    │   └── async_runner.py      # 异步运行
    │
    ├── guardrails/              # 安全与约束
    │   ├── input_filter.py
    │   ├── output_validator.py
    │   ├── permission.py
    │   └── policy.py
    │
    ├── observability/           # 观测与调试
    │   ├── logger.py
    │   ├── tracer.py
    │   ├── token_counter.py
    │   └── run_recorder.py
    │
    ├── evaluation/              # 测试与评测
    │   ├── dataset.py
    │   ├── evaluator.py
    │   ├── metrics.py
    │   └── regression.py
    │
    ├── examples/                # 示例
    │   ├── simple_chat.py
    │   ├── react_with_tools.py
    │   ├── rag_agent.py
    │   └── multi_agent_demo.py
    │
    └── tests/
```

## 文档导航

- [架构设计](docs/architecture.md)：说明 `vector_agent_lab/` 下每个子目录是什么模块、负责什么内容、为什么需要它。
- [实现路线](docs/roadmap.md)：说明后续应该按照什么顺序逐步实现这个 Agent 框架。

## 分层总览

这个项目大致分为三层：

- 核心抽象层：`core/`
- Agent 能力层：`agents/`、`models/`、`tools/`、`memory/`、`planning/`、`runtime/`
- 工程化支撑层：`guardrails/`、`observability/`、`evaluation/`、`tests/`

更详细的模块说明见 [docs/architecture.md](docs/architecture.md)。

## 当前状态

当前仓库只建立架构骨架，不追求功能完整实现。

每个模块文件会先保留职责说明，后续再逐章补充真正的代码。

## 开发环境

```bash
python -m pip install -e ".[dev]"
```

当前建议使用 Python 3.9 或更高版本。

测试会在核心接口开始实现后逐步补充。
