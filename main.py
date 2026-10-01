#!/usr/bin/env python3
"""
Epic Games Free Notifier — Epic 喜加一通知机器人
基于 GitHub Actions 全自动运行，把 Epic 免费游戏推送到你喜欢的任意渠道。

相比初版的变化：
  - 🧩 多推送渠道：Telegram / 企业微信 / 钉钉 / 飞书 / Server酱 / PushPlus / Bark /
    ntfy / Gotify / Discord / Slack / PushDeer / WxPusher / 邮件 / 通用 Webhook
  - 💾 状态持久化（state.json）：推送记录跨运行保留，去重更准，不再重复骚扰
  - ❤️ 内建心跳提交：让仓库持续产生 commit，从根上避免 GitHub 60 天禁用定时任务

原项目：https://github.com/wwxseo/epic-
"""

from __future__ import annotations

import argparse
import html
import json
import logging
import os
import re
import sys
from datetime import datetime, timedelta, timezone

import channels as ch
from channels import Message, available_channels, resolve_channels

# ─────────────────────────────────────────────
# 日志配置
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-7s │ %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("epic-notifier")

# ─────────────────────────────────────────────
# 配置（从 GitHub Secrets / 环境变量读取）
# ─────────────────────────────────────────────
NOTIFY_HOURS = int(os.environ.get("NOTIFY_HOURS", "28"))
HEARTBEAT_DAYS = int(os.environ.get("HEARTBEAT_DAYS", "15"))
ENABLE_STATE = os.environ.get("ENABLE_STATE", "true").strip().lower() not in (
    "0",
    "false",
    "no",
)
DRY_RUN = os.environ.get("DRY_RUN", "").strip().lower() in ("1", "true", "yes")

EPIC_API_URL = (
    "https://store-site-backend-static.ak.epicgames.com"
    "/freeGamesPromotions?locale=en-US"
)
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.environ.get("STATE_FILE") or os.path.join(REPO_ROOT, "state.json")

# 状态文件保留时长（超过则清理，避免无限膨胀）
STATE_RETENTION_DAYS = int(os.environ.get("STATE_RETENTION_DAYS", "365"))


# ─────────────────────────────────────────────
# 工具函数
# ─────────────────────────────────────────────
def _parse_date(raw: str | None) -> datetime | None:
    """安全解析 Epic 返回的 ISO 日期字符串，返回 timezone-aware datetime。"""
    if not raw:
        return None
    try:
        clean = raw.split(".")[0] + "Z" if "." in raw else raw
        dt = datetime.fromisoformat(clean.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception as exc:
        log.debug("日期解析失败: %s → %s", raw, exc)
        return None


def _humanize_timedelta(td: timedelta) -> str:
    total = int(td.total_seconds())
    if total < 3600:
        return f"{total // 60}分钟"
    if total < 86400:
        return f"{total // 3600}小时"
    return f"{total // 86400}天"


_TAG_RE = re.compile(r"<[^>]+>")


def _clean_text(raw: str) -> str:
    """把 Epic 返回的简介洗干净：去 HTML 标签 + 反转义实体。"""
    if not raw:
        return "暂无简介"
    text = _TAG_RE.sub(" ", raw)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or "暂无简介"


# ─────────────────────────────────────────────
# 状态持久化（去重 + 心跳）
# ─────────────────────────────────────────────
def load_state() -> dict:
    if not ENABLE_STATE or not os.path.exists(STATE_FILE):
        return {"version": 1, "last_heartbeat": None, "pushed": {}}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as fh:
            state = json.load(fh)
    except Exception as exc:
        log.warning("⚠️ 状态文件读取失败（将重建）: %s", exc)
        return {"version": 1, "last_heartbeat": None, "pushed": {}}

    state.setdefault("version", 1)
    state.setdefault("last_heartbeat", None)
    state.setdefault("pushed", {})
    if not isinstance(state["pushed"], dict):
        state["pushed"] = {}
    return state


def save_state(state: dict) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as fh:
        json.dump(state, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")


def prune_state(state: dict, now: datetime) -> None:
    """清理过期记录，防止状态文件无限增长。"""
    cutoff = now - timedelta(days=STATE_RETENTION_DAYS)
    pushed = state.get("pushed", {})
    fresh = {}
    for key, ts in pushed.items():
        dt = _parse_date(ts)
        if dt is None or dt >= cutoff:
            fresh[key] = ts
    if len(fresh) != len(pushed):
        log.info("🧹 清理 %d 条过期推送记录", len(pushed) - len(fresh))
        state["pushed"] = fresh


def _read_guard_days(path: str) -> int | None:
    """（供 keepalive 脚本复用）返回距状态文件最近一次刷新的天数。"""
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            hb = (json.load(fh) or {}).get("last_heartbeat")
        dt = _parse_date(hb)
        return None if dt is None else (datetime.now(timezone.utc) - dt).days
    except Exception:
        return None


# ─────────────────────────────────────────────
# 核心逻辑
# ─────────────────────────────────────────────
def fetch_free_games() -> list[dict]:
    """
    从 Epic Games Store 获取「免费 + 刚上架」的游戏列表。

    返回：[{"key", "title", "description", "link", "image", "end_date"}, ...]
    """
    try:
        resp = ch.request_with_retry("GET", EPIC_API_URL, timeout=30)
        elements = resp.json()["data"]["Catalog"]["searchStore"]["elements"]
    except Exception as exc:
        log.error("❌ 获取 Epic 免费游戏列表失败: %s", exc)
        raise

    now = datetime.now(timezone.utc)
    threshold = timedelta(hours=NOTIFY_HOURS)
    result: list[dict] = []

    for game in elements:
        promotions = game.get("promotions") or {}
        if not promotions.get("promotionalOffers"):
            continue

        is_free = False
        end_date_str = "未知"
        is_new = False

        for group in promotions["promotionalOffers"]:
            for offer in group.get("promotionalOffers", []):
                if offer.get("discountSetting", {}).get("discountPercentage") != 0:
                    continue
                is_free = True

                dt_end = _parse_date(offer.get("endDate"))
                if dt_end:
                    end_date_str = dt_end.strftime("%Y-%m-%d %H:%M UTC")

                dt_start = _parse_date(offer.get("startDate"))
                if dt_start:
                    elapsed = now - dt_start
                    if elapsed < threshold:
                        is_new = True
                    else:
                        log.info(
                            "⏭️  跳过旧游戏: %s (已上架 %s)",
                            game.get("title"),
                            _humanize_timedelta(elapsed),
                        )
                else:
                    # 拿不到上架时间 → 宁可多发不漏发
                    log.warning("⚠️ 无法解析上架时间，默认推送: %s", game.get("title"))
                    is_new = True
                break  # 拿到第一个免费 offer 就够了
            if is_free:
                break

        if not (is_free and is_new):
            continue

        title = game.get("title", "未知游戏")

        # —— 详情页 slug
        slug = ""
        for mapping in (game.get("offerMappings") or []):
            slug = mapping.get("pageSlug") or ""
            if slug:
                break
        if not slug:
            for mapping in ((game.get("catalogNs") or {}).get("mappings") or []):
                slug = mapping.get("pageSlug") or ""
                if slug:
                    break

        link = (
            f"https://store.epicgames.com/p/{slug}"
            if slug
            else "https://store.epicgames.com/free-games"
        )

        # —— 封面图：Thumbnail 优先，其次 OfferImageWide
        image = ""
        for img in game.get("keyImages", []):
            itype = img.get("type")
            if itype == "Thumbnail":
                image = img.get("url", "")
                break
            if itype == "OfferImageWide" and not image:
                image = img.get("url", "")

        result.append(
            {
                "key": slug or title,
                "title": title,
                "description": _clean_text(game.get("description", "")),
                "link": link,
                "image": image,
                "end_date": end_date_str,
            }
        )

    return result


def build_message(game: dict) -> Message:
    """把游戏信息渲染成各渠道共用的通知载体。"""
    title = game["title"]
    desc = game["description"]
    link = game["link"]
    end = game["end_date"]
    image = game["image"]

    safe_title = html.escape(title)
    safe_desc = html.escape(desc)

    head = f"🆓 Epic Games 限时免费 ｜ 截止 {end}"

    markdown = (
        f"🆓 **Epic Games 限时免费**\n\n"
        f"🎮 **{title}**\n"
        f"⏰ 截止：{end}\n\n"
        f"📋 {desc}\n\n"
        f"👉 [点击此处领取]({link})"
    )
    html_body = (
        f"🆓 <b>Epic Games 限时免费</b>\n\n"
        f"🎮 <b>{safe_title}</b>\n"
        f"⏰ 截止：{end}\n\n"
        f"📋 {safe_desc}\n\n"
        f"👉 <a href='{link}'>点击此处领取</a>"
    )
    plain = (
        f"Epic Games 限时免费：{title}\n"
        f"截止：{end}\n\n"
        f"{desc}\n\n"
        f"领取链接：{link}"
    )

    return Message(
        title=head,
        game=title,
        summary=desc,
        markdown=markdown,
        html=html_body,
        plain=plain,
        link=link,
        image=image,
        end_date=end,
    )


def dispatch(message: Message, channels: list) -> tuple[int, int]:
    """把一条消息发给所有已启用渠道，返回 (成功数, 失败数)。"""
    ok_count = fail_count = 0
    for channel in channels:
        try:
            channel.send(message)
            log.info("   ✅ %s 推送成功", channel.label)
            ok_count += 1
        except Exception as exc:
            log.error("   ❌ %s 推送失败: %s", channel.label, exc)
            fail_count += 1
    return ok_count, fail_count


# ─────────────────────────────────────────────
# 入口
# ─────────────────────────────────────────────
def main() -> int:
    parser = argparse.ArgumentParser(description="Epic 免费游戏多渠道路由推送")
    parser.add_argument(
        "--list-channels", action="store_true", help="列出所有支持的渠道后退出"
    )
    args = parser.parse_args()

    if args.list_channels:
        for name, desc in available_channels().items():
            print(f"  {name:<12} {desc}")
        return 0

    log.info("🚀 开始检测 Epic Games 免费游戏 (通知窗口: %dh)…", NOTIFY_HOURS)

    active = resolve_channels()
    if not active:
        log.error("❌ 没有任何可用渠道，请检查 Secrets / 环境变量配置")
        return 1
    log.info("📡 启用渠道: %s", "、".join(c.label for c in active))

    state = load_state()
    now = datetime.now(timezone.utc)
    state_changed = False

    try:
        games = fetch_free_games()
    except Exception:
        # 拉取失败也要更新心跳，避免整条链路静默
        games = []

    if games:
        log.info("🔍 发现 %d 款符合窗口的免费游戏", len(games))

    pushed: dict = state.setdefault("pushed", {})
    sent_any = False

    for game in games:
        if ENABLE_STATE and game["key"] in pushed:
            log.info("⏭️  已在 %s 推送过，跳过: %s", pushed[game["key"]], game["title"])
            continue

        log.info("📨 推送: %s (截止: %s)", game["title"], game["end_date"])
        message = build_message(game)

        if DRY_RUN:
            log.info("🧪 DRY_RUN 模式，仅打印不发送：\n%s", message.plain)
            continue

        ok_count, fail_count = dispatch(message, active)
        if ok_count and ENABLE_STATE:
            pushed[game["key"]] = now.isoformat(timespec="seconds")
            state_changed = True
            sent_any = True
        if fail_count and not ok_count:
            log.error("   ⚠️ 该游戏所有渠道均失败，本次不记入去重状态")

    if not games and not sent_any:
        log.info("😴 当前没有需要推送的新游戏")

    # ── 心跳：保证仓库始终有 commit，绕过 GitHub 60 天禁用定时任务的规则
    last_hb = _parse_date(state.get("last_heartbeat"))
    hb_due = last_hb is None or (now - last_hb).days >= HEARTBEAT_DAYS
    if hb_due:
        state["last_heartbeat"] = now.isoformat(timespec="seconds")
        state_changed = True
        log.info("❤️  刷新心跳时间戳（上次：%s）", last_hb or "无")

    prune_state(state, now)

    if ENABLE_STATE and state_changed:
        save_state(state)
        log.info("💾 状态已更新: %s", STATE_FILE)
    else:
        log.info("💤 状态无变化，本次无需提交")

    log.info("✨ 全部完成！")
    return 0


if __name__ == "__main__":
    sys.exit(main())
