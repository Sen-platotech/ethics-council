# Ethics Council — 多智能体科研伦理审查系统
**Multi-Agent Research Ethics Review System**

<div align="center">

[English](#english) | [中文](#中文)

</div>

---

<a id="english"></a>
## English

### What is this?

**Ethics Council** transforms the multi-LLM roundtable concept into a **structured, domain-aware ethics review pipeline** for research projects. Instead of asking a vague question to a group of models and getting free-form opinions, this system routes projects through specialized "expert" agents, runs cross-validation within each domain, facilitates cross-domain discussion, and synthesizes a formal ethics review opinion with prioritized action items.

### How it works (4-Stage Pipeline)

```
Project Material
  ↓
Stage 0: Routing — Select relevant experts and form cross-domain clusters
  ↓
Stage 1: Domain Review — Each expert runs cross-validation with 2-3 LLMs
         (First-pass → Cross-check → Merge summary)
  ↓
Stage 2: Context Discussion — Experts in the same cluster discuss cross-domain
         risks in multiple rounds with early stopping on consensus
  ↓
Stage 3: Chairman Synthesis — Compiles all domain summaries + discussions into
         a final ethics opinion (approved / conditional / rejected)
  ↓
Output: Structured JSON review with P0/P1/P2 priority actions
```

### Key Advantages

| Feature | Ethics Council | Typical multi-LLM roundtables |
|---------|---------------|------------------------------|
| **Structure** | 4-stage domain-specific pipeline | Single-round Q&A or basic voting |
| **Expertise** | Domain presets (life-sciences, AI ethics, etc.) with tailored prompts | Generic system prompts |
| **Validation** | 2-3 LLMs cross-check each domain to reduce single-model bias | One model = one vote |
| **Cross-domain** | Structured cross-domain risk discussion between clusters | No inter-model collaboration beyond ranking |
| **Output** | Formal JSON opinion with priority actions (P0/P1/P2) | Free-form text synthesis |
| **Offline testing** | Built-in stub LLM — run end-to-end without API keys | Requires live API access |

### Improvements over the original LLM Council

The original [karpathy/llm-council](https://github.com/karpathy/llm-council) was a 3-stage general-purpose roundtable:
1. Collect individual answers
2. Anonymous peer ranking
3. Chairman synthesis

**Ethics Council optimizes this architecture for regulated, high-stakes review workflows:**

- **Added Stage 0 (Routing)** — Instead of firing every model for every query, the router intelligently selects only relevant domain experts based on project flags and content. This saves cost and improves focus.
- **Upgraded Stage 1 (Cross-Validation)** — Replaced single-opinion responses with a rigorous in-domain review: LLM-A produces a first-pass review, LLM-B cross-checks it for missed risks and severity adjustments, and a final merge step synthesizes the domain summary. This catches errors that a single model would miss.
- **New Stage 2 (Context Discussion)** — Introduces multi-round, cluster-based cross-domain deliberation. Experts whose domains intersect (e.g. gene editing + biosafety) discuss shared risks and supplement each other's recommendations. This addresses the "blind spots" of isolated domain reviews.
- **Enhanced Stage 3 (Chairman Opinion)** — The chairman now outputs a structured ethics review document with explicit `overall_conclusion`, `domain_assessments`, `cross_domain_findings`, `unresolved_divergences`, and `priority_actions` (P0 = must fix, P1 = strongly recommended, P2 = suggested). This is actionable for real IRB/ethics committees rather than just a readable summary.
- **Preset Packages** — Experts, review dimensions, regulatory knowledge, trigger conditions, and cross-domain templates are all packaged as reusable YAML presets. You don't need to re-engineer prompts for every new project type.

---

## Complete Usage Guide

### 1. Installation

**Python dependencies**
```bash
pip install pyyaml jinja2 pydantic fastapi uvicorn httpx
```

For real LLM providers, install the corresponding SDK:
```bash
# Anthropic
pip install anthropic

# OpenAI or OpenAI-compatible services
pip install openai
```

**Frontend dependencies**
```bash
cd frontend && npm install && cd ..
```

### 2. Configuration (Stub vs Real LLM)

By default the system runs in **stub mode** (offline, no API key, deterministic fake outputs). This is great for testing and CI.

To switch to **real LLMs**, you have two options:

#### Option A: Edit `config/defaults.yaml`
Change `models.api_provider` to one of: `openrouter`, `anthropic`, `openai_compatible`.

```yaml
models:
  api_provider: "openrouter"   # or anthropic / openai_compatible
  router_model: "anthropic/claude-opus-4-6"
  chairman_model: "anthropic/claude-opus-4-6"
  default_review_models:
    - "anthropic/claude-sonnet-4-6"
    - "openai/gpt-5.1"
```

#### Option B: Environment variable override
```bash
export ETHICS_COUNCIL_LLM=stub      # force stub
export ETHICS_COUNCIL_LLM=real      # use whatever is in config
```

#### API Keys
Create a `.env` file in the project root (or export in your shell):

```bash
# OpenRouter
OPENROUTER_API_KEY=sk-or-v1-...

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# OpenAI / OpenAI-compatible
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1   # optional, for custom endpoints
```

### 3. Run the Web Application

```bash
./start.sh
```

This starts:
- Backend at http://localhost:8001
- Frontend at http://localhost:5173

**Usage flow in the UI:**
1. **Submit Project** — Fill in the structured form (title, PI, description, methodology, and flags like "involves human subjects").
2. **Expert Selection** — Review the Stage 0 routing results. See which experts were selected, why, and the proposed cross-domain clusters. You can manually toggle expert selection before confirming.
3. **Review Progress** — Watch the real-time SSE stream as Stage 1-3 run. Each expert's cross-validation and each cluster's discussion are shown with expandable details.
4. **Final Report** — View the chairman's structured opinion, download the full JSON, or inspect the raw deliberation log.

### 4. Use the REST API

All endpoints return JSON. Storage is local JSON files in `data/reviews/`.

#### List presets
```bash
curl http://localhost:8001/api/presets
```

#### Submit a project (runs Stage 0 routing)
```bash
curl -X POST http://localhost:8001/api/reviews \
  -H "Content-Type: application/json" \
  -d '{
    "project_material": {
      "project_title": "CRISPR Gene Therapy Preclinical Study",
      "principal_investigator": "Dr. Zhang",
      "research_description": "Using CRISPR-Cas9 to treat sickle cell disease in mouse models.",
      "methodology": " Lentiviral delivery of CRISPR components into hematopoietic stem cells.",
      "involves_gene_editing": true,
      "involves_animals": true
    },
    "preset": "life-sciences"
  }'
```
Response includes `review_id` and the `_routing` result.

#### Confirm and run full review (sync)
```bash
curl -X POST http://localhost:8001/api/reviews/{review_id}/confirm \
  -H "Content-Type: application/json" \
  -d '{
    "experts_selected": [{"id": "gene_editing", "name": "...", "reason": "..."}],
    "context_clusters": [{"topic": "...", "participants": ["..."], "reason": "..."}]
  }'
```

#### Confirm and run full review (SSE streaming)
```bash
curl -X POST http://localhost:8001/api/reviews/{review_id}/confirm/stream \
  -H "Content-Type: application/json" \
  -d '{
    "experts_selected": [...],
    "context_clusters": [...]
  }'
```
Events are streamed as `data: {...}\n\n` lines.

#### List all reviews
```bash
curl http://localhost:8001/api/reviews
```

#### Get a single review
```bash
curl http://localhost:8001/api/reviews/{review_id}
```

#### Delete a review
```bash
curl -X DELETE http://localhost:8001/api/reviews/{review_id}
```

### 5. Use the CLI

```bash
# Stub mode (default)
python3 main.py examples/example_project_genomics.json --preset life-sciences

# Real LLM via OpenRouter
export OPENROUTER_API_KEY=sk-or-v1-...
python3 main.py examples/example_project_genomics.json --preset life-sciences --provider openrouter

# Save output to file
python3 main.py examples/example_project_genomics.json --preset ai-ethics -o result.json
```

### 6. Interpreting the Output

The final JSON contains:

| Field | Meaning |
|-------|---------|
| `project_name` | Project title extracted from input |
| `risk_level` | `standard` / `elevated` / `high` |
| `overall_conclusion` | `approved` / `conditional` / `rejected` |
| `conclusion_rationale` | Human-readable reasoning for the conclusion |
| `domain_assessments` | Array of per-domain evaluations with key risks and recommendations |
| `cross_domain_findings` | Risks that emerge only at the intersection of multiple domains |
| `unresolved_divergences` | Disagreements between domains that the chairman notes but does not override |
| `priority_actions` | Actionable items tagged P0 (must fix), P1 (strongly recommended), P2 (suggested) |
| `chairman_notes` | Free-form executive summary from the chairman |
| `_deliberation_log` | Full raw outputs from Stage 1 and Stage 2 for auditability |
| `_routing` | Stage 0 output: which experts were selected and why |

### 7. Adding a Custom Preset or Expert

**Add a new preset folder:**
```
presets/my-domain/
├── preset.yaml
├── experts/
│   ├── expert_a.yaml
│   └── expert_b.yaml
└── cross_domain_templates.yaml
```

Copy any existing preset (e.g. `ai-ethics`) as a template and modify:
- `experts/*.yaml` — define the expert's review dimensions, regulatory knowledge, trigger conditions, and `system_prompt`
- `cross_domain_templates.yaml` — define which experts should discuss cross-domain topics together
- `preset.yaml` — metadata and the list of expert files to load

No code changes are required. The preset will appear automatically in `/api/presets` and the CLI/UI.

### 8. Troubleshooting

| Problem | Solution |
|---------|----------|
| `NotImplementedError` from LLM client | Make sure you installed the right SDK (`anthropic` or `openai`) and set the API key. |
| Stub always returns fake JSON even with provider set | Check if `ETHICS_COUNCIL_LLM=stub` is exported in your environment. Unset it. |
| Backend says preset not found | Verify `presets_dir` path. Presets must contain `preset.yaml` and at least one expert YAML. |
| Frontend can't connect to backend | Check CORS origins in `backend/main.py` and ensure backend is running on port 8001. |
| JSON parse errors from real LLM | Lower `temperature` in config (0.2-0.3). Some models are more reliable with structured JSON at low temp. |
| Stage 3 misdetected in stub mode | This was fixed. If you see it on a custom branch, ensure Stage 3 is checked first in `engine/llm_client.py` because it embeds earlier-stage JSON. |

---

## Presets

| Preset | Domain | Experts | Typical Use Case |
|--------|--------|---------|------------------|
| `life-sciences` | Life Sciences | 8 | Gene editing, animal trials, biosafety |
| `ai-ethics` | AI Ethics | 6 | Medical AI, algorithmic fairness |
| `social-science` | Social Science | 6 | Surveys, vulnerable populations |
| `clinical-trial` | Clinical Trial | 6 | Drug trials, medical devices |

## Tech Stack

- **Engine**: Python 3.10+, asyncio, Pydantic v2, Jinja2
- **Backend**: FastAPI, Server-Sent Events (SSE)
- **Frontend**: React + Vite
- **Storage**: JSON files (`data/reviews/`)

---

<a id="中文"></a>
## 中文

### 项目简介

**Ethics Council（伦理委员会）** 将多 LLM 圆桌讨论的概念升级为面向科研项目的**结构化、领域感知的伦理审查流水线**。它不再是对一组模型提出模糊问题并收集自由格式的回答，而是让项目材料经过专门的"领域专家" agent、在域内进行多模型交叉验证、在跨域议题簇中进行结构化讨论，最终由主席 agent 输出一份带优先级行动项的正式伦理审查意见书。

### 核心原理（4 阶段流水线）

```
项目材料
  ↓
Stage 0: 路由 — 根据项目特征智能选择相关专家，生成交叉议题簇
  ↓
Stage 1: 域内审查 — 每位专家由 2-3 个 LLM 进行交叉验证
         （首审意见 → 交叉检查 → 合并摘要）
  ↓
Stage 2: 跨域讨论 — 同一议题簇内的专家进行多轮讨论
         识别交叉风险、补充建议，达成共识可提前终止
  ↓
Stage 3: 主席综合 — 汇总所有域内摘要与跨域讨论结果
         生成最终伦理审查意见书（通过 / 附条件 / 不通过）
  ↓
输出: 结构化 JSON 审查意见（含 P0/P1/P2 优先级行动项）
```

### 相比其他多 LLM 方案的优势

| 特性 | Ethics Council | 一般多 LLM 圆桌 |
|------|----------------|----------------|
| **结构** | 4 阶段领域专属流水线 | 单轮问答或简单投票 |
| **专业性** | 开箱即用的领域预设包，含定制 prompt 与法规库 | 通用系统提示 |
| **验证机制** | 每领域 2-3 个 LLM 交叉审查，降低单模型偏差 | 一模型一票 |
| **跨域协作** | 结构化跨域风险讨论与建议补充 | 除投票/排序外无实质协作 |
| **输出形式** | 正式 JSON 意见书，含 P0/P1/P2 优先级行动项 | 自由文本综合 |
| **离线测试** | 内置 Stub LLM，无需 API Key 即可端到端运行 | 必须调用真实 API |

### 对比原 LLM Council 的优化

原项目 [karpathy/llm-council](https://github.com/karpathy/llm-council) 是一个 3 阶段通用问答圆桌：
1. 收集各模型独立回答
2. 匿名互评排序
3. 主席综合最终答案

**Ethics Council 针对受监管、高风险的审查场景做了深度改造：**

- **新增 Stage 0（智能路由）** — 不再对每个查询调用所有模型，而是根据项目标志词和内容只选择相关的领域专家。既节省成本，又提升聚焦度。
- **升级 Stage 1（交叉验证）** — 将原来的"单轮回答"改为严格的域内审查流程：LLM-A 出具首审意见，LLM-B 对其进行交叉检查（查漏补缺、调整严重等级），最后由合并步骤生成领域摘要。这能捕获单一模型容易遗漏的风险。
- **新增 Stage 2（跨域讨论）** — 引入基于议题簇的多轮跨域协商。领域存在交叉的专家（如基因编辑 + 生物安全）共同讨论共享风险、互相补充建议，解决孤立审查的"盲区"问题。
- **强化 Stage 3（主席意见书）** — 主席不再只是生成一段可读摘要，而是输出结构化的伦理审查文档：明确给出 `overall_conclusion`（整体结论）、`domain_assessments`（各领域评估）、`cross_domain_findings`（跨域发现）、`unresolved_divergences`（未解决分歧）以及 `priority_actions`（P0=必须修改否则不通过；P1=强烈建议；P2=建议）。这对真实的 IRB / 伦理委员会而言是可落地的。
- **领域预设包** — 专家定义、审查维度、法规知识、触发条件、跨域模板全部打包为可复用的 YAML 预设。无需为每个新项目重新设计 prompt。

---

## 完整使用教程

### 1. 安装依赖

**Python 依赖**
```bash
pip install pyyaml jinja2 pydantic fastapi uvicorn httpx
```

若使用真实 LLM，需额外安装对应 SDK：
```bash
# Anthropic
pip install anthropic

# OpenAI 或兼容服务
pip install openai
```

**前端依赖**
```bash
cd frontend && npm install && cd ..
```

### 2. 配置：Stub 模式 vs 真实 LLM

系统默认运行在 **Stub 模式**（离线、无需 API Key、返回确定性假数据），适合测试和 CI。

要切换到 **真实 LLM**，有两种方式：

#### 方式 A：修改 `config/defaults.yaml`
将 `models.api_provider` 改为 `openrouter`、`anthropic` 或 `openai_compatible`：

```yaml
models:
  api_provider: "openrouter"   # 或 anthropic / openai_compatible
  router_model: "anthropic/claude-opus-4-6"
  chairman_model: "anthropic/claude-opus-4-6"
  default_review_models:
    - "anthropic/claude-sonnet-4-6"
    - "openai/gpt-5.1"
```

#### 方式 B：环境变量强制覆盖
```bash
export ETHICS_COUNCIL_LLM=stub      # 强制使用 stub
export ETHICS_COUNCIL_LLM=real      # 使用配置文件中指定的 provider
```

#### API Key 配置
在项目根目录创建 `.env` 文件（或在 shell 中 export）：

```bash
# OpenRouter
OPENROUTER_API_KEY=sk-or-v1-...

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# OpenAI / 兼容服务商
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1   # 可选，用于自定义端点
```

### 3. 运行 Web 应用

```bash
./start.sh
```

启动后：
- 后端地址：http://localhost:8001
- 前端地址：http://localhost:5173

**Web 端使用流程：**
1. **提交项目** — 填写结构化表单（项目名称、负责人、研究描述、方法学，以及是否涉及人类受试者、基因编辑等 9 个标志位）。
2. **专家选择** — 查看 Stage 0 路由结果，包括入选专家、推荐理由、风险等级、跨域议题簇。可手动调整专家勾选后确认。
3. **审查进度** — 通过 SSE 实时流观看 Stage 1-3 的执行过程。每个专家的交叉验证细节、每个议题簇的讨论结果都可展开查看。
4. **最终报告** — 查看主席生成的结构化意见书，可下载完整 JSON 或查看原始审议日志。

### 4. 使用 REST API

#### 查看所有预设
```bash
curl http://localhost:8001/api/presets
```

#### 提交项目（执行 Stage 0 路由）
```bash
curl -X POST http://localhost:8001/api/reviews \
  -H "Content-Type: application/json" \
  -d '{
    "project_material": {
      "project_title": "基于CRISPR-Cas9的基因治疗临床前研究",
      "principal_investigator": "张博士",
      "research_description": "利用CRISPR-Cas9治疗镰状细胞贫血症的小鼠模型研究。",
      "methodology": "通过慢病毒载体递送CRISPR组件至造血干细胞。",
      "involves_gene_editing": true,
      "involves_animals": true
    },
    "preset": "life-sciences"
  }'
```
返回包含 `review_id` 和 `_routing` 路由结果。

#### 确认并运行完整审查（同步接口）
```bash
curl -X POST http://localhost:8001/api/reviews/{review_id}/confirm \
  -H "Content-Type: application/json" \
  -d '{
    "experts_selected": [{"id": "gene_editing", "name": "...", "reason": "..."}],
    "context_clusters": [{"topic": "...", "participants": ["..."], "reason": "..."}]
  }'
```

#### 确认并运行完整审查（SSE 流式接口，推荐）
```bash
curl -X POST http://localhost:8001/api/reviews/{review_id}/confirm/stream \
  -H "Content-Type: application/json" \
  -d '{
    "experts_selected": [...],
    "context_clusters": [...]
  }'
```
事件以 `data: {...}\n\n` 格式逐行推送。

#### 列出所有审查记录
```bash
curl http://localhost:8001/api/reviews
```

#### 获取单条审查详情
```bash
curl http://localhost:8001/api/reviews/{review_id}
```

#### 删除审查记录
```bash
curl -X DELETE http://localhost:8001/api/reviews/{review_id}
```

### 5. 使用 CLI

```bash
# 默认 stub 模式
python3 main.py examples/example_project_genomics.json --preset life-sciences

# 使用 OpenRouter 真实模型
export OPENROUTER_API_KEY=sk-or-v1-...
python3 main.py examples/example_project_genomics.json --preset life-sciences --provider openrouter

# 输出到文件
python3 main.py examples/example_project_genomics.json --preset ai-ethics -o result.json
```

### 6. 如何解读输出 JSON

最终报告 JSON 包含以下关键字段：

| 字段 | 含义 |
|------|------|
| `project_name` | 从输入提取的项目名称 |
| `risk_level` | 风险等级：`standard`（标准）/ `elevated`（升高）/ `high`（高） |
| `overall_conclusion` | 整体结论：`approved`（通过）/ `conditional`（附条件）/ `rejected`（不通过） |
| `conclusion_rationale` | 结论理由的自然语言说明 |
| `domain_assessments` | 各领域的评估详情，含关键风险点与建议 |
| `cross_domain_findings` | 仅在多领域交叉处浮现的风险与建议 |
| `unresolved_divergences` | 各领域之间的分歧，主席记录但不强行消除 |
| `priority_actions` | 优先级行动项：P0=必须修改，P1=强烈建议，P2=建议 |
| `chairman_notes` | 主席的自由格式综合评语 |
| `_deliberation_log` | Stage 1 和 Stage 2 的完整原始输出，可供审计回溯 |
| `_routing` | Stage 0 输出：入选专家、未入选专家、风险标记 |

### 7. 添加自定义预设或专家

**新建预设目录结构：**
```
presets/my-domain/
├── preset.yaml
├── experts/
│   ├── expert_a.yaml
│   └── expert_b.yaml
└── cross_domain_templates.yaml
```

复制任意现有预设（如 `ai-ethics`）作为模板，然后修改：
- `experts/*.yaml` — 定义专家的审查维度、法规知识、触发条件、`system_prompt`
- `cross_domain_templates.yaml` — 定义哪些专家应就哪些跨域议题进行讨论
- `preset.yaml` — 元数据与专家文件列表

**无需修改任何代码**。新预设会自动出现在 `/api/presets`、CLI 和前端下拉框中。

### 8. 常见问题排查

| 问题 | 解决方案 |
|------|----------|
| LLM client 报 `NotImplementedError` | 请安装对应 SDK（`anthropic` 或 `openai`）并正确设置 API Key。 |
| 已配置真实 provider 但仍返回 stub 数据 | 检查是否误设了 `ETHICS_COUNCIL_LLM=stub` 环境变量，取消 export 即可。 |
| 后端提示 preset 找不到 | 检查 `presets_dir` 路径，确保预设目录下包含 `preset.yaml` 和至少一个专家 YAML。 |
| 前端无法连接后端 | 检查 `backend/main.py` 中的 CORS 配置，确保后端已启动在 8001 端口。 |
| 真实 LLM 返回的 JSON 解析失败 | 降低 `temperature` 至 0.2-0.3，低温下模型输出结构化 JSON 更稳定。 |
| Stage 3 stub 被误识别为 Stage 1 | 已修复。若自定义分支遇到类似问题，请在 `engine/llm_client.py` 中确保 Stage 3 优先检测，因为它的 prompt 嵌入了前面阶段的 JSON。 |

---

## 预设包一览

| 预设 | 领域 | 专家数 | 典型场景 |
|------|------|--------|----------|
| `life-sciences` | 生命科学 | 8 | 基因编辑、动物实验、生物安全 |
| `ai-ethics` | AI 伦理 | 6 | 医疗 AI 部署、算法公平性 |
| `social-science` | 社会科学 | 6 | 问卷调查、弱势群体研究 |
| `clinical-trial` | 临床试验 | 6 | 药物试验、医疗器械 |

## 技术栈

- **引擎层**：Python 3.10+, asyncio, Pydantic v2, Jinja2
- **后端**：FastAPI, SSE (Server-Sent Events) 实时流式进度
- **前端**：React + Vite
- **存储**：JSON 文件（`data/reviews/`）

---

**License**: Provided as-is for inspiration and research use.
