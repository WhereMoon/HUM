# 配置说明

## 环境变量配置

在 `backend` 目录下创建 `.env` 文件，包含以下配置：

```env
# 本地 Qwen API（可选，部署在树莓派或本机时使用）
LOCAL_QWEN_URL=http://localhost:8088/v1
LOCAL_QWEN_MODEL=qwen2.5

# 阿里云百炼 (DashScope) API Key（必填，用于 Qwen/ASR/TTS）
DASHSCOPE_API_KEY=your-dashscope-api-key

# Database
DATABASE_URL=sqlite:///./data/personality.db
CHROMA_DB_PATH=./data/chroma_db

# Server
HOST=0.0.0.0
PORT=8000
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

## 本地 Qwen API 配置

系统现在使用部署在树莓派上的本地 Qwen2.5 模型。确保：

1. **本地 Qwen API 服务正在运行**（可选，若使用云 Qwen 可跳过）
   - 默认地址：`http://localhost:8088`
   - API 端点：`/v1/chat/completions`

2. **网络连接**
   - 若部署在局域网设备（如树莓派），将 `.env` 中 `LOCAL_QWEN_URL` 改为该设备 IP 与端口

3. **测试连接**
   ```bash
   curl http://localhost:8088/v1/chat/completions \
     -H "Content-Type:application/json" \
     -d '{"model":"qwen2.5","messages":[{"role":"user","content":"你好"}]}'
   ```

## 获取 API Keys

### 阿里云百炼 (DashScope) API Key
1. 访问 https://dashscope.aliyun.com/
2. 注册/登录阿里云账号
3. 开通百炼服务
4. 在控制台获取 API Key，填入 `.env` 的 `DASHSCOPE_API_KEY`

**注意**：
- 百炼 API Key 同时支持 ASR (语音识别) 和 TTS (语音合成)
- 新用户通常有免费额度可以使用
- TTS 支持的声音类型：zhiyan(知燕-女声), zhiqi(知琪-女声), zhitian(知甜-女声), zhijian(知健-男声) 等
- ASR 模型：paraformer-realtime-v2

## Live2D 模型配置

1. 下载 Live2D 模型文件（.model3.json 格式）
2. 将模型文件放置在 `frontend/public/models/` 目录
3. 在 `Live2DStage.tsx` 中修改模型路径

示例目录结构：
```
frontend/public/models/
  └── shizuku/
      ├── shizuku.model3.json
      └── (其他资源文件)
```

## 数据库初始化

首次运行时会自动创建：
- SQLite 数据库：`backend/data/personality.db`
- ChromaDB 向量库：`backend/data/chroma_db/`

无需手动创建。
