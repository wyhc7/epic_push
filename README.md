# 🎮 epic_push — Epic 免费游戏 Telegram 通知机器人

<p align="center">
  <b>零服务器 · 零费用 · 零代码基础 · Fork 即用</b><br>
  <img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License">
  <img src="https://img.shields.io/badge/platform-GitHub_Actions-orange.svg" alt="Platform">
  <img src="https://img.shields.io/badge/schedule-每天10:00_北京时间-brightgreen.svg" alt="Schedule">
</p>

---

基于 **GitHub Actions** 的全自动脚本，每天检测 **Epic Games Store** 免费游戏，第一时间通过 **Telegram Bot** 推送到你手机。无需服务器、无需写代码，Fork + 填配置 = 永久运行。

---

## 📑 目录

- [它能做什么](#它能做什么)
- [工作原理](#工作原理)
- [🚀 部署教程（5 步）](#-部署教程5-步)
  - [第一步：准备 Telegram 机器人](#第一步准备-telegram-机器人)
  - [第二步：Fork 本仓库](#第二步fork-本仓库)
  - [第三步：配置 Secrets](#第三步配置-secrets)
  - [第四步：开启写权限](#第四步开启写权限)
  - [第五步：启动测试](#第五步启动测试)
- [自定义配置](#自定义配置)
- [故障排查](#故障排查)
- [本地运行](#本地运行)
- [项目结构](#项目结构)
- [常见问题 FAQ](#常见问题-faq)
- [许可证 & 致谢](#许可证--致谢)

---

## 它能做什么

| 场景 | 说明 |
|---|---|
| 🎁 **每周四 Epic 更新免费** | 次日 10:00 自动推送通知到 Telegram |
| 🎄 **节假日每日送游戏** | 每天检测，有新游戏立刻推送 |
| 🤫 **日常无更新时安静** | 智能去重，旧游戏不重复骚扰 |
| 🔄 **永久自动运行** | Keepalive 保活，不怕被 GitHub 暂停 |

**收到通知后，点击链接 → 跳转 Epic 商店 → 登录 → 免费入库，永久拥有。**

---

## 工作原理

```
每天北京时间 10:00（UTC 02:00）GitHub Actions 自动触发
                        │
         ┌──────────────▼──────────────┐
         │       main.py 执行流程        │
         │                              │
         │  ① 请求 Epic GraphQL API     │
         │  ② 遍历全部促销游戏           │
         │  ③ discountPercentage = 0    │
         │     → 100% 折扣 = 完全免费    │
         │  ④ 检查 startDate 上架时间    │
         │     ├ < 28h → 🆕 推送         │
         │     └ ≥ 28h → 📦 跳过         │
         │  ⑤ 提取封面/标题/简介/链接    │
         │  ⑥ 构建 HTML 富文本消息       │
         │  ⑦ POST → Telegram Bot API   │
         └──────────────┬──────────────┘
                        ▼
               📱 你的 Telegram
            收到精美推送通知 ✅
```

| 环节 | 实现 |
|---|---|
| 数据来源 | Epic 官方 GraphQL API（公开接口，无需 Key） |
| 免费判定 | `discountPercentage == 0` |
| 去重窗口 | 上架 < 28 小时才推送（留 4h 容错） |
| 封面图 | 优先 `Thumbnail`，其次 `OfferImageWide` |
| 消息格式 | Telegram HTML + `<a href>` 零宽字符封面预览 |
| 网络可靠性 | 3 次指数退避重试（2ⁿ 秒），超时 30s |
| 容错策略 | 日期解析失败 → 默认推送（不漏发） |

---

## 🚀 部署教程（5 步）

> **需时 10 分钟**，只需 GitHub + Telegram 账号。

---

### 第一步：准备 Telegram 机器人

> ⏱️ 3 分钟 | 已有 Token 和 Chat ID 可跳过。

**获取 Bot Token：**

1. Telegram 搜索 **`@BotFather`**（认准蓝勾 ✅）
2. 发送 `/newbot`
3. 按提示输入**显示名称**（如 `Epic 免费通知`）
4. 输入**用户名**（必须以 `bot` 结尾，如 `epic_free_game_bot`）
5. 获得 Bot Token，格式类似：
   ```
   1234567890:ABCdEfGhIJKlmnOPQRstUVwXyZ-1234567890
   ```
   > ⚠️ **立即复制保存，不要分享给任何人！**

**获取 Chat ID：**

1. 搜索 **`@userinfobot`**
2. 点击 Start，回复中的 `Id` 就是 Chat ID（纯数字）

**验证（推荐）：** 搜索刚创建的机器人用户名，给它发一条消息，确保通信正常。

> 📋 **你现在应该有：** Bot Token + Chat ID

---

### 第二步：Fork 本仓库

> ⏱️ 30 秒

打开 [wyhc7/epic_push](https://github.com/wyhc7/epic_push) → 右上角 **`Fork`** → **`Create fork`**。

---

### 第三步：配置 Secrets

> ⏱️ 2 分钟 | **最关键的一步**

在你 Fork 的仓库中：**`Settings`** ⚙️ → **`Secrets and variables`** → **`Actions`** → **`New repository secret`**，依次添加：

| Name | Secret |
|---|---|
| `TG_BOT_TOKEN` | 你的 Bot Token |
| `TG_CHAT_ID` | 你的 Chat ID |

> ✅ 两个 Secret 显示后即完成。**名称必须完全一致（大写 + 下划线）！**

---

### 第四步：开启写权限

> ⏱️ 30 秒 | **不做这步，60 天后 Keepalive 失效**

**`Settings`** → **`Actions`** → **`General`** → **Workflow permissions** → 选 **`Read and write permissions`** → **`Save`**

---

### 第五步：启动测试

> ⏱️ 2 分钟

1. 仓库顶部点击 **`Actions`** → 点绿色按钮 **`I understand my workflows…`**
2. 左侧选 **`Epic Free Game Notifier`** → 右侧 **`Run workflow`** → **`Run workflow`**
3. 点运行条目 → **`run_script`** → 展开 **`Run Notifier`** 查看日志：

**有新游戏时：**
```
✅ 绿勾  →  Telegram 消息发送成功 → 部署完成！
```

**无新游戏时（同样成功）：**
```
😴 当前没有需要推送的免费游戏 (可能是旧游戏被去重跳过)
```

| 日志结尾 | 含义 |
|---|---|
| ✅ 绿勾 | 部署成功，已推送 |
| 😴 无推送 | 部署成功，当前无新游戏（最常见） |
| ❌ 红叉 | 有问题，对照下方故障排查 |

---

## 自定义配置

### 修改通知窗口

**Settings → Secrets and variables → Actions → Variables** → **New variable**：

| Name | Value | 含义 |
|---|---|---|
| `NOTIFY_HOURS` | `24` | 仅推送 1 天内的 |
| `NOTIFY_HOURS` | `28` | 默认（推荐） |
| `NOTIFY_HOURS` | `168` | 推送一周内的 |

### 修改执行时间

编辑 `.github/workflows/main.yml` 的 cron：

```yaml
- cron: '0 2 * * *'   # 默认 UTC 02:00 = 北京时间 10:00
```

| cron | 北京时间 | 场景 |
|---|---|---|
| `0 2 * * *` | 10:00 | 默认 |
| `0 6 * * *` | 14:00 | 下午党 |
| `0 */6 * * *` | 每 6 小时 | 高频 |
| `0 0 * * 4` | 周四 08:00 | 仅周四 |

> ⚠️ cron 是 UTC 时间，北京时间 = UTC + 8。

### 自定义消息（改英文等）

编辑 `main.py` 的 `build_message()` 函数：

```python
def build_message(game: dict) -> str:
    safe_title = html.escape(game["title"])
    safe_desc  = html.escape(game["description"])
    # 封面图（保留此行，否则 Telegram 不显示预览图）
    image_tag = f"<a href='{game['image']}'>&#8205;</a>\n" if game["image"] else ""

    msg = (
        f"{image_tag}"
        f"🆓 <b>Epic Games FREE</b> 🆓\n\n"
        f"🎮 <b>{safe_title}</b>\n"
        f"⏰ Ends: {game['end_date']}\n\n"
        f"📋 {safe_desc}\n\n"
        f"👉 <a href='{game['link']}'>Claim Now</a>"
    )
    return msg
```

提交后下次运行即生效。

---

## 故障排查

### 运行成功但没收到消息？ ⭐ 最常见

去重机制正常工作——当前免费游戏已上架超过 28 小时，脚本自动跳过。日志显示 `😴` 即说明一切正常。

**验证：** 先给机器人发条消息确认通路，等**周四 23:00 后**（Epic 更新）手动 `Run workflow`，收到推送即 OK。

### `❌ 缺少配置`

- Secret 名称必须 `TG_BOT_TOKEN` / `TG_CHAT_ID`（下划线非横杠）
- 无多余空格换行
- 确认加在 **Actions secrets**，不是 Codespaces 或 Dependabot

### `获取 Epic 免费游戏列表失败`

网络波动，脚本已自动重试 3 次。全失败时稍后手动再触发，下次通常自动恢复。

### Actions 无运行记录

1. 确认 `.github/workflows/` 文件存在
2. 确认点过 `I understand my workflows…`
3. 手动 Run workflow 激活

### Keepalive 失败

检查第四步权限是否设为 `Read and write permissions`。

---

## 本地运行

```bash
git clone https://github.com/你的用户名/epic_push.git && cd epic_push
python -m venv venv
source venv/bin/activate      # Linux/macOS
pip install -r requirements.txt
export TG_BOT_TOKEN="你的Token"
export TG_CHAT_ID="你的ChatID"
python main.py
```

> ⚠️ 本地运行**真实调用 API 并发送消息**，确保变量正确。

---

## 项目结构

```
epic_push/
├── .github/workflows/
│   ├── main.yml           # 主工作流：定时 + 手动触发
│   └── keepalive.yml      # 保活：每月自动空 commit
├── main.py                # 核心脚本（263 行）
├── requirements.txt       # 依赖：requests
├── README.md
├── LICENSE                # MIT
└── .gitignore
```

| 文件 | 职责 |
|---|---|
| `main.py` | 调 API → 筛免费 → 去重 → 拼消息 → 发 Telegram |
| `main.yml` | Python 环境 + 定时器 + Secrets 注入 |
| `keepalive.yml` | 每月自动 commit，防 GitHub 60 天暂停 |
| `requirements.txt` | 仅 `requests` 一个依赖 |

---

## 常见问题 FAQ

<details>
<summary><b>每天什么时候自动运行？</b></summary>

每天 **北京时间 10:00**（UTC 02:00），可能有 5~30 分钟调度延迟，正常。
</details>

<details>
<summary><b>为什么去重窗口是 28 小时？</b></summary>

留 4 小时冗余应对 GitHub Actions 调度延迟。设为 24 小时容易漏发。可通过 `NOTIFY_HOURS` 自定义。
</details>

<details>
<summary><b>一周送两款游戏，会收到几条？</b></summary>

每条游戏独立推送一条消息，附带各自封面图和链接。所以是两条。
</details>

<details>
<summary><b>需要定期维护吗？</b></summary>

几乎不需要。Keepalive 每月自动保活。若 Epic 修改 API，关注 Actions 日志——连续报错时回本仓库同步更新。
</details>

<details>
<summary><b>别人能用我的机器人吗？</b></summary>

不能。Token + Chat ID 绑定你的账号。Secrets 在 GitHub 加密存储，其他人看不到。
</details>

<details>
<summary><b>能推送到微信/钉钉吗？</b></summary>

当前仅 Telegram。扩展只需在 `send_telegram_message()` 旁加新函数，欢迎 PR。
</details>

<details>
<summary><b>GitHub Actions 免费额度够用吗？</b></summary>

绰绰有余。每月约 31 次运行，每次几秒，用量不到免费额度（2000 分钟/月）的 1%。
</details>

<details>
<summary><b>Token 泄露了怎么办？</b></summary>

去 Telegram 找 `@BotFather`，发送 `/revoke` 吊销旧 Token 并生成新的，然后在 GitHub Secrets 更新。
</details>

---

## 许可证 & 致谢

MIT License · 自由使用、修改、分发。

参考并改进自 [wwxseo/epic-](https://github.com/wwxseo/epic-)，感谢原作者。

| 改进点 | 说明 |
|---|---|
| 🔄 自动重试 | 网络请求失败 3 次指数退避重试 |
| 🕐 现代时区 API | `timezone-aware datetime` 替代已弃用的 `utcnow()` |
| 📝 结构化日志 | `logging` 模块替代裸 `print()` |
| ⚙️ 可配置窗口 | `NOTIFY_HOURS` 环境变量，无需改代码 |
| 🧩 消息解耦 | `build_message()` 独立函数，易自定义 |
| 🐍 版本升级 | Python 3.11+，最新 GitHub Actions runner |

---

<p align="center">
  ⭐ 如果这个项目帮到了你，给个 Star 支持一下！<br>
  <a href="https://github.com/wyhc7/epic_push">
    <img src="https://img.shields.io/github/stars/wyhc7/epic_push?style=social" alt="Stars">
  </a>
</p>