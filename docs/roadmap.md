# VectorAgentLab Roadmap

这份文档记录 VectorAgentLab 的建议实现路线。

当前目标是按照学习顺序逐步实现 Agent 框架，而不是一开始就追求完整生产级能力。

## 阶段 0：仓库骨架

目标：建立清晰的项目结构和文档。

主要内容：

- 创建 `vector_agent_lab/` 包结构。
- 创建 `README.md`。
- 创建 `docs/architecture.md`。
- 创建 `docs/roadmap.md`。
- 创建 `pyproject.toml`、`.gitignore`、`LICENSE`。

完成标准：

- 目录职责清楚。
- 没有提前写复杂实现。
- 后续每个章节都能找到对应文件。

## 阶段 1：核心抽象

目标：定义 Agent 框架最小可用的核心协议。

建议实现：

- `core.message.Message`
- `core.llm.BaseLLM`
- `core.agent.BaseAgent`
- `core.context.AgentContext`
- `core.result.AgentResult`
- `core.config.AgentConfig`
- `models.mock.MockLLM`
- `agents.simple_agent.SimpleAgent`

完成标准：

- 可以用 Mock 模型跑一个最简单的 Agent。
- 所有 Agent 返回统一的 `AgentResult`。
- 消息格式不再只是普通字符串。

## 阶段 2：工具系统

目标：让 Agent 具备调用工具的能力。

建议实现：

- `tools.base.BaseTool`
- `tools.base.ToolResult`
- `tools.schema.ToolSchema`
- `tools.registry.ToolRegistry`
- `tools.executor.ToolExecutor`
- `tools.builtin.calculator.CalculatorTool`
- `agents.tool_agent.ToolAgent`

完成标准：

- 工具可以注册、查找和执行。
- 工具执行结果有统一格式。
- Agent 可以根据工具列表组织提示词。

## 阶段 3：ReAct Agent

目标：实现 Reason-Act-Observe 循环。

建议实现：

- `agents.react_agent.ReActAgent`
- `runtime.loop.AgentLoop`
- `runtime.events.Event`
- `runtime.callbacks.CallbackManager`

完成标准：

- Agent 可以多步推理。
- Agent 可以选择工具、观察结果、继续推理。
- 运行过程可以被事件记录。

## 阶段 3.5：本地 Web 测试台

目标：提供一个浏览器聊天页面，方便测试当前 Agent、tools 和多轮对话行为。

建议实现：

- `web.app` FastAPI 服务入口。
- `web.agent_factory` 组装 `SimpleAgent` 和本地 tools。
- `web.static` 浏览器聊天界面。
- `start.sh` 和 `stop.sh` 一键启动/停止本地服务。

完成标准：

- 可以通过浏览器访问本地聊天页面。
- 页面可以和 `SimpleAgent` 进行多轮对话。
- Web 模块不改变 `core/`、`agents/`、`tools/` 的核心设计。

## 阶段 3.6：对话持久化

目标：让本地 Web 测试台可以保存并恢复历史话题。

建议实现：

- `storage.base.ConversationStore`
- `storage.models.Conversation`
- `storage.models.StoredMessage`
- `storage.models.StoredTraceEvent`
- `storage.sqlite.SQLiteConversationStore`
- Web 侧话题列表、历史消息加载和最近一次 Trace 恢复

完成标准：

- 刷新页面后仍然能看到之前聊过的话题。
- 点击某个话题后，可以看到该话题里的上下文消息。
- 重启 Web 服务后，本地 SQLite 中的历史话题仍然存在。

## 阶段 4：记忆系统

目标：让 Agent 能够利用历史上下文和外部知识。

建议实现：

- `memory.base.BaseMemory`
- `memory.short_term.ShortTermMemory`
- `memory.long_term.LongTermMemory`
- `memory.vector_store.VectorStoreMemory`
- `memory.summarizer.ConversationSummarizer`

完成标准：

- Agent 可以读取短期对话历史。
- Agent 可以保存和查询长期记忆。
- 长对话可以被压缩成摘要。

## 阶段 5：RAG Agent

目标：加入检索增强生成能力。

建议实现：

- 向量检索接口。
- 文档切分与索引流程。
- 基于 Memory 或 VectorStore 的检索流程。
- `examples/rag_agent.py` 示例。

完成标准：

- 用户问题可以触发相关知识检索。
- Agent 回答时可以引用检索到的上下文。
- RAG 示例能清楚展示数据流。

## 阶段 6：规划系统

目标：支持复杂任务拆解和分步执行。

建议实现：

- `planning.task.Task`
- `planning.step.PlanStep`
- `planning.planner.Planner`
- `planning.scheduler.Scheduler`
- `agents.plan_solve_agent.PlanAndSolveAgent`

完成标准：

- Agent 可以先生成计划。
- Agent 可以按步骤执行计划。
- 每个步骤有状态和结果。

## 阶段 7：反思与自我修正

目标：让 Agent 能对自己的输出进行检查和改进。

建议实现：

- `agents.reflection_agent.ReflectionAgent`
- 输出 critique prompt。
- 修改和重试机制。

完成标准：

- Agent 可以生成初稿。
- Agent 可以检查初稿的问题。
- Agent 可以基于反馈生成修正版。

## 阶段 8：多 Agent 协作

目标：支持多个 Agent 分工完成任务。

建议实现：

- `agents.multi_agent.MultiAgent`
- 协调者 Agent。
- 工作者 Agent。
- 简单的任务分派和结果汇总。

完成标准：

- 多个 Agent 可以分别处理子任务。
- 协调者可以汇总结果。
- 示例能展示协作流程。

## 阶段 9：安全与权限

目标：限制 Agent 的高风险行为。

建议实现：

- `guardrails.input_filter.InputFilter`
- `guardrails.output_validator.OutputValidator`
- `guardrails.permission.PermissionManager`
- `guardrails.policy.Policy`

完成标准：

- 可以限制工具调用权限。
- 可以过滤输入。
- 可以校验输出。

## 阶段 10：观测与评测

目标：让 Agent 行为可解释、可测试、可回归。

建议实现：

- `observability.logger`
- `observability.tracer`
- `observability.token_counter`
- `observability.run_recorder`
- `evaluation.dataset`
- `evaluation.evaluator`
- `evaluation.metrics`
- `evaluation.regression`

完成标准：

- 可以记录每一步模型调用和工具调用。
- 可以统计 token 或成本。
- 可以用数据集评测 Agent 表现。
- 可以做基础回归测试。

## 长期方向

后续可以继续扩展：

- 插件系统。
- 工作流编排。
- Web UI 调试界面。
- 多模型路由。
- 更严格的沙箱执行。
- 与常见向量数据库集成。
- 更完整的 benchmark 和评测报告。
