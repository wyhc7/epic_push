# 🎮 epic_push — Epic Games 免费游戏 Telegram 通知机器人

<p align="center">
  <b>零服务器 · 零费用 · 零代码基础 · Fork 即用</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License">
  <img src="https://img.shields.io/badge/platform-GitHub%20Actions-orange.svg" alt="Platform">
  <img src="https://img.shields.io/badge/schedule-每天%2010:00%20北京时间-brightgreen.svg" alt="Schedule">
</p>

---

epic_push 是一个基于 **GitHub Actions** 的全自动脚本，每天定时检测 **Epic Games Store** 的免费游戏，并通过 **Telegram Bot** 第一时间推送到你的手机上。无需购买服务器、无需编写一行代码，Fork 仓库、填入配置，即可永久运行。

---

## 📑 目录

- [🎯 它能做什么？](#-它能做什么)
- [📸 效果预览](#-效果预览)
- [🏗️ 工作原理](#️-工作原理)
- [🚀 新手部署教程](#-新手部署教程)
  - [第一步：准备 Telegram 机器人](#第一步准备-telegram-机器人)
  - [第二步：Fork 本仓库](#第二步fork-本仓库)
  - [第三步：配置 Secrets](#第三步配置-secrets)
  - [第四步：开启工作流写权限](#第四步开启工作流写权限)
  - [第五步：启动并测试](#第五步启动并测试)
- [⚙️ 自定义配置](#️-自定义配置)
- [🔧 故障排查](#-故障排查)
- [🖥️ 本地运行（进阶）](#️-本地运行进阶)
- [📂 项目结构](#-项目结构)
- [❓ 常见问题 FAQ](#-常见问题-faq)
- [📄 许可证 & 致谢](#-许可证--致谢)

---

## 🎯 它能做什么？

| 场景 | 说明 |
|---|---|
| 🎁 **每周四 Epic 更新免费游戏** | 北京时间次日 10:00，自动推送通知到你的 Telegram |
| 🎄 **圣诞/春节期间每日送游戏** | 每天检测，有新游戏立刻推送 |
| 🤫 **日常无更新时保持安静** | 智能去重，旧游戏不重复骚扰你 |
| 🔄 **永久自动运行** | Keepalive 保活机制，不用担心被 GitHub 暂停 |

**你只需要在 Telegram 收到这样一条消息：**

> 🆓 **Epic Games 限时免费** 🆓
>
> [游戏封面大图]
>
> 🎮 **DEATH STRANDING**
>
> ⏰ 截止：2025-06-19 17:00 UTC
>
> 📋 From legendary game creator Hideo Kojima…
>
> 👉 [点击此处领取]

然后点链接领取，游戏永久入库。就这么简单。

---

## 🏗️ 工作原理

```
┌─────────────────────────────────────────────────┐
│                  GitHub Actions                  │
│                                                 │
│  每天 UTC 02:00 (北京时间 10:00) 自动触发  │
│                      │                          │
│                      ▼                          │
│  ┌───────────────────────────────────────┐      │
│  │           main.py 执行流程              │      │
│  │                                        │      │
│  │  ① 请求 Epic GraphQL API               │      │
│  │     ↓                                  │      │
│  │  ② 遍历全部促销游戏                     │      │
│  │     ↓                                  │      │
│  │  ③ 筛选 discountPercentage = 0        │      │
│  │     (100% 折扣 = 完全免费)             │      │
│  │     ↓                                  │      │
│  │  ④ 检查上架时间 (startDate)            │      │
│  │     ├─ < 28 小时 → 🆕 新游戏 → 推送    │      │
│  │     └─ ≥ 28 小时 → 📦 旧游戏 → 跳过    │      │
│  │     ↓                                  │      │
│  │  ⑤ 提取封面图/标题/简介/领取链接        │      │
│  │     ↓                                  │      │
│  │  ⑥ 构建 HTML 富文本消息                 │      │
│  │     ↓                                  │      │
│  │  ⑦ POST → Telegram Bot API            │      │
│  └───────────────────────────────────────┘      │
│                      │                          │
│                      ▼                          │
│              📱 你的 Telegram                     │
│           收到精美推送通知 ✅                       │
└─────────────────────────────────────────────────┘
```

### 关键技术细节

| 环节 | 实现方式 |
|---|---|
| **数据来源** | Epic Games 官方 GraphQL API：`store-site-backend-static.ak.epicgames.com/freeGamesPromotions` |
| **免费判定** | `discountPercentage == 0` → 100% 折扣即为免费 |
| **去重窗口** | 上架时间距今 < 28 小时才推送（留出 4 小时容错应对 GitHub Actions 调度延迟） |
| **封面图** | 优先取 `Thumbnail`，其次 `OfferImageWide` |
| **消息格式** | Telegram HTML parse_mode，通过 `<a href='图片URL'>&#8205;</a>` 技巧实现封面预览 |
| **网络可靠性** | 3 次指数退避重试（`2ⁿ` 秒间隔），超时 30s |
| **容错策略** | 日期解析失败 → 默认推送（宁可多发不漏发） |

---

## 🚀 新手部署教程

> **预计耗时：10 分钟**。你只需要一个 GitHub 账号和一个 Telegram 账号。

---

### 第一步：准备 Telegram 机器人

> ⏱️ 约 3 分钟 | 如果你已有 Bot Token 和 Chat ID，请跳至第二步。

#### 1.1 创建 Bot，获取 Token

1. 打开 Telegram，在搜索框输入 **`@BotFather`**（注意：是 BotFather，不是 BotFather 的仿冒号，认准蓝勾官方认证）
2. 点击 Start，你会看到一串欢迎信息和命令列表
3. 发送命令：
   ```
   /newbot
   ```
4. BotFather 会问：「Alright, a new bot. How are we going to call it?」
   - **输入你想给机器人起的名字**，例如：`Epic 免费游戏通知`
5. 接着问：「Good. Now let's choose a username for your bot.」
   - **输入机器人的用户名，必须以 `bot` 结尾**，例如：`epic_free_game_bot`
6. 🎉 创建成功！你会收到一条消息，其中包含：
   ```
   Use this token to access the HTTP API:
   1234567890:ABCdEfGhIJKlmnOPQRstUVwXyZ-1234567890
   ```
   > ⚠️ **这串字符就是你的 Bot Token，立即复制保存！不要分享给任何人！**

#### 1.2 获取你的 Chat ID

1. 在 Telegram 搜索 **`@userinfobot`**
2. 点击 Start，它会立刻回复你的信息：
   ```
   Id: 1234567890
   First: 张三
   ```
3. **等号后面的数字就是你的 Chat ID**，复制保存

#### 1.3 验证（可选但推荐）

给你刚创建的机器人随便发一条消息（搜索你刚才设的用户名，比如 `@epic_free_game_bot`），确认对话能建立。这一步确保你的账号和机器人之间能正常通信。

> 📋 **准备清单：你现在应该有**
> - 一串 Bot Token（类似 `1234567890:ABCdEfGh...`）
> - 一串 Chat ID（纯数字，如 `1234567890`）

---

### 第二步：Fork 本仓库

> ⏱️ 约 30 秒

1. 确保你已经登录 GitHub（没有账号的话去 [github.com](https://github.com) 免费注册一个）
2. 打开本仓库：[github.com/wyhc7/epic_push](https://github.com/wyhc7/epic_push)
3. 点击右上角的 **`Fork`** 按钮
4. 弹出窗口确认仓库名（保持 `epic_push` 即可），点击 **`Create fork`**

> ✅ 几秒后，你会跳转到属于你自己的 `你的用户名/epic_push` 仓库。这就是你的副本，接下来所有操作都在这个 Fork 仓库里进行。

---

### 第三步：配置 Secrets

> ⏱️ 约 2 分钟 | **最关键的步骤，务必仔细操作**

1. 在你 Fork 后的仓库页面，点击顶部 **`Settings` ⚙️** 标签
2. 在左侧菜单栏，找到并点击 **`Secrets and variables`** → **`Actions`**
3. 你会看到一个页面，包含两个标签页：**Secrets** 和 **Variables**
4. 确保你在 **Secrets** 标签页下，点击绿色的 **`New repository secret`** 按钮
5. 依次添加以下两个 Secret：

**添加第一个：**

| 字段 | 输入内容 |
|---|---|
| **Name** * | `TG_BOT_TOKEN` |
| **Secret** * | 粘贴你在第一步获取的 Bot Token（例如 `1234567890:ABCdEfGhIJKlmnOPQRstUVwXyZ-1234567890`） |

点击 **`Add secret`**

**添加第二个：**

再次点击 **`New repository secret`**：

| 字段 | 输入内容 |
|---|---|
| **Name** * | `TG_CHAT_ID` |
| **Secret** * | 粘贴你在第一步获取的 Chat ID（例如 `1234567890`） |

点击 **`Add secret`**

> ✅ 完成后，Secrets 列表应该显示两个条目：`TG_BOT_TOKEN` 和 `TG_CHAT_ID`。**注意大小写完全一致！**

---

### 第四步：开启工作流写权限

> ⏱️ 约 30 秒 | **如果不做这步，Keepalive 保活机制会在 60 天后失效**

GitHub 默认对 Fork 仓库限制写权限，而 Keepalive 工作流需要通过自动提交来保持仓库活跃。我们需要手动开启：

1. 仍然在 **`Settings`** 页面
2. 左侧菜单点击 **`Actions`** → **`General`**
3. 向下滚动到 **`Workflow permissions`** 区域
4. 选择 **`Read and write permissions`**（默认是 Read-only）
5. 勾选 **`Allow GitHub Actions to create and approve pull requests`**（如果存在）
6. 点击 **`Save`** 保存

> ✅ 这确保了 Keepalive 工作流下个月能正常自动创建 commit。

---

### 第五步：启动并测试

> ⏱️ 约 2 分钟

#### 5.1 启用工作流

1. 点击仓库顶部的 **`Actions`** 标签
2. 如果看到黄色提示条 "Workflows aren't being run on this forked repository"，点击绿色按钮：
   **`I understand my workflows, go ahead and enable them`**

#### 5.2 手动触发首次运行

1. 在 Actions 页面，左侧列表点击 **`Epic Free Game Notifier`**
2. 右侧会看到 **`Run workflow`** 下拉按钮，点击它
3. Branch 保持默认 `main`，点击 **`Run workflow`**
4. 刷新页面（或等待几秒），你会看到一个黄色的运行条目出现

#### 5.3 查看运行结果

1. 点击那个运行条目（名称类似 "Epic Free Game Notifier"）
2. 再点击 **`run_script`** job
3. 展开 **`Run Notifier`** 步骤，查看日志输出

你会看到类似这样的日志：

```
2025-07-09 02:00:15 │ INFO     │ 🚀 开始检测 Epic Games 免费游戏 (通知窗口: 28小时)…
2025-07-09 02:00:17 │ INFO     │ 😴 当前没有需要推送的免费游戏 (可能是旧游戏被去重跳过)
```

或者如果有新游戏：

```
2025-07-09 02:00:15 │ INFO     │ 🚀 开始检测 Epic Games 免费游戏 (通知窗口: 28小时)…
2025-07-09 02:00:17 │ INFO     │ 🔍 发现 1 款免费游戏，开始推送通知…
2025-07-09 02:00:17 │ INFO     │ 📨 推送: DEATH STRANDING (截止: 2025-07-16 17:00 UTC)
2025-07-09 02:00:18 │ INFO     │ ✅ Telegram 消息发送成功
2025-07-09 02:00:18 │ INFO     │ ✨ 全部完成！
```

- ✅ 看到 **绿色勾** + 日志正常 → **部署成功！**
- 😴 看到 "没有需要推送的免费游戏" → **也说明成功了**，只是当前 Epic 没有新上架的免费游戏
- ❌ 看到 **红色叉** → 请查看日志错误信息，对照下方故障排查

---

## ⚙️ 自定义配置

### 修改通知时间窗口

默认只推送 28 小时内的新游戏。你可以自定义这个窗口：

1. **Settings → Secrets and variables → Actions → Variables**（注意这次是 Variables，不是 Secrets）
2. 点击 **`New repository variable`**
3. Name：`NOTIFY_HOURS`
4. Value：你想要的数字，例如：
   - `24` → 只推送 1 天内的
   - `72` → 推送 3 天内的
   - `168` → 推送一周内的（适合不常看消息的用户）

### 修改执行时间

打开 `.github/workflows/main.yml`，编辑 cron 表达式：

```yaml
on:
  schedule:
    - cron: '0 2 * * *'   # 默认：UTC 02:00 = 北京时间 10:00
```

| 改成 | 北京时间 | 适用场景 |
|---|---|---|
| `0 2 * * *` | 上午 10:00 | 默认（推荐） |
| `0 6 * * *` | 下午 14:00 | 下午党 |
| `0 12 * * *` | 晚上 20:00 | 晚间通知 |
| `0 */6 * * *` | 每 6 小时一次 | 高频监测 |
| `0 0 * * 4` | 周四 08:00 | 仅在周四检查 |

> ⚠️ 注意：cron 时间是 UTC，北京时间 = UTC + 8。调试时建议使用 `workflow_dispatch` 手动触发。

### 推送通知样例

如果你想把消息改成英文或自定义风格，编辑 `main.py` 中 `build_message()` 函数：

```python
def build_message(game: dict) -> str:
    # 自定义你的消息模板
    msg = (
        f"🆓 <b>Epic Games FREE</b> 🆓\n\n"
        f"🎮 <b>{html.escape(game['title'])}</b>\n"
        f"⏰ Ends: {game['end_date']}\n\n"
        f"📋 {html.escape(game['description'])}\n\n"
        f"👉 <a href='{game['link']}'>Claim Now</a>"
    )
    return msg
```

改完提交到 GitHub，下次运行即生效。

---

## 🔧 故障排查

### 运行成功但没收到 Telegram 消息？

这是 **最常被误认为失败** 的情况。检查两点：

1. **去重机制在正常工作** — 如果 Epic 当前免费游戏已上架超过 28 小时，脚本会自动跳过。只有刚上架的新游戏才会推送。
2. 登录 GitHub Actions 查看 `Run Notifier` 日志，如果显示 `😴 当前没有需要推送的免费游戏`，说明一切正常，只是时机未到。

**验证方法：** 先给你机器人发一条消息 `你好`，确认对话通路存在。等到周四 Epic 更新免费游戏后（北京时间周四 23:00 之后），手动 Run workflow 一次，应该就能收到推送。

### 日志报错：`❌ 缺少配置：请设置 TG_BOT_TOKEN 和 TG_CHAT_ID`

说明 Secrets 没配好。检查：
- Secrets 名称**完全一致**：`TG_BOT_TOKEN`、`TG_CHAT_ID`（注意下划线，不是横杠）
- 没有多余的空格或换行
- Secret 是加在 **Actions secrets** 而不是 Codespaces secrets 或 Dependabot secrets

### 日志报错：`获取 Epic 免费游戏列表失败`

网络问题或 Epic API 临时服务中断。脚本会自动重试 3 次。如果 3 次都失败：
- 等几分钟后手动再 Run workflow 一次
- 大部分情况是临时波动，下次自动运行即可恢复

### Actions 页面显示 "There are no workflow runs yet"

1. 确认仓库 `.github/workflows/` 目录下文件存在
2. 确认点过 `I understand my workflows…` 按钮
3. 手动 Run workflow 一次

### Keepalive 失败

检查 **第四步** 权限设置是否正确（`Read and write permissions`）。

---

## 🖥️ 本地运行（进阶）

如果你想在电脑上调试或修改代码：

```bash
# 1. 克隆仓库
git clone https://github.com/你的用户名/epic_push.git
cd epic_push

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 设置环境变量（模拟 GitHub Secrets）
export TG_BOT_TOKEN="你的Token"
export TG_CHAT_ID="你的ChatID"
export NOTIFY_HOURS="28"

# 5. 运行
python main.py
```

> ⚠️ 本地运行会真实调用 Epic API 和发送 Telegram 消息，请确保变量正确。

---

## 📂 项目结构

```
epic_push/
├── .github/
│   └── workflows/
│       ├── main.yml              # 主工作流：每天定时触发 main.py
│       └── keepalive.yml         # 保活工作流：每月自动创建空提交
├── main.py                       # 核心脚本（263行）
├── requirements.txt              # Python 依赖：requests
├── README.md                     # 本文档
├── LICENSE                       # MIT License
└── .gitignore                    # Git 忽略规则
```

| 文件 | 职责 |
|---|---|
| `main.py` | 全部业务逻辑：请求 API → 筛选免费游戏 → 去重判断 → 构建消息 → 发送 Telegram |
| `main.yml` | 定义 GitHub Actions 行为：Python 环境、定时器、Secrets 注入 |
| `keepalive.yml` | 每月 1 号自动提交空 commit，防止仓库被 GitHub 标记为"不活跃"而暂停定时任务 |
| `requirements.txt` | 仅依赖 `requests` 库（HTTP 请求） |

---

## ❓ 常见问题 FAQ

<details>
<summary><b>Q: 我手动 Run workflow 了，日志也显示成功，为什么没收到消息？</b></summary>

**A:** 这是去重机制的预期行为。如果当前 Epic 免费游戏已上架超过 28 小时，脚本会自动跳过。日志会显示 `😴 当前没有需要推送的免费游戏`。等 Epic 更新新游戏后（如周四晚），再次手动触发即可收到。详见上方「故障排查」第一项。
</details>

<details>
<summary><b>Q: 每天什么时候自动运行？</b></summary>

**A:** 每天 **北京时间上午 10:00**（UTC 02:00）。GitHub Actions 调度可能有 5~30 分钟延迟，完全正常。
</details>

<details>
<summary><b>Q: 为什么是 28 小时而不是 24 小时？</b></summary>

**A:** 留出 4 小时冗余，应对 GitHub Actions cron 的调度延迟。如果设为 24，某天稍微延迟几个小时就会漏发新游戏。28 小时是一个经过实际测试的稳妥值。你也可以自定义，见「自定义配置」。
</details>

<details>
<summary><b>Q: 如果这周 Epic 送了两款游戏，会收到几条通知？</b></summary>

**A:** 每条游戏一条消息，所以是两条。每条消息独立推送，附带各自的封面图和领取链接。
</details>

<details>
<summary><b>Q: 我需要定期维护吗？</b></summary>

**A:** 几乎不需要。Keepalive 每月自动为仓库保持活跃。唯一需要注意的是：如果 Epic 修改了 API 结构，脚本可能需要更新——届时检查 Actions 日志，如果连续几天报错，查看本仓库是否有更新，同步一下即可。
</details>

<details>
<summary><b>Q: 别人能用我的机器人吗？</b></summary>

**A:** 不能。你的 Bot Token 和 Chat ID 决定了消息只发给你自己。Secrets 在 GitHub 端加密存储，其他人（包括仓库的协作者）看不到。
</details>

<details>
<summary><b>Q: 能推送到微信群/钉钉/Server酱吗？</b></summary>

**A:** 当前版本仅支持 Telegram。扩展其他平台只需在 `send_telegram_message()` 旁增加新的发送函数，欢迎提 PR。
</details>

<details>
<summary><b>Q: GitHub Actions 免费额度够用吗？</b></summary>

**A:** 绰绰有余。每月总共运行约 30 次（每天 1 次 + 每月 1 次 keepalive），每次仅需几秒。GitHub 免费额度为每月 2000 分钟，实际用量不到 1%。
</details>

<details>
<summary><b>Q: 我的 Token 泄露了怎么办？</b></summary>

**A:** 立即去 Telegram 找 `@BotFather`，发送 `/revoke` 吊销旧 Token 并生成新的。然后在 GitHub Secrets 里更新 `TG_BOT_TOKEN` 的值。
</details>

---

## 📄 许可证 & 致谢

本项目基于 **MIT License** 开源。你可以自由使用、修改和分发。

本项目参考并改进自 [wwxseo/epic-](https://github.com/wwxseo/epic-)，感谢原作者提供的优秀思路。

主要改进：
- 网络请求自动重试（3 次指数退避）
- 现代 timezone-aware datetime API
- 结构化日志输出
- 可配置的通知时间窗口（`NOTIFY_HOURS`）
- 消息模板独立解耦
- Python 3.11+ 与最新 GitHub Actions runner 适配

---

<p align="center">
  ⭐ 如果这个项目帮到了你，请给个 Star 支持一下！
</p>

<p align="center">
  <a href="https://github.com/wyhc7/epic_push">
    <img src="https://img.shields.io/github/stars/wyhc7/epic_push?style=social" alt="Stars">
  </a>
</p>