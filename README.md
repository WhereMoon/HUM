# 拟人数字人陪伴系统

基于多模型协作的 Web 端数字人陪伴系统，具备动态人格演化能力。

## 项目结构

```
digital-human/
├── backend/          # FastAPI 后端
│   ├── agents/      # LangGraph Agent 工作流
│   │   ├── workflow.py      # 多Agent协作流程
│   │   └── reflection.py    # 人格演化反思机制
│   ├── api/         # API 路由
│   │   ├── websocket_handler.py  # WebSocket实时交互
│   │   └── reflection_api.py     # 反思API端点
│   ├── db/          # 数据库相关
│   │   ├── personality.py   # 性格参数数据库
│   │   ├── memory.py        # 向量记忆管理
│   │   └── init_db.py       # 数据库初始化
│   ├── utils/       # 工具函数
│   │   ├── api_clients.py   # 外部API客户端
│   │   ├── audio_processor.py  # 音频处理
│   │   └── reflection_scheduler.py  # 反思调度器
│   └── main.py      # 应用入口
├── frontend/        # React 前端
│   └── src/
│       ├── components/  # React 组件
│       │   ├── Live2DStage.tsx    # Live2D渲染
│       │   └── ChatInterface.tsx  # 聊天界面
│       ├── services/    # 服务层
│       │   └── websocket.ts       # WebSocket服务
│       └── App.tsx      # 主应用
└── README.md
```

## 核心特性

- **多模型协作**: 使用 LangGraph 实现"统筹-执行-监督"的三层 Agent 架构
- **动态人格演化**: 基于对话历史的自动反思机制，数字人性格会随时间变化
- **实时交互**: WebSocket 流式传输，支持语音输入/输出
- **长效记忆**: ChromaDB 向量数据库存储对话记忆，支持语义检索
- **Live2D 视觉**: 2D 数字人形象，支持表情切换和口型同步

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- **阿里云百炼 API Key**（必填，用于 Qwen/ASR/TTS，在 `.env` 中配置 `DASHSCOPE_API_KEY`）
- **本地 Qwen API**（可选，若使用云 Qwen 可忽略）

### 后端设置

1. 进入后端目录：
```bash
cd backend
```

2. 创建虚拟环境并安装依赖：
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. 配置环境变量：
```bash
# 在 backend 目录下复制 .env.example 为 .env，并填入 DASHSCOPE_API_KEY
cp .env.example .env
# 编辑 .env，必填：DASHSCOPE_API_KEY（阿里云百炼）；可选：LOCAL_QWEN_URL
```

4. 测试本地 Qwen 连接：
```bash
python test_local_qwen.py
```

5. 启动服务器：
```bash
python main.py
# 或使用启动脚本
chmod +x run.sh
./run.sh
```

服务器将在 `http://localhost:8000` 启动。

### 前端设置

1. 进入前端目录：
```bash
cd frontend
```

2. 安装依赖：
```bash
npm install
```

3. 启动开发服务器：
```bash
npm run dev
```

前端将在 `http://localhost:3000` 启动。

## API 文档

启动后端后，访问 `http://localhost:8000/docs` 查看 Swagger API 文档。

### 主要端点

- `GET /`: 健康检查
- `GET /health`: 服务状态
- `WebSocket /ws/{client_id}`: 实时交互端点
- `POST /api/reflection/trigger`: 手动触发人格反思
- `GET /api/reflection/status/{user_id}`: 查看反思状态

## 使用说明

1. **首次使用**: 系统会自动为新用户创建默认性格参数
2. **对话交互**: 通过前端界面输入文字或使用语音输入
3. **人格演化**: 每 10 轮对话后，系统会自动触发反思，更新性格参数
4. **记忆检索**: 系统会从历史对话中检索相关记忆，提升回复连贯性

## 技术栈

### 后端
- **FastAPI**: 异步 Web 框架
- **LangGraph**: Agent 工作流编排
- **ChromaDB**: 向量数据库（记忆存储）
- **SQLite**: 关系数据库（性格参数）
- **本地 Qwen2.5 API**: 部署在树莓派上，用于所有 Agent 节点（统筹/执行/监督）
- **阿里云百炼 API**: ASR (语音识别), TTS (语音合成)

### 前端
- **React 18**: UI 框架
- **TypeScript**: 类型安全
- **Vite**: 构建工具
- **PixiJS**: 2D 渲染引擎
- **Live2D**: 数字人模型驱动

## 开发计划

- [x] 项目结构初始化
- [x] 数据库设计
- [x] Agent 工作流实现
- [x] API 集成
- [x] WebSocket 流式交互
- [x] Live2D 集成
- [x] 人格演化逻辑
- [ ] 性能优化
- [ ] 更多 TTS 提供商支持
- [ ] 3D 模型支持（Phase 2）

## 注意事项

1. **本地 Qwen API**: 确保树莓派上的 Qwen API 服务正在运行，并且网络可达
2. **Live2D 模型**: 需要自行准备 Live2D 模型文件，放置在 `frontend/public/models/` 目录
3. **数据库**: 首次运行会自动创建数据库文件在 `backend/data/` 目录
4. **API Key**: 请勿将 `.env` 或真实 API Key 提交到版本库；使用 `.env.example` 作为模板

## 许可证

MIT License
