# Ethics Council — 多智能体科研伦理审查系统

基于 [karpathy/llm-council](https://github.com/karpathy/llm-council) 架构，将多 LLM 协商机制应用于科研伦理审查领域。多个领域专家 agent 对研究项目进行结构化审查，通过交叉验证与跨域讨论产出最终伦理审查意见书。

## 核心特性

- **4 阶段异步流水线**：路由 → 域内交叉验证 → 跨域讨论 → 主席综合
- **领域预设包**：生命科学（8 专家）、AI 伦理（6）、社会科学（6）、临床试验（6）
- **多模型交叉验证**：每个专家域内由 2-3 个 LLM 交叉审查，减少单模型偏差
- **离线 Stub 模式**：无需 API Key 即可端到端运行全流程
- **Web UI**：4 步向导界面，SSE 实时进度推送

## 快速开始

### 安装依赖

```bash
pip install pyyaml jinja2 pydantic
```

### CLI 运行（Stub 模式）

```bash
# 生命科学 - 基因编辑项目审查
python3 main.py examples/example_project_genomics.json --preset life-sciences

# AI 伦理 - 医疗 AI 项目审查
python3 main.py examples/example_project_ai.json --preset ai-ethics

# 输出到文件
python3 main.py examples/example_project_genomics.json -o review_result.json
```

### Web 应用

```bash
# 安装前端依赖
cd frontend && npm install && cd ..

# 安装后端依赖
pip install fastapi uvicorn

# 启动（后端 :8001，前端 :5173）
./start.sh
```

浏览器打开 http://localhost:5173

### 运行测试

```bash
python3 tests/test_smoke.py
```

## 流水线架构

```
项目材料
  ↓
Stage 0: 路由 — 根据项目标志词和内容选择相关专家、生成跨域议题簇
  ↓
Stage 1: 域内审查 — 每位专家由 2-3 个 LLM 交叉验证（首审→交叉检查→合并摘要）
  ↓
Stage 2: 跨域讨论 — 同一议题簇内专家多轮讨论交叉风险，达成共识可提前终止
  ↓
Stage 3: 主席综合 — 汇总所有域内摘要 + 跨域讨论，生成最终伦理审查意见书
  ↓
输出: JSON 格式审查意见（含优先级行动项 P0/P1/P2）
```

## 预设一览

| 预设 | 领域 | 专家数 | 适用场景 |
|------|------|--------|----------|
| `life-sciences` | 生命科学 | 8 | 基因编辑、动物实验、生物安全 |
| `ai-ethics` | AI 伦理 | 6 | AI 系统部署、算法公平性 |
| `social-science` | 社会科学 | 6 | 问卷调查、弱势群体研究 |
| `clinical-trial` | 临床试验 | 6 | 药物试验、医疗器械 |

## 使用真实 LLM

默认使用 Stub（离线模式）。要接入真实 LLM：

1. 在 `config/council_config.yaml` 中设置 `models.api_provider` 为 `openrouter`、`anthropic` 或 `openai_compatible`
2. 实现 `engine/llm_client.py` 中对应 provider 类的 `query()` 方法
3. 设置对应的 API Key 环境变量

## 项目结构

```
ethics-council/
├── config/              # 配置层（Pydantic schema + YAML loader）
├── engine/              # 引擎层（pipeline, router, domain_review, chairman, llm_client）
├── prompts/             # Jinja2 提示词模板（Stage 0-3）
├── presets/             # 领域预设包（专家定义 + 跨域模板）
├── schemas/             # JSON Schema（IO 契约）
├── examples/            # 示例项目材料
├── tests/               # 冒烟测试
├── backend/             # FastAPI 后端
├── frontend/            # React + Vite 前端
└── main.py              # CLI 入口
```

## 技术栈

- **引擎**：Python 3.10+, asyncio, Pydantic v2, Jinja2
- **后端**：FastAPI, SSE (Server-Sent Events)
- **前端**：React, Vite
- **存储**：JSON 文件（`data/reviews/`）
