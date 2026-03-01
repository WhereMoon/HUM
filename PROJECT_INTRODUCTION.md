# 拟人数字人陪伴系统 — 项目介绍文档

## 一、整体项目情况

### 1.1 项目概述

**拟人数字人陪伴系统**是一款基于多模型协作的 Web 端数字人陪伴应用。用户通过浏览器与具备性格、情感与记忆的 2D 数字人进行实时对话与语音交互，数字人具备**人格一致性**、**长效记忆**与**人格演化**能力，可随对话逐步调整性格参数，提供更贴近真人陪伴的体验。

- **形态**：Web 应用（前后端分离）
- **交互方式**：文字输入、语音输入（ASR）、语音回复（TTS）、Live2D 形象与表情
- **部署方式**：后端可部署于服务器，前端通过浏览器访问；核心 AI 能力使用阿里云百炼（DashScope）API，无需本地 GPU

### 1.2 项目目标

- 提供**拟人化、情感化**的对话与语音陪伴体验  
- 通过**多 Agent 协作**（统筹 → 执行 → 监督 → 修订）保证回复质量与人设一致  
- 支持**人格演化**：基于对话历史的自动反思，动态更新性格参数  
- 支持**长效记忆**：向量检索历史对话，提升上下文连贯性  
- 提供**实时、低延迟**的文本与语音流式输出，以及 Live2D 口型与表情联动  

### 1.3 系统架构总览

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            Browser (Frontend)                            │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────┐ │
│  │   Live2DStage       │  │   ChatInterface     │  │  WebSocket      │ │
│  │   (PixiJS + Live2D) │  │   (文字/状态展示)   │  │  (全局单连接)   │ │
│  └──────────┬──────────┘  └──────────┬──────────┘  └────────┬────────┘ │
└─────────────┼─────────────────────────┼─────────────────────┼──────────┘
              │                         │                     │
              │  expression/audio        │  text / audio       │  ws://host:8000/ws/{client_id}
              └─────────────────────────┴─────────────────────┘
                                              │
┌─────────────────────────────────────────────┼─────────────────────────────┐
│                    Backend (FastAPI, port 8000)                            │
│  ┌─────────────────────────────────────────▼───────────────────────────┐ │
│  │  WebSocket Handler                                                     │ │
│  │  • 接收 text_input / audio → ASR → 统一进入 process_and_respond       │ │
│  │  • 流式下发：status / text_response / audio_start / audio_chunk /      │ │
│  │    audio_end / error                                                   │ │
│  └─────────────────────────────────────────┬───────────────────────────┘ │
│                                             │                             │
│  ┌─────────────────────────────────────────▼───────────────────────────┐ │
│  │  LangGraph Workflow (agents/workflow.py)                              │ │
│  │  orchestrator → personality → supervisor → [revision] → END           │ │
│  │  • 使用 Qwen 云 API (qwen-turbo) 驱动各节点                            │ │
│  │  • 记忆检索 (ChromaDB)、性格读取/写入 (SQLite)                          │ │
│  └─────────────────────────────────────────┬───────────────────────────┘ │
│                                             │                             │
│  ┌─────────────────────────────────────────▼───────────────────────────┐ │
│  │  TTS (DashScope Sambert) → 流式音频 → WebSocket 二进制下发             │ │
│  │  Reflection Scheduler → 每 N 轮对话触发 perform_reflection            │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                     │
│  │ SQLite       │  │ ChromaDB     │  │ DashScope     │                     │
│  │ personality  │  │ user_memories│  │ Qwen/ASR/TTS │                     │
│  └──────────────┘  └──────────────┘  └──────────────┘                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 二、项目亮点

### 2.1 多模型协作架构（统筹 — 执行 — 监督 — 修订）

- **Orchestrator（统筹）**：分析用户意图，从 ChromaDB 检索相关记忆，结合当前性格参数制定回复策略（语气、重点），不直接生成回复。  
- **Personality（执行）**：根据策略与性格参数（友好度、信任度、心情、能量值、沟通风格等）生成拟人化回复，并做简单情感识别 → 映射到 Live2D 表情。  
- **Supervisor（监督）**：检查回复是否贴合人设、是否自然、是否过于机械或不当；输出 `PASS` 或 `REVISE: 建议`。  
- **Revision（修订）**：仅在需要时执行，根据监督建议修改回复并重新做情感/表情映射。  

通过 LangGraph 编排，保证每条回复都经过策略规划、性格执行与质量把关，避免“机械客服感”。

### 2.2 人格演化（Evolving Personality）

- 性格参数存储在 **SQLite**（`personality_params`）：如友好度、信任度、心情、能量值、幽默风格、沟通风格等。  
- **反思机制**（`agents/reflection.py`）：每隔一定轮次（如每 10 轮对话）或通过 API 手动触发，对近期对话进行总结，由 Qwen 分析用户偏好与情感，输出反思与建议的 JSON 参数调整。  
- 将建议的数值约束在 [0,1] 后写回数据库，并记录到 `reflection_logs`，实现**随对话演进的人格**，而非固定人设。

### 2.3 实时多模态交互

- **文字**：前端发送 `text_input`，后端经完整工作流后返回 `text_response` + 表情，再 TTS 合成语音并流式下发。  
- **语音**：前端上传音频二进制，后端使用阿里云 **ASR（paraformer-realtime-v2）** 转文字，再走同一套工作流与 TTS。  
- **流式体验**：先推送“正在思考”状态，再推送文本与表情，随后 `audio_start` → 多段 `audio_chunk`（WAV）→ `audio_end`，前端用 **AudioContext + 队列** 顺序播放，并可选与口型联动。

### 2.4 长效记忆与 RAG

- **ChromaDB** 存储用户维度的对话摘要与交互片段，采用余弦相似度检索。  
- 每次进入 **Orchestrator** 时，根据当前用户输入做向量检索（如 top 3），将相关记忆注入统筹与执行节点的上下文，使数字人能“记得”过往话题与偏好，提升连贯性与个性化。

### 2.5 Live2D 视觉与兼容性

- 前端使用 **PixiJS 6.5.10** + **pixi-live2d-display (Cubism 4)** 渲染 Live2D 模型。  
- 支持根据回复情感切换表情（如 happy → smile, sad → sad），以及基于 TTS 的口型同步（预留接口与音频幅度处理）。  
- 针对部分环境 WebGL 报告 `MAX_FRAGMENT_UNIFORM_VECTORS === 0` 导致的 Shader 错误，通过 patch `getParameter` 保证兼容性；默认使用 Cubism SDK 示例模型 Haru，可替换为任意 Cubism 3/4 兼容模型（见 `LIVE2D_MODELS.md`）。

### 2.6 工程化与可维护性

- **后端**：FastAPI 异步、模块化（api / agents / db / utils），环境变量与 `.env` 管理密钥与地址。  
- **前端**：React 18 + TypeScript + Vite，WebSocket 与 AudioContext 使用“全局单例”（如 `window._globalWs`）避免热更新与组件重挂载导致断连或无法发消息。  
- **可观测**：关键节点（WebSocket 收发包、工作流各节点、TTS/ASR）带日志，便于排查“一直正在思考”或无声等问题。

---

## 三、技术实现

### 3.1 后端技术栈与模块

| 类别     | 技术/库           | 用途说明 |
|----------|--------------------|----------|
| Web 框架 | FastAPI + Uvicorn  | HTTP/WebSocket 服务、CORS、生命周期 |
| 工作流   | LangGraph          | 多节点 DAG：orchestrator → personality → supervisor → revision |
| LLM      | 阿里云百炼 Qwen    | 云 API `qwen-turbo`，兼容 OpenAI 格式 endpoint |
| ASR      | 阿里云百炼         | 模型 `paraformer-realtime-v2`，音频 → 文本 |
| TTS      | 阿里云百炼         | 模型 `sambert-{voice}-v1`（如 zhiyan），流式 WAV |
| 关系库   | SQLite + SQLAlchemy| 性格参数、对话历史、反思日志 |
| 向量库   | ChromaDB           | 用户记忆向量存储与检索 |
| HTTP 客户端 | httpx            | 异步调用 DashScope API |
| 其他     | Pydantic、python-dotenv | 配置与数据校验 |

**目录与职责简述：**

- `main.py`：FastAPI 应用、CORS、路由挂载、`/` 与 `/health`、数据库初始化（lifespan）。  
- `api/websocket_handler.py`：WebSocket 连接管理、文本/音频消息分发、`process_and_respond`（调用工作流 + TTS 流式推送 + 反思触发）。  
- `api/reflection_api.py`：`POST /api/reflection/trigger`、`GET /api/reflection/status/{user_id}`。  
- `agents/workflow.py`：`AgentState`、四节点实现、LangGraph 图构建、`process_user_input` 入口及与 DB/记忆的交互。  
- `agents/reflection.py`：`perform_reflection`（拉取近期对话、调用 Qwen 分析、解析 JSON 更新性格并写库）。  
- `db/personality.py`：SQLite 表结构（personality_params、conversation_history、reflection_logs）及 CRUD。  
- `db/memory.py`：ChromaDB 初始化（关闭 telemetry）、add/search/clear 记忆。  
- `db/init_db.py`：应用启动时统一初始化 SQLite + ChromaDB。  
- `utils/api_clients.py`：DashScope ASR/TTS/Qwen 封装及单例获取。  
- `utils/reflection_scheduler.py`：按对话轮次判断是否触发 `perform_reflection`（如每 10 轮）。  

### 3.2 前端技术栈与模块

| 类别     | 技术/库                    | 用途说明 |
|----------|-----------------------------|----------|
| 框架     | React 18                    | UI 与状态 |
| 语言     | TypeScript                  | 类型安全 |
| 构建     | Vite 5                      | 开发/生产构建 |
| 2D 渲染  | PixiJS 6.5.10               | Canvas/WebGL 舞台 |
| Live2D   | pixi-live2d-display (Cubism 4) | 模型加载、表情、口型 |
| 通信     | 原生 WebSocket              | 与后端 `/ws/{client_id}` 通信 |
| 音频     | 原生 AudioContext           | 解码 WAV、队列顺序播放 |

**目录与职责简述：**

- `App.tsx`：根布局，生成稳定 `clientId`，渲染 `Live2DStage` 与 `ChatInterface`。  
- `components/Live2DStage.tsx`：PIXI 应用初始化、WebGL 兼容 patch、Live2D 模型加载与缩放/居中、表情更新、口型/音频幅度接口。  
- `components/ChatInterface.tsx`：输入框、发送、消息列表、连接状态；依赖 `useWebSocket` 收发包与回调。  
- `services/websocket.ts`：`useWebSocket(clientId, callbacks)`，全局 WebSocket/AudioContext/音频队列，处理 `text_response`、`audio_start`/`audio_end`、二进制音频块与播放队列，自动重连。  

### 3.3 数据流简述

1. **用户发文字**：前端 `sendMessage({ type: 'text_input', text })` → 后端 `handle_text_message` → `process_and_respond(text, client_id)`。  
2. **用户发语音**：前端发送音频二进制 → 后端 `handle_audio_message` → ASR 得到文本 → 同上 `process_and_respond`。  
3. **process_and_respond 内**：发 `status: thinking` → `process_user_input`（LangGraph 全链路）→ 存对话与记忆 → 发 `text_response` + emotion/expression → 发 `audio_start` → TTS 流式合成并 `send_audio_chunk` → 发 `audio_end` → 可选 `check_and_reflect`。  
4. **前端**：收到 `text_response` 更新气泡与表情；收到音频块入队播放；收到 `audio_end` 可结束口型或状态。

### 3.4 使用的模型与 API

| 能力 | 模型/服务 | 说明 |
|------|------------|------|
| 对话与推理 | 阿里云百炼 **qwen-turbo** | 统筹、执行、监督、修订、反思均调用同一模型 |
| 语音识别 | 阿里云百炼 **paraformer-realtime-v2** | 将用户上传的音频转为文字 |
| 语音合成 | 阿里云百炼 **sambert-zhiyan-v1**（知燕） | 支持其他发音人如 zhiqi、zhitian、zhijian 等 |
| 形象与表情 | Live2D（如 Haru） | 前端渲染，表情由后端 emotion 映射为 expression id |

所有云服务均通过 **DashScope API Key**（环境变量 `DASHSCOPE_API_KEY`）认证，端点分别为：

- Qwen：`https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions`  
- ASR/TTS：见 `utils/api_clients.py` 中各 `base_url`。

### 3.5 部署与运行

- **后端**：  
  - `cd digital-human/backend`  
  - 建议使用虚拟环境：`python3 -m venv venv && source venv/bin/activate`  
  - `pip install -r requirements.txt`  
  - 配置 `.env`（见 `CONFIG.md`，至少配置 `DASHSCOPE_API_KEY`）  
  - `python main.py`（默认 `http://0.0.0.0:8000`）  

- **前端**：  
  - `cd digital-human/frontend`  
  - `npm install && npm run dev`（默认 `http://127.0.0.1:5173`，可 `--host 127.0.0.1 --port 5173`）  

- **访问**：浏览器打开前端地址，即可与数字人进行文字/语音交互。API 文档：`http://localhost:8000/docs`。

---

## 四、文档与扩展

- **CONFIG.md**：环境变量、本地 Qwen（可选）、DashScope、Live2D 模型路径等配置说明。  
- **LIVE2D_MODELS.md**：免费 Live2D 模型获取方式与项目内使用方式。  
- **README.md**：快速开始、项目结构、主要 API、注意事项与开发计划。  

后续可扩展方向：更多 TTS 发音人/厂商、情感模型细化、3D 数字人、性能与延迟优化、多用户与鉴权等。  

— 文档版本与项目版本对应，如有架构变更请同步更新本文档。
