# VectorAgentLab Architecture

这份文档解释 `vector_agent_lab/` 下每个子目录是什么模块、负责什么内容，以及为什么需要它。

当前阶段只定义仓库架构和模块边界，具体代码会在后续学习过程中逐步实现。

## 总体分层

VectorAgentLab 可以分成三层：

```text
核心抽象层
core/

Agent 能力层
agents/
models/
tools/
memory/
planning/
runtime/

工程化支撑层
guardrails/
observability/
evaluation/
tests/
examples/
```

核心抽象层负责定义稳定协议，Agent 能力层负责让 Agent 具备推理、工具、记忆和规划能力，工程化支撑层负责安全、调试、评测和示例。

## core/

`core/` 是整个框架最稳定的基础层。

它负责定义 Agent 框架里最核心的对象和协议：

- `agent.py`：Agent 基类，定义 Agent 应该如何接收输入、执行任务、返回结果。
- `llm.py`：LLM 统一接口，屏蔽不同模型服务商之间的差异。
- `message.py`：消息协议，统一表达 system、user、assistant、tool 等消息。
- `prompt.py`：Prompt 模板，管理可复用的提示词结构。
- `context.py`：运行上下文，保存一次 Agent 运行中的消息、状态和临时数据。
- `state.py`：Agent 状态，记录运行状态、步骤数、中间变量等。
- `result.py`：执行结果，统一 Agent 的输出格式。
- `config.py`：配置管理，保存模型、温度、最大步数等配置。
- `exceptions.py`：异常体系，定义框架级错误类型。

为什么需要这一层：

Agent 框架最重要的是抽象稳定。如果 `Agent`、`LLM`、`Message`、`Tool` 等基础协议没有设计清楚，后续实现 ReAct、RAG、多 Agent 和评测系统时会反复推倒重来。

## agents/

`agents/` 放具体的 Agent 策略实现。

每种 Agent 代表一种不同的任务执行方式：

- `simple_agent.py`：最简单的一次模型调用。
- `tool_agent.py`：能够选择和调用工具的 Agent。
- `react_agent.py`：基于 Reason-Act-Observe 循环的 Agent。
- `reflection_agent.py`：先回答，再反思和修正的 Agent。
- `plan_solve_agent.py`：先规划任务，再逐步执行的 Agent。
- `multi_agent.py`：多个 Agent 分工协作的编排方式。

为什么需要这一层：

“Agent”不是单一模式。简单问答、工具调用、RAG、任务规划和多 Agent 协作适合不同的执行策略。把它们拆到 `agents/` 下，可以让每种策略独立演进。

## models/

`models/` 负责模型适配。

它的目标是让 Agent 不直接依赖某个厂商 API，而是依赖 `core.llm` 里定义的统一接口。

- `openai.py`：OpenAI 或 OpenAI-compatible 模型适配。
- `anthropic.py`：Anthropic 模型适配。
- `ollama.py`：Ollama 本地模型适配。
- `mock.py`：测试和示例用的 Mock 模型。

为什么需要这一层：

Agent 框架应该允许自由切换模型。今天使用 OpenAI，明天换成本地 Ollama 或其他模型，不应该改 Agent 的核心逻辑。

## tools/

`tools/` 是工具系统层。

它负责让 Agent 能够调用外部能力，而不是只生成文本。

- `base.py`：Tool 基类和 ToolResult。
- `registry.py`：工具注册中心，管理可用工具。
- `executor.py`：工具执行器，统一执行工具并处理错误。
- `schema.py`：工具参数 Schema，让模型知道工具需要什么参数。
- `builtin/`：内置工具集合。

`builtin/` 下的工具包括：

- `calculator.py`：计算工具。
- `search.py`：搜索工具。
- `file.py`：文件工具。
- `python_repl.py`：Python 执行工具。

为什么需要这一层：

工具调用是 Agent 从“会说话”走向“能完成任务”的关键。一个好的工具系统需要解决工具描述、参数校验、注册发现、执行错误和权限控制。

## memory/

`memory/` 负责记忆系统。

它让 Agent 可以利用历史信息，而不是每次都从零开始。

- `base.py`：Memory 基类和 MemoryItem。
- `short_term.py`：短期上下文记忆，保存当前对话窗口。
- `long_term.py`：长期记忆，保存跨会话信息。
- `vector_store.py`：向量检索记忆，用 embedding 找相关内容。
- `summarizer.py`：对话压缩，解决上下文过长问题。

为什么需要这一层：

真实 Agent 往往需要记住用户偏好、历史任务、外部知识和之前的执行结果。没有记忆的 Agent 更像一次性问答机器人。

## planning/

`planning/` 负责规划与任务分解。

它处理那些不能一次回答、需要拆步骤执行的复杂任务。

- `planner.py`：规划器，把用户目标拆成计划。
- `task.py`：任务对象，描述用户希望完成的目标。
- `step.py`：计划步骤，表示一个可执行子任务。
- `scheduler.py`：步骤调度器，决定步骤如何执行。

为什么需要这一层：

复杂任务通常需要先理解目标，再拆解步骤，再执行和检查。规划系统是 Agent 从“回答问题”走向“解决任务”的关键。

## runtime/

`runtime/` 负责 Agent 的运行时与编排。

它管理 Agent 真正执行时发生的循环、事件和回调。

- `runner.py`：Agent 执行入口。
- `loop.py`：Agent 循环，用于多步执行。
- `events.py`：事件流，记录运行时发生的关键事件。
- `callbacks.py`：回调机制，让外部系统监听 Agent 运行过程。
- `async_runner.py`：异步运行支持。

为什么需要这一层：

复杂 Agent 不是调用一次模型就结束。ReAct、工具调用和多 Agent 协作都需要稳定的执行循环和运行时事件。

## guardrails/

`guardrails/` 负责安全与约束。

它定义 Agent 能做什么、不能做什么。

- `input_filter.py`：输入过滤。
- `output_validator.py`：输出校验。
- `permission.py`：权限管理。
- `policy.py`：策略组合。

为什么需要这一层：

Agent 一旦可以调用工具、读写文件或执行代码，就必须有边界。Guardrails 负责把能力控制在安全范围内。

## observability/

`observability/` 负责观测与调试。

它帮助开发者理解 Agent 为什么这样行动。

- `logger.py`：日志。
- `tracer.py`：调用链追踪。
- `token_counter.py`：Token 统计。
- `run_recorder.py`：运行记录。

为什么需要这一层：

Agent 调试的难点常常不是代码报错，而是行为不可解释。可观测性模块需要回答：模型调用了几次，工具调用了什么，每一步输入输出是什么，成本花在哪里。

## evaluation/

`evaluation/` 负责测试与评测。

它让 Agent 的表现可以被持续衡量。

- `dataset.py`：评测数据集。
- `evaluator.py`：评测执行器。
- `metrics.py`：评测指标。
- `regression.py`：回归测试。

为什么需要这一层：

Agent 行为具有不确定性。修改 Prompt、模型或工具后，需要用评测判断效果是否真的变好，而不是只靠感觉。

## examples/

`examples/` 放可运行示例。

它面向学习者，展示框架每个阶段应该怎么使用。

- `simple_chat.py`：简单对话示例。
- `react_with_tools.py`：ReAct + 工具示例。
- `rag_agent.py`：RAG Agent 示例。
- `multi_agent_demo.py`：多 Agent 示例。

为什么需要这一层：

开源项目需要示例降低理解成本。每个示例都应该对应一个核心能力，而不是堆砌复杂功能。

## tests/

`tests/` 放测试。

当前阶段先保留占位，等核心接口开始实现后再补充测试。

为什么需要这一层：

Agent 框架的接口会持续演进。测试可以保护核心协议不被无意破坏，也方便后续做回归验证。

## 模块依赖方向

推荐依赖方向如下：

```text
core
  <- models
  <- tools
  <- memory
  <- planning
  <- agents
  <- runtime
  <- guardrails / observability / evaluation
```

基本原则：

- `core/` 尽量不依赖其他业务模块。
- `agents/` 可以组合 `models/`、`tools/`、`memory/`、`planning/`。
- `runtime/` 负责运行编排，不应该塞具体 Agent 策略。
- `evaluation/`、`observability/`、`guardrails/` 是横向能力，可以围绕 Agent 运行过程工作。

