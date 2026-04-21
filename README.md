# MCP EB 使用说明

MCP EB 是一个提供持续交互能力的 MCP 工具服务，面向 GitHub Copilot 等 AI 助手，支持通过 Web UI 与用户进行循环式沟通。

---

## 目录

- [功能简介](#功能简介)
- [项目结构](#项目结构)
- [快速开始](#快速开始)
- [命令说明](#命令说明)
- [工作原理](#工作原理)
- [VS Code 配置](#vs-code-配置)
- [Web UI 界面说明](#web-ui-界面说明)
- [常见问题](#常见问题)

---

## 功能简介

MCP EB 提供两个核心 MCP 工具：

| 工具 | 说明 |
|------|------|
| `eb_back` | AI 的唯一用户通道。AI 将工作摘要发送给用户，等待用户反馈后返回。实现了 AI ↔ 用户的持续循环交互。 |
| `eb_check` | 非阻塞地检查用户是否发送了中断信号。返回 `continue`（继续）或 `INTERRUPT`（中断）。 |

**核心特点：**
- AI 每完成一步工作后调用 `eb_back` 将摘要推送给用户
- 用户通过 Web UI 查看 AI 的摘要并输入回复
- AI 收到回复后继续工作，形成持续的交互循环
- 用户可随时点击 INTERRUPT 按钮中断 AI 的工作
- 服务端历史记录自动限制长度，降低长时间使用后的卡顿风险

---

## 项目结构

```
MCP_EB/
├── main.py          # CLI 命令入口
├── eb_mcp.py        # MCP Server（实现 eb_back 和 eb_check 工具）
├── eb_app.py        # FastAPI Web UI 服务器（消息队列 + REST API）
├── requirements.txt # Python 依赖列表
├── README.md        # 本说明文档
└── static/
    └── index.html   # Web UI 前端页面
```

---

## 快速开始

### 1. 安装依赖

```powershell
cd C:\Users\dqwan\Desktop\MCP_EB
pip install -r requirements.txt
```

### 2. 启动 Web UI

```powershell
python main.py app
```

- 自动在浏览器中打开 `http://localhost:7337`
- 自动将 `mcp-eb` 写入 VS Code 的 MCP 配置
- 保持此终端窗口运行，不要关闭

### 3. 在 VS Code 中使用

1. 重启 VS Code（使 MCP 配置生效）
2. 打开 GitHub Copilot Chat，切换到 Agent 模式
3. 告诉 AI：**"请通过 MCP EB 与我交互"**
4. AI 会调用 `eb_back` 将消息显示在 Web UI 中
5. 你在 Web UI 的输入框中输入回复，AI 收到后继续工作

---

## 命令说明

### `python main.py server`

启动 MCP 服务器（stdio 模式），供 VS Code Copilot 自动调用。  
通常不需要手动执行此命令，VS Code 会在需要时自动启动。

```powershell
python main.py server
```

### `python main.py app`

独立运行模式，启动 Web UI 服务器并自动配置 VS Code MCP。

```powershell
# 默认端口 7337，自动打开浏览器
python main.py app

# 自定义端口
python main.py app --port 8080

# 不自动打开浏览器
python main.py app --no-browser

# 不自动配置 VS Code MCP
python main.py app --no-vscode
```

### `python main.py version`

显示版本信息。

```powershell
python main.py version
```

### `python main.py test`

测试各组件是否正常运行。

```powershell
python main.py test
```

输出示例：
```
🔍 测试 App Server 连接 (http://localhost:7337)...
✅ App Server 运行正常
🔍 检查 VS Code MCP 配置...
✅ VS Code MCP 已配置 mcp-eb
```

### `python main.py copilot-server`

Copilot CLI MCP 服务器模式（功能同 `server`）。

### `python main.py bridge`

OpenClaw 桥接模式（当前版本暂不支持）。

---

## 工作原理

```
VS Code Copilot
      │
      │ (stdio MCP 协议)
      ▼
eb_mcp.py (MCP Server)
      │
      │ (HTTP REST API)
      ▼
eb_app.py (FastAPI 服务器 :7337)
      │
      │ (浏览器轮询)
      ▼
static/index.html (Web UI)
      │
      │ (用户输入回复)
      └─────────────────────────────→ 返回给 AI
```

**`eb_back` 调用流程：**

1. AI 调用 `eb_back(summary="工作摘要")`
2. MCP Server 将摘要 POST 到 Web UI 服务器
3. Web UI 自动显示新消息（Markdown 渲染）
4. 用户在输入框输入回复，点击"发送"
5. MCP Server 轮询到用户回复后，将其返回给 AI
6. AI 读取回复，继续工作，再次调用 `eb_back`

**`eb_check` 调用流程：**

1. AI 在每一步工作完成后调用 `eb_check()`
2. MCP Server 查询 Web UI 服务器的中断状态
3. 若用户点击了 INTERRUPT 按钮，返回 `"INTERRUPT"`；否则返回 `"continue"`
4. AI 收到 `INTERRUPT` 后立即停止并汇报进度

**自动启动机制：**

当 AI 调用 `eb_back` 时，MCP Server 会检查 Web UI 服务器是否运行。  
若未运行，会自动在后台启动 Web UI 服务器（无需用户手动操作）。

---

## VS Code 配置

运行 `python main.py app` 后，会自动在以下文件中添加配置：

```
C:\Users\<用户名>\AppData\Roaming\Code\User\mcp.json
```

添加的配置内容：

```json
{
    "servers": {
        "mcp-eb": {
            "command": "C:\\...\\python.exe",
            "args": [
                "C:\\Users\\dqwan\\Desktop\\MCP_EB\\main.py",
                "server"
            ],
            "type": "stdio"
        }
    }
}
```

**注意：修改 mcp.json 后需要重启 VS Code 才能生效。**

---

## Web UI 界面说明

访问 `http://localhost:7337` 打开 Web UI。

| 界面元素 | 说明 |
|----------|------|
| 顶部状态栏 | 显示连接状态（绿色=已连接，黄色=等待中）和当前项目目录 |
| 消息列表 | AI 消息（左侧，深色背景）和用户回复（右侧，蓝色背景） |
| 消息 ID 徽章 | 当前消息编号，便于追踪对话进度 |
| 清空历史按钮 | 清空当前已显示的历史记录，但不重置正在进行中的会话状态 |
| ⛔ INTERRUPT 按钮 | 点击后向 AI 发送中断信号，AI 会立即停止并汇报 |
| 输入框 | 输入对 AI 的回复（Enter 发送，Shift+Enter 换行）|
| 发送按钮 | 点击发送回复 |

**历史记录优化：**
- 服务端默认最多保留最近 `100` 条历史消息
- 页面初始化默认只加载最近 `50` 条消息
- 可通过 `POST /api/clear-history` 主动清空历史记录
- 可通过 `GET /api/history?limit=N` 只获取最近 `N` 条消息

**Markdown 支持：** AI 发送的摘要支持完整 Markdown 渲染，包括：
- 标题、列表、粗体、斜体
- 代码块（含语法高亮）
- 表格、引用块
- 链接

---

## 常见问题

### Q: 运行 `python main.py app` 后浏览器没有自动打开？

手动访问 `http://localhost:7337` 即可。

### Q: AI 发送消息后 Web UI 没有更新？

- 检查 `python main.py app` 的终端窗口是否报错
- 刷新浏览器页面
- 运行 `python main.py test` 检查服务状态

### Q: VS Code 中找不到 `mcp-eb` 工具？

1. 确认已运行过 `python main.py app`（自动配置 VS Code MCP）
2. 重启 VS Code
3. 在 Copilot Chat 中切换到 Agent 模式

### Q: 端口 7337 被占用怎么办？

```powershell
python main.py app --port 8080
```

注意：更改端口后，需要同步修改 `eb_mcp.py` 中的 `APP_PORT = 7337` 改为新端口。

### Q: 如何停止服务？

在运行 `python main.py app` 的终端中按 `Ctrl+C` 即可停止。

---

## 依赖说明

| 包名 | 用途 |
|------|------|
| `mcp` | MCP 协议 Python SDK，提供 FastMCP 服务器框架 |
| `fastapi` | Web UI 服务器框架 |
| `uvicorn` | ASGI 服务器，运行 FastAPI 应用 |
| `httpx` | HTTP 客户端，MCP Server 与 Web UI 通信 |
| `click` | CLI 命令行框架 |

---

*MCP EB v1.0.3*
