# 🎮 epic_push — Epic 免费游戏多通道通知机器人

<p align="center">
  <b>零服务器 · 零费用 · 零代码基础 · Fork 即用</b><br>
  <img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License">
  <img src="https://img.shields.io/badge/platform-GitHub_Actions-orange.svg" alt="Platform">
  <img src="https://img.shields.io/badge/推送渠道-15_种-purple.svg" alt="Channels">
  <img src="https://img.shields.io/badge/schedule-每天10:00_北京时间-brightgreen.svg" alt="Schedule">
</p>

---

基于 **GitHub Actions** 的全自动脚本，每天检测 **Epic Games Store** 免费游戏，第一时间推送到你指定的 **15 种渠道**（Telegram、企业微信、钉钉、飞书、微信、邮件、iOS 推送……任选其一或全开）。无需服务器、无需写代码，Fork + 填配置 = 永久运行。

---

## 📑 目录

- [支持的推送渠道](#支持的推送渠道)
- [工作原理](#工作原理)
- [🚀 部署教程（5 步）](#-部署教程5-步)
- [渠道配置大全](#渠道配置大全)
- [自定义配置](#自定义配置)
- [🛡️ 保活机制说明](#️-保活机制说明)
- [故障排查](#故障排查)
- [本地运行](#本地运行)
- [项目结构](#项目结构)
- [常见问题 FAQ](#常见问题-faq)

---

## 支持的推送渠道

**配置了谁，就推给谁。** 默认 `auto` 模式会自动探测所有「凭证齐全」的渠道并同时推送——想推几个就配几个，不需要的留空即可。

| # | 渠道 | 标识 | 需要配置 | 适合谁 |
|---|---|---|---|---|
| 1 | ✈️ **Telegram** | `telegram` | `TG_BOT_TOKEN` `TG_CHAT_ID` | 有梯子，想要封面图预览 |
| 2 | 🏢 **企业微信群机器人** | `wecom` | `WECOM_WEBHOOK` | 国内最省事，图文卡片 |
| 3 | 📌 **钉钉机器人** | `dingtalk` | `DINGTALK_WEBHOOK` `DINGTALK_SECRET` | 钉钉用户，支持封面图 |
| 4 | 🕊️ **飞书机器人** | `feishu` | `FEISHU_WEBHOOK` `FEISHU_SECRET` | 飞书用户，交互式卡片 + 按钮 |
| 5 | 📨 **Server 酱** | `serverchan` | `SERVERCHAN_SENDKEY` | 想推送到**微信**，最简单 |
| 6 | 📮 **PushPlus** | `pushplus` | `PUSHPLUS_TOKEN` | 推送到**微信**，支持 Markdown |
| 7 | 🍎 **Bark** | `bark` | `BARK_KEY` | iPhone 用户，带封面图标 |
| 8 | 🔔 **ntfy** | `ntfy` | `NTFY_TOPIC` | 全平台开源方案，无需注册 |
| 9 | 🚀 **Gotify** | `gotify` | `GOTIFY_URL` `GOTIFY_TOKEN` | 有自建服务器 |
| 10 | 🎯 **Discord** | `discord` | `DISCORD_WEBHOOK` | 游戏社群，富文本 Embed |
| 11 | 💬 **Slack** | `slack` | `SLACK_WEBHOOK` | 团队协作场景 |
| 12 | 🦌 **PushDeer** | `pushdeer` | `PUSHDEER_KEY` | 开源、可自建、支持 iOS |
| 13 | 💚 **WxPusher** | `wxpusher` | `WXPUSHER_APP_TOKEN` `WXPUSHER_UIDS` | 推送到**微信**，支持多人订阅 |
| 14 | 📧 **邮件** | `email` | `SMTP_HOST` `SMTP_USER` `SMTP_PASS` `MAIL_TO` | 邮箱党，HTML 富文本 |
| 15 | 🔗 **通用 Webhook** | `webhook` | `GENERIC_WEBHOOK` | 对接飞书多维表格/n8n/自建服务等 |

> 💡 不确定选哪个？**国内用户推荐 `wecom`（企业微信）或 `serverchan`（微信）**，5 分钟搞定，不需要梯子。

---

## 工作原理

```
每天北京时间 10:00（UTC 02:00）GitHub Actions 自动触发
                        │
         ┌──────────────▼──────────────┐
         │       main.py 执行流程        │
         │                              │
         │  ① 请求 Epic 官方 API         │
         │  ② 遍历全部促销游戏           │
         │  ③ discountPercentage = 0    │
         │     → 100% 折扣 = 完全免费    │
         │  ④ 检查 startDate 上架时间    │
         │     ├ < 28h → 🆕 候选         │
         │     └ ≥ 28h → 📦 跳过         │
         │  ⑤ 查 state.json 去重         │
         │     └ 已推送过 → 跳过         │
         │  ⑥ 渲染消息（按渠道适配格式）  │
         │  ⑦ 并发推送到所有已配置渠道    │
         │  ⑧ 按需提交 state.json（保活）│
         └──────────────┬──────────────┘
                        ▼
          📱 Telegram / 微信 / 钉钉 / 飞书 / 邮件 …
               全部同时收到推送 ✅
```

| 环节 | 实现 |
|---|---|
| 数据来源 | Epic 官方公开接口（无需 Key） |
| 免费判定 | `discountPercentage == 0` |
| 首次过滤 | 上架 < `NOTIFY_HOURS` 小时（默认 28） |
| **二次去重** | `state.json` 记录已推送 gameslug，跨运行持久化 |
| 封面图 | `Thumbnail` 优先，其次 `OfferImageWide`；各渠道按能力渲染 |
| 消息格式 | 一份内容 → 按渠道转成 HTML / Markdown / 卡片 / 纯文本 |
| 网络可靠性 | 3 次指数退避重试；4xx 直接失败不空转 |
| 容错策略 | 日期解析失败 → 默认推送（不漏发） |
| **保活** | 每次运行按需提交 `state.json`，永不被 60 天规则禁用 |

---

## 🚀 部署教程（5 步）

> **需时 10 分钟**，只需 GitHub 账号 + 任意一个推送渠道。

---

### 第一步：准备推送渠道

去 [渠道配置大全](#渠道配置大全) 挑一个，按说明拿到凭证。比如最简单的企业微信：

> 手机/电脑企业微信 → 进入任意群 → 右上角 `···` → `群机器人` → `添加` → 建好后**复制 Webhook 地址**（形如 `https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxxx`）

📋 **你现在应该有：** 至少一个渠道的凭证。

---

### 第二步：Fork 本仓库

> ⏱️ 30 秒

打开 [wyhc7/epic_push](https://github.com/wyhc7/epic_push) → 右上角 **`Fork`** → **`Create fork`**。

---

### 第三步：配置 Secrets

> ⏱️ 2 分钟 | **最关键的一步**

在你 Fork 的仓库中：**`Settings`** ⚙️ → **`Secrets and variables`** → **`Actions`** → **`New repository secret`**。

把第一步拿到的凭证逐个填进去，**名称必须和下表完全一致**：

| 你用的渠道 | 要加的 Secret |
|---|---|
| Telegram | `TG_BOT_TOKEN`、`TG_CHAT_ID` |
| 企业微信 | `WECOM_WEBHOOK` |
| 钉钉 | `DINGTALK_WEBHOOK`（加签再加 `DINGTALK_SECRET`） |
| 飞书 | `FEISHU_WEBHOOK`（加签再加 `FEISHU_SECRET`） |
| Server 酱 | `SERVERCHAN_SENDKEY` |
| PushPlus | `PUSHPLUS_TOKEN` |
| Bark | `BARK_KEY` |
| ntfy | `NTFY_TOPIC` |
| Gotify | `GOTIFY_URL`、`GOTIFY_TOKEN` |
| Discord | `DISCORD_WEBHOOK` |
| Slack | `SLACK_WEBHOOK` |
| PushDeer | `PUSHDEER_KEY` |
| WxPusher | `WXPUSHER_APP_TOKEN`、`WXPUSHER_UIDS` |
| 邮件 | `SMTP_HOST`、`SMTP_USER`、`SMTP_PASS`、`MAIL_TO` |
| 通用 Webhook | `GENERIC_WEBHOOK` |

> ✅ **不想全开？** 默认 `auto` 模式只认「凭证齐全」的渠道，没配的自动跳过，不用管。

---

### 第四步：开启写权限

> ⏱️ 30 秒 | **不做这步，保活会失效**

**`Settings`** → **`Actions`** → **`General`** → **Workflow permissions** → 选 **`Read and write permissions`** → **`Save`**

这是让工作流能把 `state.json` 提交回仓库（= 保活心跳）的必要条件。

---

### 第五步：启动测试

> ⏱️ 2 分钟

1. 仓库顶部点击 **`Actions`** → 点绿色按钮 **`I understand my workflows…`**
2. 左侧选 **`Epic Free Game Notifier`** → 右侧 **`Run workflow`** → **`Run workflow`**
3. 点运行条目 → **`Run Notifier`** → 展开日志：

**成功的样子：**
```
📡 启用渠道: 企业微信群机器人
🔍 发现 2 款符合窗口的免费游戏
📨 推送: Mechabellum (截止: 2026-10-01 15:00 UTC)
   ✅ 企业微信群机器人 推送成功
❤️  刷新心跳时间戳（上次：无）
💾 状态已更新: state.json
✨ 全部完成！
```

| 日志 | 含义 |
|---|---|
| `✅ xxx 推送成功` | 部署成功，手机上应该已经收到了 |
| `😴 当前没有需要推送的新游戏` | **正常**，只是现在没有新游戏 |
| `❌ 没有任何可用渠道` | Secret 没配对，回第三步 |
| `❌ xxx 推送失败` | 看报错信息，对照 [故障排查](#故障排查) |

> 🔍 想知道当前识别到哪些渠道？日志里的 `📡 启用渠道:` 一行就是答案。

---

## 渠道配置大全

<details>
<summary><b>✈️ Telegram</b></summary>

1. Telegram 搜索 **`@BotFather`** → 发 `/newbot` → 按提示创建 → 拿到 **Bot Token**
2. 搜索 **`@userinfobot`** → 点 Start → 回复里的 `Id` 就是 **Chat ID**
3. Secret：`TG_BOT_TOKEN`、`TG_CHAT_ID`

> 群组推送：把机器人拉进群，Chat ID 用群 ID（形如 `-1001234567890`）。
</details>

<details>
<summary><b>🏢 企业微信群机器人（推荐）</b></summary>

1. 企业微信 → 任意群 → 右上角 `···` → **`群机器人`** → **`添加`**
2. 起个名字 → 创建后**复制 Webhook 地址**
3. Secret：`WECOM_WEBHOOK` = 完整地址

> 推送为图文卡片（封面图 + 标题 + 简介 + 点击跳转），手机上体验最好。
</details>

<details>
<summary><b>📌 钉钉机器人</b></summary>

1. 钉钉群 → 右上角 `···` → **`机器人`** → **`添加机器人`** → **`自定义`**
2. **安全设置**（重要，二选一）：
   - **`加签`** → 复制 `SEC` 开头的密钥 → 填进 `DINGTALK_SECRET`
   - **`自定义关键词`** → 填 **`Epic`**（本项目消息标题含 "Epic"，能通过校验）
3. Secret：`DINGTALK_WEBHOOK` = Webhook 地址；用加签再填 `DINGTALK_SECRET`

> 钉钉 markdown 能直接渲染封面图。
</details>

<details>
<summary><b>🕊️ 飞书机器人</b></summary>

1. 飞书群 → 设置 → **`群机器人`** → **`添加机器人`** → **`自定义机器人`**
2. 可选开启**签名校验** → 复制密钥
3. Secret：`FEISHU_WEBHOOK` = Webhook 地址；开启签名再填 `FEISHU_SECRET`

> 推送为交互式卡片（标题栏 + Markdown + 「点击领取」按钮）。
</details>

<details>
<summary><b>📨 Server 酱（微信，最省事）</b></summary>

1. 打开 [sct.ftqq.com](https://sct.ftqq.com) → 微信扫码登录
2. 复制页面上的 **SendKey**（`SCT` 开头）
3. Secret：`SERVERCHAN_SENDKEY`

> 免费版每天有限额，对每天 1~2 条的通知绰绰有余。
</details>

<details>
<summary><b>📮 PushPlus（微信）</b></summary>

1. 打开 [pushplus.plus](https://www.pushplus.plus) → 微信扫码登录
2. **`一对一推送`** → 复制 **Token**
3. Secret：`PUSHPLUS_TOKEN`
</details>

<details>
<summary><b>🍎 Bark（iOS）</b></summary>

1. App Store 搜 **`Bark`** 安装（免费）
2. 打开 App，首页那串地址里的最后一段就是你的 **Key**
3. Secret：`BARK_KEY`

> 自建服务器：额外加 `BARK_SERVER`，例如 `https://bark.yourdomain.com`。
</details>

<details>
<summary><b>🔔 ntfy（全平台开源）</b></summary>

1. 装 **ntfy** App（iOS / Android / 桌面端），或用网页版 [ntfy.sh](https://ntfy.sh)
2. 自己想一个**足够随机**的 topic 名，比如 `epic-8f3k2n9q`（相当于密码，别用太简单的）
3. App 里订阅同一个 topic
4. Secret：`NTFY_TOPIC`

> 自建：加 `NTFY_SERVER`；开了鉴权再加 `NTFY_TOKEN`。
</details>

<details>
<summary><b>🚀 Gotify（自建）</b></summary>

1. 在你的 Gotify 服务器里 **`Apps`** → **`Create Application`**
2. Secret：`GOTIFY_URL` = 服务器地址（如 `https://gotify.example.com`）、`GOTIFY_TOKEN` = 生成的 Token
</details>

<details>
<summary><b>🎯 Discord</b></summary>

1. 频道设置 → **`整合`** → **`Webhook`** → **`新 Webhook`** → 复制 Webhook URL
2. Secret：`DISCORD_WEBHOOK`

> 推送为 Embed 富文本卡片，带封面大图。
</details>

<details>
<summary><b>💬 Slack</b></summary>

1. [api.slack.com/apps](https://api.slack.com/apps) → Create New App → **`Incoming Webhooks`** → 开启 → **`Add New Webhook to Workspace`**
2. 复制 Webhook URL
3. Secret：`SLACK_WEBHOOK`
</details>

<details>
<summary><b>🦌 PushDeer</b></summary>

1. [pushdeer.com](https://www.pushdeer.com) 或自建服务 → 获取 **Key**
2. Secret：`PUSHDEER_KEY`；自建再加 `PUSHDEER_URL`
</details>

<details>
<summary><b>💚 WxPusher（微信，支持多人）</b></summary>

1. [wxpusher.zjiecode.com](https://wxpusher.zjiecode.com) → 微信登录 → **`应用管理`** → 创建应用 → 复制 **appToken**
2. 用微信关注你的应用二维码，在 **`用户管理`** 里看到 **UID**（形如 `UID_xxxxx`）
3. Secret：`WXPUSHER_APP_TOKEN`、`WXPUSHER_UIDS`（多个用英文逗号隔开）

> 想推给一群人？把多个 UID 用逗号填进 `WXPUSHER_UIDS` 就行。
</details>

<details>
<summary><b>📧 邮件（SMTP）</b></summary>

以 QQ 邮箱为例：

1. QQ 邮箱 → 设置 → 账户 → 开启 **SMTP 服务** → 生成 **授权码**（不是登录密码！）
2. Secrets：
   | Name | 值 |
   |---|---|
   | `SMTP_HOST` | `smtp.qq.com` |
   | `SMTP_PORT` | `465` |
   | `SMTP_USER` | `你的QQ号@qq.com` |
   | `SMTP_PASS` | 刚生成的授权码 |
   | `MAIL_TO` | 收件邮箱（多个用逗号隔开） |

> 163 邮箱：`SMTP_HOST` = `smtp.163.com`，端口同样 465。
</details>

<details>
<summary><b>🔗 通用 Webhook（对接任意服务）</b></summary>

会向你指定的地址 POST 一段 JSON：

```json
{
  "title": "🆓 Epic Games 限时免费 ｜ 截止 2026-10-01 15:00 UTC",
  "summary": "游戏简介…",
  "content": "Markdown 正文",
  "plain": "纯文本正文",
  "url": "https://store.epicgames.com/p/xxx",
  "image": "封面图 URL",
  "end_date": "2026-10-01 15:00 UTC",
  "game": "Mechabellum"
}
```

| Secret | 说明 |
|---|---|
| `GENERIC_WEBHOOK` | 目标地址 |
| `GENERIC_WEBHOOK_METHOD` | 可选，默认 `POST` |
| `GENERIC_WEBHOOK_HEADERS` | 可选，JSON 字符串，如 `{"Authorization":"Bearer xxx"}` |

> 适合接 n8n、Node-RED、自建 Bot、飞书多维表格自动化等。
</details>

---

## 自定义配置

### 只启用指定渠道

**Settings → Secrets and variables → Actions → Variables** → **New variable**：

| Name | Value | 效果 |
|---|---|---|
| `PUSH_CHANNELS` | （留空 / `auto`） | 默认：自动启用所有配好的渠道 |
| `PUSH_CHANNELS` | `wecom` | 只推企业微信 |
| `PUSH_CHANNELS` | `wecom,serverchan,email` | 同时推这 3 个 |
| `PUSH_CHANNELS` | `all` | 强制尝试全部（缺配置的会报错跳过） |

### 修改通知窗口

| Name | Value | 含义 |
|---|---|---|
| `NOTIFY_HOURS` | `24` | 仅推送 1 天内上架的 |
| `NOTIFY_HOURS` | `28` | 默认（推荐，留了调度延迟冗余） |
| `NOTIFY_HOURS` | `168` | 推送一周内上架的 |

> 有 `state.json` 兜底去重后，把窗口放宽（比如 168）也**不会重复推送**同一款游戏，只是会补推"你刚 Fork 时正在免费中"的游戏。

### 调整保活心跳频率

| Name | Value | 含义 |
|---|---|---|
| `HEARTBEAT_DAYS` | `15` | 默认，最多 15 天必有一次 commit（远低于 GitHub 的 60 天红线） |
| `HEARTBEAT_DAYS` | `7` | 更频繁，适合想每天都看到仓库有动静的强迫症 |

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
| `0 16 * * 4` | 周五 00:00 | Epic 周四晚更新后第一时间 |

> ⚠️ cron 是 UTC 时间，北京时间 = UTC + 8。

### 自定义消息文案

编辑 `main.py` 的 `build_message()` 函数，里面有 `markdown` / `html` / `plain` 三种版本，分别给不同渠道用：

```python
markdown = (
    f"🆓 **Epic Games 限时免费**\n\n"
    f"🎮 **{title}**\n"
    f"⏰ 截止：{end}\n\n"
    f"📋 {desc}\n\n"
    f"👉 [点击此处领取]({link})"
)
```

改完提交，下次运行生效。

---

## 🛡️ 保活机制说明

这一节解释**为什么旧的保活会失效**，以及现在**为什么不会再失效**。

### GitHub 的规则

> 公开仓库连续 **60 天没有 commit 被 push**，GitHub 会自动**静默禁用**该仓库所有由 `schedule` 触发的工作流。
> —— 不发邮件、不发通知、UI 上也不显眼，到点就是不跑。

注意"活动"的定义非常窄：**只有 push commit 算数**，提 Issue、发评论、改 Wiki 都不算。

### 旧版为什么会失效（3 个坑）

| # | 问题 | 后果 |
|---|---|---|
| 1 | 保活工作流**每月 1 号才跑一次** | 而第三方保活 Action 的默认阈值是"距上次 commit 满 50 天才提交"。于是 1 号跑时可能才 30 天 → 判定"还不用保活"，什么都不做；等下个月 1 号，已经 60 天 → **工作流此时已被禁用，根本不会触发**。死锁。 |
| 2 | 保活工作流**自己也是 `schedule` 触发** | 一旦被禁用，它自己也停了，**无法自救**。 |
| 3 | 判断逻辑依赖第三方 Action 的默认参数 | 版本变更 / 上游行为变化，你完全不知情。 |

### 现在是怎么修的

**核心思路：让保活不再依赖"保活工作流"，而是让主流程天然产生活动。**

```
主工作流每次运行
      │
      ├─ 有游戏推送 → 更新 state.json → 有变化 → 提交 ✅
      │
      └─ 没游戏推送 → 检查上次心跳距今是否 ≥ HEARTBEAT_DAYS(15 天)
                        ├ 是 → 刷新 last_heartbeat → 提交 ✅
                        └ 否 → 不改动，不提交（保持提交历史干净）
```

于是：

- 📌 **最多 15 天必有一次 commit** —— 远低于 60 天红线，计时器永远被重置；
- 📌 **不依赖任何第三方 Action** —— 零供应链风险，行为 100% 可预测；
- 📌 **提交历史依然清爽** —— 只在必要时提交，不是每天硬造一条垃圾 commit。

而 `.github/workflows/keepalive.yml` 降级为**第二层保险**：每周一检查一次，如果发现距上次 commit 已经超过 30 天（说明主工作流长期没跑成功，比如 Epic 改了 API 而你没同步上游），就补一个心跳提交兜底。

### 如果已经被禁用了，怎么救回来

1. 打开仓库 **`Actions`** 页面 → 左侧点开被禁用的工作流 → 右上角会有 **`Enable workflow`** 按钮，点一下即可；
2. 或者随便往仓库推一个 commit（改改 README 都行），定时任务会一并被重新激活。

> 💡 **核弹级方案**：`workflow_dispatch` 触发器**不会**被 60 天规则禁用。你可以用 [cron-job.org](https://cron-job.org) / UptimeRobot 之类的免费外部定时服务，定期调用 GitHub API 手动触发工作流，做到 100% 不依赖仓库活动状态。本项目默认不启用，因为上面两层机制已经足够。

---

## 故障排查

### 运行成功但没收到消息？ ⭐ 最常见

先看日志里的 **`📡 启用渠道:`** 一行 —— 你要的渠道在不在里面？

- **不在** → 该渠道的 Secret 没配齐或名字拼错了，回 [渠道配置大全](#渠道配置大全) 对照。
- **在，但日志显示 `😴 当前没有需要推送的新游戏`** → 正常，当前确实没有符合窗口的新游戏。
- **在，日志显示 `⏭️ 已在 xxx 推送过，跳过`** → 正常，`state.json` 去重生效了。

**快速验证通路**：把 Variable `NOTIFY_HOURS` 临时改成 `100000`，然后手动 `Run workflow` —— 这样会把当前所有免费中的游戏都推一遍（去重表是空的就会全推）。验证完记得改回来。

### `❌ 缺少配置 xxx`

- Secret 名称必须**大小写 + 下划线完全一致**，且不能有多余空格换行；
- 必须加在 **Actions secrets**，不是 Codespaces 或 Dependabot；
- 变量类配置（`PUSH_CHANNELS` / `NOTIFY_HOURS` / `HEARTBEAT_DAYS`）加在 **Variables**，不是 Secrets。

### 钉钉报 `keywords not in content` / `sign not match`

- 用了**自定义关键词**模式：关键词必须是 **`Epic`**（消息标题里含这个词）；
- 用了**加签**模式：`DINGTALK_SECRET` 必须填 `SEC` 开头那串；
- 两者不能混着来，按机器人设置里实际启用的那种填。

### 飞书报 `sign match fail`

`FEISHU_SECRET` 填错了，或机器人**没有**开启签名校验但你还是填了 secret —— 后者请把 `FEISHU_SECRET` 删掉。

### `获取 Epic 免费游戏列表失败`

网络波动，脚本已自动重试 3 次。全失败时稍后手动再触发，下次通常自动恢复。

### Actions 无运行记录

1. 确认 `.github/workflows/` 文件存在；
2. 确认点过 `I understand my workflows…`；
3. 手动 `Run workflow` 激活一次。

### `Persist state` 步骤报 `403` / `Permission denied`

第四步的 Workflow permissions 没设成 **`Read and write permissions`**。设完重新跑一次即可。

### 保活相关的问题

见上面的 [保活机制说明](#️-保活机制说明)。

---

## 本地运行

```bash
git clone https://github.com/你的用户名/epic_push.git && cd epic_push
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 看看支持哪些渠道
python main.py --list-channels

# 干跑：真实调 Epic API，但只打印不发送
DRY_RUN=1 PUSH_CHANNELS=telegram TG_BOT_TOKEN=x TG_CHAT_ID=y python main.py

# 真实发送
export WECOM_WEBHOOK="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx"
python main.py
```

| 环境变量 | 作用 |
|---|---|
| `DRY_RUN=1` | 只打印消息内容，不真的发送 |
| `PUSH_CHANNELS` | 覆盖渠道选择，如 `wecom,email` |
| `STATE_FILE` | 自定义状态文件路径（默认 `./state.json`） |

> ⚠️ 不带 `DRY_RUN=1` 本地运行会**真实发送**，确保变量正确。

---

## 项目结构

```
epic_push/
├── .github/workflows/
│   ├── main.yml           # 主工作流：定时 + 手动触发 + 状态提交（保活）
│   └── keepalive.yml      # 兜底保活：每周自查，30 天无提交则补心跳
├── channels.py            # 15 种推送渠道的实现与注册表
├── main.py                # 核心逻辑：拉数据 → 去重 → 渲染 → 分发
├── state.json             # 推送记录 + 心跳时间戳（由工作流自动维护）
├── requirements.txt       # 依赖：requests
├── README.md
├── LICENSE                # MIT
└── .gitignore
```

| 文件 | 职责 |
|---|---|
| `main.py` | 调 API → 筛免费 → 去重 → 拼消息 → 分发给各渠道 → 维护 state.json |
| `channels.py` | 每个渠道一个类，负责凭证校验、消息格式适配、错误处理 |
| `main.yml` | Python 环境 + 定时器 + Secrets 注入 + 提交 state.json |
| `keepalive.yml` | 每周兜底检查，防止主流程长期失效导致仓库被判定不活跃 |
| `state.json` | 去重表 + 心跳时间戳，是保活机制的载体 |

---

## 常见问题 FAQ

<details>
<summary><b>每天什么时候自动运行？</b></summary>

每天 **北京时间 10:00**（UTC 02:00），可能有 5~30 分钟调度延迟，正常。

想更早收到？改 cron 到 `0 16 * * 4`（北京时间周五 00:00），正好赶上 Epic 周四晚更新。
</details>

<details>
<summary><b>可以同时推送到多个渠道吗？</b></summary>

可以，而且是**默认行为**。默认 `auto` 模式会探测所有凭证齐全的渠道，同时推送。

想精确控制就设 Variable `PUSH_CHANNELS=wecom,serverchan,email`。
</details>

<details>
<summary><b>能推送到微信吗？</b></summary>

可以，有 3 种方式：**Server 酱**（`serverchan`）、**PushPlus**（`pushplus`）、**WxPusher**（`wxpusher`）。

三者都不需要梯子，Server 酱和 PushPlus 最简单，WxPusher 适合推给多个人。
</details>

<details>
<summary><b>为什么去重窗口是 28 小时？</b></summary>

留 4 小时冗余应对 GitHub Actions 的调度延迟。设为 24 小时容易漏发。

而且现在有 `state.json` 二次去重，把窗口调宽到 168 小时也**不会重复推送**同一款游戏。
</details>

<details>
<summary><b>state.json 是干什么的？可以删吗？</b></summary>

它存两样东西：**已推送过的游戏列表**（跨运行去重）和**上次心跳时间**（保活）。

删掉不会报错（脚本会自动重建），但会丢失去重记录，可能导致同一款游戏被重推一次，并且下一次运行会重新开始计算心跳周期。**建议不要手动删。**
</details>

<details>
<summary><b>一周送两款游戏，会收到几条？</b></summary>

每条游戏独立推送一条消息，附带各自封面图和链接。所以是两条。
</details>

<details>
<summary><b>需要定期维护吗？</b></summary>

几乎不需要。保活现在是内建的，不依赖外部 Action。

唯一需要留意的是：如果 Epic 改了 API 接口，主工作流会连续报错。关注 Actions 日志或回本仓库同步更新即可（`keepalive.yml` 会在此期间兜底保活，不会让定时任务被禁用）。
</details>

<details>
<summary><b>别人能用我的机器人的吗？</b></summary>

不能。所有凭证都绑定你的账号，且加密存储在 GitHub Secrets 里，其他人（包括 Fork 你仓库的人）都看不到。

如果你 Fork 了本仓库，记得**不要**把自己的凭证写进代码文件里。
</details>

<details>
<summary><b>GitHub Actions 免费额度够用吗？</b></summary>

绰绰有余。每月约 31 次运行，每次几秒，用量不到免费额度（公开仓库完全免费、私有仓库 2000 分钟/月）的 1%。
</details>

<details>
<summary><b>凭证泄露了怎么办？</b></summary>

去对应平台吊销并重新生成，然后在 GitHub Secrets 里更新：

| 渠道 | 吊销方式 |
|---|---|
| Telegram | 找 `@BotFather` 发 `/revoke` |
| 企业微信 / 钉钉 / 飞书 | 群机器人设置里删除后重新创建 |
| Server 酱 / PushPlus / Bark | 网页后台重置 Token |
| 邮件 | 重新生成授权码 |
</details>

---

## 许可证 & 致谢

MIT License · 自由使用、修改、分发。

参考并改进自 [wwxseo/epic-](https://github.com/wwxseo/epic-)，感谢原作者。

| 改进点 | 说明 |
|---|---|
| 🧩 **15 种推送渠道** | 从仅有 Telegram 扩展到覆盖国内主流 IM、微信推送、iOS 推送、邮件、Webhook |
| 🛡️ **保活机制重做** | 从"每月一次 + 依赖第三方 Action"改为"主流程内建心跳 + 每周兜底"，彻底解决 60 天禁用 |
| 💾 **状态持久化** | `state.json` 跨运行去重，不再重复推送同一款游戏 |
| 🌐 **网络重试优化** | 4xx 客户端错误立即失败，不再无意义重试；5xx / 429 才退避重试 |
| 🔍 **可自检** | `python main.py --list-channels` 列出所有渠道及其配置要求 |
| 🧪 **DRY_RUN** | 支持干跑预览，不发送也能看到消息长什么样 |
| 🕐 现代时区 API | `timezone-aware datetime` 替代已弃用的 `utcnow()` |
| 📝 结构化日志 | `logging` 模块替代裸 `print()` |
| ⚙️ 可配置窗口 | `NOTIFY_HOURS` 环境变量，无需改代码 |
| 🧩 消息解耦 | `build_message()` 输出三种格式，各渠道按需取用 |
| 🐍 版本升级 | Python 3.11+，最新 GitHub Actions runner |

---

<p align="center">
  ⭐ 如果这个项目帮到了你，给个 Star 支持一下！<br>
  <a href="https://github.com/wyhc7/epic_push">
    <img src="https://img.shields.io/github/stars/wyhc7/epic_push?style=social" alt="Stars">
  </a>
</p>
