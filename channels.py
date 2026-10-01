#!/usr/bin/env python3
"""
多推送渠道 —— epic_push

每个渠道实现 BaseChannel 接口并在 REGISTRY 中注册。
启用方式由环境变量 PUSH_CHANNELS 控制：

    auto    （默认）自动启用所有「凭证齐全」的渠道
    all     尝试启用全部渠道（缺凭证的会报错跳过）
    telegram,wecom,feishu,...   仅启用指定渠道（逗号分隔）

每个渠道只读取自己需要的环境变量，因此可以任意组合、同时推送到多个渠道。
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import smtplib
import time
import urllib.parse
from dataclasses import dataclass
from email.header import Header
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import Dict, List, Type

import requests

log = logging.getLogger("epic-notifier")

# ─────────────────────────────────────────────
# 网络请求：3 次指数退避重试
# ─────────────────────────────────────────────
MAX_RETRIES = 3
RETRY_BACKOFF = 2
TIMEOUT = 20


def request_with_retry(
    method: str,
    url: str,
    *,
    retries: int = MAX_RETRIES,
    backoff: int = RETRY_BACKOFF,
    timeout: int = TIMEOUT,
    **kwargs,
):
    """
    带自动重试的 HTTP 请求。

    - 网络错误 / 5xx / 429：指数退避重试
    - 4xx（除 429）：客户端错误，立即抛出，不做无意义重试
    """
    last_exc: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            resp = requests.request(method, url, timeout=timeout, **kwargs)
        except Exception as exc:  # 连接超时、DNS 失败等
            last_exc = exc
        else:
            if resp.status_code < 400:
                return resp
            if resp.status_code != 429 and 400 <= resp.status_code < 500:
                # 凭证错误 / 参数错误 —— 重试也是白搭，直接失败
                raise requests.HTTPError(
                    f"HTTP {resp.status_code} {resp.reason}: {resp.text[:300]}",
                    response=resp,
                )
            last_exc = requests.HTTPError(
                f"HTTP {resp.status_code} {resp.reason}: {resp.text[:300]}",
                response=resp,
            )

        if attempt < retries:
            wait = backoff ** attempt
            log.warning(
                "请求失败 (%d/%d) %s ｜ %ss 后重试…", attempt, retries, last_exc, wait
            )
            time.sleep(wait)

    raise last_exc  # type: ignore[misc]


# ─────────────────────────────────────────────
# 消息载体
# ─────────────────────────────────────────────
@dataclass
class Message:
    """一条渲染好的通知，各渠道按需取用其中的字段。"""

    title: str        # 纯文本标题，如 "Epic 免费：《XXX》"
    game: str         # 游戏名
    summary: str      # 一句话纯文本摘要
    markdown: str     # Markdown 正文
    html: str         # HTML 正文（Telegram / 邮件）
    plain: str        # 纯文本正文
    link: str         # 领取链接
    image: str        # 封面图 URL
    end_date: str     # 截止时间


# ─────────────────────────────────────────────
# 渠道基类
# ─────────────────────────────────────────────
class BaseChannel:
    """所有推送渠道的基类。"""

    name: str = ""            # 稳定标识（PUSH_CHANNELS 里写这个）
    label: str = ""           # 中文展示名
    doc: str = ""             # 需要的配置项，仅用于日志/文档
    required: List[str] = []  # 必须齐全才算「已配置」的环境变量

    @classmethod
    def is_configured(cls, env: Dict[str, str] | None = None) -> bool:
        env = env if env is not None else os.environ
        return all((env.get(k) or "").strip() for k in cls.required)

    @classmethod
    def missing(cls, env: Dict[str, str] | None = None) -> List[str]:
        env = env if env is not None else os.environ
        return [k for k in cls.required if not (env.get(k) or "").strip()]

    def send(self, msg: Message) -> None:  # pragma: no cover - 抽象方法
        raise NotImplementedError


REGISTRY: Dict[str, Type[BaseChannel]] = {}


def register(cls: Type[BaseChannel]) -> Type[BaseChannel]:
    """把渠道类登记进全局注册表。"""
    REGISTRY[cls.name] = cls
    return cls


# ─────────────────────────────────────────────
# 小工具
# ─────────────────────────────────────────────
def _env(key: str, default: str = "") -> str:
    return (os.environ.get(key) or default).strip()


def _clip(text: str, limit: int) -> str:
    """按字符数截断，避免超过各平台的消息长度上限。"""
    return text if len(text) <= limit else text[: limit - 20] + "\n…（内容过长已截断）"


def _post_json(url: str, payload: dict, label: str, *, params=None, headers=None):
    """POST JSON 并校验响应中的业务错误码。"""
    resp = request_with_retry(
        "POST",
        url,
        json=payload,
        params=params,
        headers=headers or {"Content-Type": "application/json"},
    )
    try:
        data = resp.json()
    except Exception:
        return resp

    # 各平台五花八门的"成功码"，统一做一次体检
    code = data.get("code", data.get("errcode", data.get("StatusCode", 0)))
    ok = data.get("ok", True)
    if data.get("errcode") not in (None, 0) or (
        isinstance(code, int) and code not in (0, 200)
    ) or ok is False:
        raise RuntimeError(f"{label} 返回错误: {json.dumps(data, ensure_ascii=False)[:300]}")
    return resp


# ─────────────────────────────────────────────
# 1. Telegram
# ─────────────────────────────────────────────
@register
class TelegramChannel(BaseChannel):
    name = "telegram"
    label = "Telegram Bot"
    doc = "TG_BOT_TOKEN, TG_CHAT_ID"
    required = ["TG_BOT_TOKEN", "TG_CHAT_ID"]

    def send(self, msg: Message) -> None:
        url = f"https://api.telegram.org/bot{_env('TG_BOT_TOKEN')}/sendMessage"
        # 零宽字符超链接 → 触发 Telegram 的链接预览，从而显示封面图
        image_tag = f"<a href='{msg.image}'>&#8205;</a>\n" if msg.image else ""
        payload = {
            "chat_id": _env("TG_CHAT_ID"),
            "text": image_tag + _clip(msg.html, 4000),
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        }
        resp = request_with_retry("POST", url, json=payload)
        data = resp.json()
        if not data.get("ok"):
            raise RuntimeError(f"Telegram 返回错误: {data.get('description')}")


# ─────────────────────────────────────────────
# 2. 企业微信群机器人
# ─────────────────────────────────────────────
@register
class WeComChannel(BaseChannel):
    name = "wecom"
    label = "企业微信群机器人"
    doc = "WECOM_WEBHOOK"
    required = ["WECOM_WEBHOOK"]

    def send(self, msg: Message) -> None:
        article = {
            "title": _clip(msg.title, 120),
            "description": _clip(msg.summary, 480),
            "url": msg.link,
        }
        if msg.image:
            article["picurl"] = msg.image
        _post_json(
            _env("WECOM_WEBHOOK"),
            {"msgtype": "news", "news": {"articles": [article]}},
            "企业微信",
        )


# ─────────────────────────────────────────────
# 3. 钉钉机器人
# ─────────────────────────────────────────────
@register
class DingTalkChannel(BaseChannel):
    name = "dingtalk"
    label = "钉钉机器人"
    doc = "DINGTALK_WEBHOOK, DINGTALK_SECRET（可选）"
    required = ["DINGTALK_WEBHOOK"]

    def send(self, msg: Message) -> None:
        params = {}
        secret = _env("DINGTALK_SECRET")
        if secret:
            ts = str(round(time.time() * 1000))
            digest = hmac.new(
                secret.encode("utf-8"),
                f"{ts}\n{secret}".encode("utf-8"),
                hashlib.sha256,
            ).digest()
            params = {
                "timestamp": ts,
                "sign": urllib.parse.quote_plus(base64.b64encode(digest)),
            }
        _post_json(
            _env("DINGTALK_WEBHOOK"),
            {
                "msgtype": "markdown",
                "markdown": {
                    "title": msg.title,
                    # 钉钉的 markdown 能直接渲染图片，这里补上封面
                    "text": _clip(
                        (f"![封面]({msg.image})\n\n" if msg.image else "") + msg.markdown,
                        4000,
                    ),
                },
            },
            "钉钉",
            params=params,
        )


# ─────────────────────────────────────────────
# 4. 飞书机器人
# ─────────────────────────────────────────────
@register
class FeishuChannel(BaseChannel):
    name = "feishu"
    label = "飞书机器人"
    doc = "FEISHU_WEBHOOK, FEISHU_SECRET（可选）"
    required = ["FEISHU_WEBHOOK"]

    def send(self, msg: Message) -> None:
        payload = {
            "msg_type": "interactive",
            "card": {
                "config": {"wide_screen_mode": True},
                "header": {
                    "template": "blue",
                    "title": {"tag": "plain_text", "content": _clip(msg.title, 60)},
                },
                "elements": [
                    {"tag": "div", "text": {"tag": "lark_md", "content": msg.markdown}},
                    {
                        "tag": "action",
                        "actions": [
                            {
                                "tag": "button",
                                "type": "primary",
                                "text": {"tag": "plain_text", "content": "点击领取"},
                                "url": msg.link,
                            }
                        ],
                    },
                ],
            },
        }
        secret = _env("FEISHU_SECRET")
        if secret:
            ts = str(int(time.time()))
            digest = hmac.new(
                f"{ts}\n{secret}".encode("utf-8"), digestmod=hashlib.sha256
            ).digest()
            payload["timestamp"] = ts
            payload["sign"] = base64.b64encode(digest).decode("utf-8")
        _post_json(_env("FEISHU_WEBHOOK"), payload, "飞书")


# ─────────────────────────────────────────────
# 5. Server 酱
# ─────────────────────────────────────────────
@register
class ServerChanChannel(BaseChannel):
    name = "serverchan"
    label = "Server 酱"
    doc = "SERVERCHAN_SENDKEY"
    required = ["SERVERCHAN_SENDKEY"]

    def send(self, msg: Message) -> None:
        url = f"https://sctapi.ftqq.com/{_env('SERVERCHAN_SENDKEY')}.send"
        resp = request_with_retry(
            "POST", url, data={"title": msg.title, "desp": msg.markdown}
        )
        data = resp.json()
        errno = (data.get("data") or {}).get("errno")
        if data.get("code") not in (0, None) or errno not in (None, 0):
            raise RuntimeError(f"Server 酱返回错误: {data}")


# ─────────────────────────────────────────────
# 6. PushPlus
# ─────────────────────────────────────────────
@register
class PushPlusChannel(BaseChannel):
    name = "pushplus"
    label = "PushPlus"
    doc = "PUSHPLUS_TOKEN"
    required = ["PUSHPLUS_TOKEN"]

    def send(self, msg: Message) -> None:
        _post_json(
            "https://www.pushplus.plus/send",
            {
                "token": _env("PUSHPLUS_TOKEN"),
                "title": msg.title,
                "content": msg.markdown,
                "template": "markdown",
            },
            "PushPlus",
        )


# ─────────────────────────────────────────────
# 7. Bark（iOS）
# ─────────────────────────────────────────────
@register
class BarkChannel(BaseChannel):
    name = "bark"
    label = "Bark（iOS）"
    doc = "BARK_KEY, BARK_SERVER（可选，自建用）"
    required = ["BARK_KEY"]

    def send(self, msg: Message) -> None:
        server = (_env("BARK_SERVER") or "https://api.day.app").rstrip("/")
        payload = {
            "device_key": _env("BARK_KEY"),
            "title": msg.title,
            "body": msg.summary,
            "url": msg.link,
            "group": "Epic 免费游戏",
            "level": "active",
        }
        if msg.image:
            payload["icon"] = msg.image
        _post_json(f"{server}/push", payload, "Bark")


# ─────────────────────────────────────────────
# 8. ntfy
# ─────────────────────────────────────────────
@register
class NtfyChannel(BaseChannel):
    name = "ntfy"
    label = "ntfy"
    doc = "NTFY_TOPIC, NTFY_SERVER（可选）, NTFY_TOKEN（可选）"
    required = ["NTFY_TOPIC"]

    def send(self, msg: Message) -> None:
        server = (_env("NTFY_SERVER") or "https://ntfy.sh").rstrip("/")
        payload = {
            "topic": _env("NTFY_TOPIC"),
            "title": msg.title,
            "message": msg.markdown,
            "markdown": True,
            "click": msg.link,
            "tags": ["video_game", "gift"],
        }
        headers = {}
        token = _env("NTFY_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        # 用 JSON 发布端点，避免中文标题在 HTTP header 里被拒
        _post_json(server, payload, "ntfy", headers=headers or None)


# ─────────────────────────────────────────────
# 9. Gotify（自建）
# ─────────────────────────────────────────────
@register
class GotifyChannel(BaseChannel):
    name = "gotify"
    label = "Gotify（自建）"
    doc = "GOTIFY_URL, GOTIFY_TOKEN"
    required = ["GOTIFY_URL", "GOTIFY_TOKEN"]

    def send(self, msg: Message) -> None:
        url = f"{_env('GOTIFY_URL').rstrip('/')}/message"
        _post_json(
            url,
            {
                "title": msg.title,
                "message": msg.markdown,
                "priority": 5,
                "extras": {
                    "client::notification": {"click": {"url": msg.link}},
                },
            },
            "Gotify",
            params={"token": _env("GOTIFY_TOKEN")},
        )


# ─────────────────────────────────────────────
# 10. Discord
# ─────────────────────────────────────────────
@register
class DiscordChannel(BaseChannel):
    name = "discord"
    label = "Discord Webhook"
    doc = "DISCORD_WEBHOOK"
    required = ["DISCORD_WEBHOOK"]

    def send(self, msg: Message) -> None:
        embed = {
            "title": _clip(msg.title, 250),
            "description": _clip(msg.summary, 1800),
            "url": msg.link,
            "color": 0x5C6BC0,
            "footer": {"text": f"⏰ 截止 {msg.end_date}"},
        }
        if msg.image:
            embed["image"] = {"url": msg.image}
        request_with_retry(
            "POST",
            _env("DISCORD_WEBHOOK"),
            json={"username": "Epic 喜加一", "embeds": [embed]},
        )


# ─────────────────────────────────────────────
# 11. Slack
# ─────────────────────────────────────────────
@register
class SlackChannel(BaseChannel):
    name = "slack"
    label = "Slack Webhook"
    doc = "SLACK_WEBHOOK"
    required = ["SLACK_WEBHOOK"]

    def send(self, msg: Message) -> None:
        blocks = [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": _clip(msg.markdown, 2800)},
            }
        ]
        if msg.image:
            blocks.append(
                {"type": "image", "image_url": msg.image, "alt_text": msg.game}
            )
        blocks.append(
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "点击领取"},
                        "url": msg.link,
                        "style": "primary",
                    }
                ],
            }
        )
        request_with_retry(
            "POST",
            _env("SLACK_WEBHOOK"),
            json={"text": f"{msg.title} ｜ {msg.link}", "blocks": blocks},
        )


# ─────────────────────────────────────────────
# 12. PushDeer
# ─────────────────────────────────────────────
@register
class PushDeerChannel(BaseChannel):
    name = "pushdeer"
    label = "PushDeer"
    doc = "PUSHDEER_KEY, PUSHDEER_URL（可选，自建用）"
    required = ["PUSHDEER_KEY"]

    def send(self, msg: Message) -> None:
        base = (_env("PUSHDEER_URL") or "https://api2.pushdeer.com").rstrip("/")
        _post_json(
            f"{base}/message/push",
            {
                "pushkey": _env("PUSHDEER_KEY"),
                "text": msg.title,
                "desp": msg.markdown,
                "type": "markdown",
            },
            "PushDeer",
        )


# ─────────────────────────────────────────────
# 13. WxPusher
# ─────────────────────────────────────────────
@register
class WxPusherChannel(BaseChannel):
    name = "wxpusher"
    label = "WxPusher（微信）"
    doc = "WXPUSHER_APP_TOKEN, WXPUSHER_UIDS（逗号分隔）"
    required = ["WXPUSHER_APP_TOKEN", "WXPUSHER_UIDS"]

    def send(self, msg: Message) -> None:
        uids = [u.strip() for u in _env("WXPUSHER_UIDS").split(",") if u.strip()]
        resp = request_with_retry(
            "POST",
            "https://wxpusher.zjiecode.com/api/send/message",
            json={
                "appToken": _env("WXPUSHER_APP_TOKEN"),
                "content": msg.markdown,
                "summary": _clip(msg.title, 99),
                "contentType": 3,  # 3 = Markdown
                "uids": uids,
            },
        )
        # WxPusher 的成功码是 1000，不能套用通用的 0/200 判断
        data = resp.json()
        if data.get("code") != 1000:
            raise RuntimeError(f"WxPusher 返回错误: {data}")


# ─────────────────────────────────────────────
# 14. 邮件（SMTP）
# ─────────────────────────────────────────────
@register
class EmailChannel(BaseChannel):
    name = "email"
    label = "邮件（SMTP）"
    doc = "SMTP_HOST, SMTP_USER, SMTP_PASS, MAIL_TO；SMTP_PORT 默认 465"
    required = ["SMTP_HOST", "SMTP_USER", "SMTP_PASS", "MAIL_TO"]

    def send(self, msg: Message) -> None:
        host = _env("SMTP_HOST")
        port = int(_env("SMTP_PORT") or "465")
        user = _env("SMTP_USER")
        password = _env("SMTP_PASS")
        sender = _env("MAIL_FROM") or user
        receivers = [r.strip() for r in _env("MAIL_TO").split(",") if r.strip()]

        body = (
            f"{msg.html}"
            + (f"<br><img src='{msg.image}' style='max-width:520px'>" if msg.image else "")
        )
        mail = MIMEText(body, "html", "utf-8")
        mail["Subject"] = Header(msg.title, "utf-8")
        mail["From"] = formataddr((str(Header("Epic 喜加一", "utf-8")), sender))
        mail["To"] = ", ".join(receivers)

        if port == 465:
            server = smtplib.SMTP_SSL(host, port, timeout=TIMEOUT)
        else:
            server = smtplib.SMTP(host, port, timeout=TIMEOUT)
            server.starttls()
        try:
            server.login(user, password)
            server.sendmail(sender, receivers, mail.as_string())
        finally:
            server.quit()


# ─────────────────────────────────────────────
# 15. 通用 Webhook
# ─────────────────────────────────────────────
@register
class GenericWebhookChannel(BaseChannel):
    name = "webhook"
    label = "通用 Webhook（自定义）"
    doc = "GENERIC_WEBHOOK；GENERIC_WEBHOOK_METHOD / GENERIC_WEBHOOK_HEADERS 可选"
    required = ["GENERIC_WEBHOOK"]

    def send(self, msg: Message) -> None:
        headers = {"Content-Type": "application/json"}
        raw_headers = _env("GENERIC_WEBHOOK_HEADERS")
        if raw_headers:
            headers.update(json.loads(raw_headers))
        method = (_env("GENERIC_WEBHOOK_METHOD") or "POST").upper()
        request_with_retry(
            method,
            _env("GENERIC_WEBHOOK"),
            json={
                "title": msg.title,
                "summary": msg.summary,
                "content": msg.markdown,
                "plain": msg.plain,
                "url": msg.link,
                "image": msg.image,
                "end_date": msg.end_date,
                "game": msg.game,
            },
            headers=headers,
        )


# ─────────────────────────────────────────────
# 渠道选择
# ─────────────────────────────────────────────
def resolve_channels(env: Dict[str, str] | None = None) -> List[BaseChannel]:
    """
    根据 PUSH_CHANNELS 决定启用哪些渠道。

    - 未设置 / auto：自动启用所有凭证齐全的渠道
    - all：启用全部（缺凭证的会记录警告并跳过）
    - 逗号分隔：只启用列出的渠道
    """
    env = env if env is not None else os.environ
    raw = (env.get("PUSH_CHANNELS") or "auto").strip().lower()

    if raw in ("", "auto"):
        names = [n for n, cls in REGISTRY.items() if cls.is_configured(env)]
        skipped = [n for n, cls in REGISTRY.items() if not cls.is_configured(env)]
        log.info("🔎 自动探测到 %d 个可用渠道: %s", len(names), ", ".join(names) or "无")
        log.debug("未配置的渠道: %s", ", ".join(skipped) or "无")
    elif raw == "all":
        names = list(REGISTRY.keys())
    else:
        names = [n.strip() for n in raw.replace("，", ",").split(",") if n.strip()]

    channels: List[BaseChannel] = []
    for name in names:
        cls = REGISTRY.get(name)
        if cls is None:
            log.warning("⚠️ 未知渠道 %r，已忽略（可用：%s）", name, ", ".join(REGISTRY))
            continue
        if not cls.is_configured(env):
            log.warning(
                "⚠️ 渠道 %s 缺少配置 %s，已跳过", cls.label, ", ".join(cls.missing(env))
            )
            continue
        channels.append(cls())

    return channels


def available_channels() -> Dict[str, str]:
    """返回 {名称: 说明}，供 CLI 打印帮助。"""
    return {name: f"{cls.label} —— 需要 {cls.doc}" for name, cls in REGISTRY.items()}
