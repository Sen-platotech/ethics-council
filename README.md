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

### Quick Start

```bash
# Install Python deps
pip install pyyaml jinja2 pydantic

# Run smoke tests (no API key needed)
python3 tests/test_smoke.py

# CLI review
python3 main.py examples/example_project_genomics.json --preset life-sciences

# Web app
pip install fastapi uvicorn
cd frontend && npm install && cd ..
./start.sh   # backend :8001, frontend :5173
```

### Presets

| Preset | Domain | Experts | Typical Use Case |
|--------|--------|---------|------------------|
| `life-sciences` | Life Sciences | 8 | Gene editing, animal trials, biosafety |
| `ai-ethics` | AI Ethics | 6 | Medical AI, algorithmic fairness |
| `social-science` | Social Science | 6 | Surveys, vulnerable populations |
| `clinical-trial` | Clinical Trial | 6 | Drug trials, medical devices |

### Tech Stack

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

### 快速开始

```bash
# 安装 Python 依赖
pip install pyyaml jinja2 pydantic

# 运行冒烟测试（无需 API Key）
python3 tests/test_smoke.py

# CLI 运行审查
python3 main.py examples/example_project_genomics.json --preset life-sciences

# Web 应用
pip install fastapi uvicorn
cd frontend && npm install && cd ..
./start.sh   # 后端 :8001，前端 :5173
```

浏览器打开 http://localhost:5173

### 预设包一览

| 预设 | 领域 | 专家数 | 典型场景 |
|------|------|--------|----------|
| `life-sciences` | 生命科学 | 8 | 基因编辑、动物实验、生物安全 |
| `ai-ethics` | AI 伦理 | 6 | 医疗 AI 部署、算法公平性 |
| `social-science` | 社会科学 | 6 | 问卷调查、弱势群体研究 |
| `clinical-trial` | 临床试验 | 6 | 药物试验、医疗器械 |

### 技术栈

- **引擎层**：Python 3.10+, asyncio, Pydantic v2, Jinja2
- **后端**：FastAPI, SSE (Server-Sent Events) 实时流式进度
- **前端**：React + Vite
- **存储**：JSON 文件（`data/reviews/`）

---

**License**: Provided as-is for inspiration and research use.
