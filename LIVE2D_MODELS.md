# Live2D 免费模型下载资源

以下是可以直接下载的免费 Live2D 模型资源：

## 官方免费模型

### 1. Live2D Cubism SDK 示例模型
- **下载地址**: https://www.live2d.com/download/cubism-sdk/
- **说明**: Live2D 官方提供的示例模型，包括：
  - Haru (春)
  - Rice (米)
  - 其他示例角色
- **格式**: .model3.json (Cubism 3.0+)

### 2. Live2D 官方角色库
- **下载地址**: https://www.live2d.com/sdk/download/cubism-sdk-free-character/
- **说明**: 官方提供的免费角色模型，可直接用于商业项目

## 社区免费模型

### 3. Booth (日本)
- **网址**: https://booth.pm/ja/search/live2d
- **搜索**: "live2d 無料" 或 "live2d free"
- **说明**: 日本最大的同人商品平台，有很多免费的 Live2D 模型

### 4. GitHub 开源模型
- **搜索**: GitHub 搜索 "live2d model free"
- **推荐仓库**:
  - https://github.com/guansss/pixi-live2d-display (包含示例模型)
  - https://github.com/zenghongtu/live2d-model-assets

### 5. 中文社区资源
- **Bilibili**: 搜索 "Live2D 模型 免费下载"
- **贴吧**: Live2D 吧、Vtuber 吧
- **说明**: 很多创作者会分享免费模型

## 快速开始

### 使用 pixi-live2d-display 示例模型

1. 安装依赖后，示例模型通常位于：
   ```
   node_modules/pixi-live2d-display/lib/assets/
   ```

2. 复制模型到项目：
   ```bash
   cp -r node_modules/pixi-live2d-display/lib/assets/* frontend/public/models/
   ```

### 下载官方 Haru 模型

1. 访问 Live2D 官网下载 Cubism SDK
2. 解压后找到 `Samples/Resources` 目录
3. 复制 `Haru` 或 `Rice` 模型文件夹到 `frontend/public/models/`

## 模型目录结构

将下载的模型放置在以下目录：
```
frontend/public/models/
  └── your-model-name/
      ├── your-model-name.model3.json
      └── (其他资源文件)
```

## 推荐免费模型

1. **Haru (春)** - Live2D 官方示例，适合初学者
2. **Rice (米)** - Live2D 官方示例，简单可爱
3. **Shizuku (雫)** - 社区常用模型，资源丰富

## 注意事项

- 确保模型格式为 `.model3.json` (Cubism 3.0+)
- 检查模型许可证，确保可以用于你的项目
- 某些模型可能需要 Cubism Editor 进行格式转换

## 模型使用

在 `Live2DStage.tsx` 中修改模型路径：
```typescript
const modelPath = '/models/your-model-name/your-model-name.model3.json'
```
