#!/usr/bin/env python3
"""
Epic Games Free Notifier — Epic 喜加一通知机器人
基于 GitHub Actions 全自动运行，通过 Telegram Bot 推送 Epic 免费游戏信息。

改进点：
  - 网络请求自动重试（3次，指数退避）
  - 使用现代时区 API（timezone-aware datetime）
  - 可配置的通知时间窗口（环境变量 NOTIFY_HOURS）
  - 更健壮的容错和日志输出
  - 消息模板与逻辑解耦，便于自定义

原项目：https://github.com/wwxseo/epic-
"""

import os
import time
import html
import logging
from datetime import datetime, timezone, timedelta

import requests

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
BOT_TOKEN  = os.environ.get("TG_BOT_TOKEN", "")
CHAT_ID    = os.environ.get("TG_CHAT_ID", "")
# 通知时间窗口：上架多久以内的游戏才推送（小时），默认 28
NOTIFY_HOURS = int(os.environ.get("NOTIFY_HOURS", "28"))
# Epic API 端点
EPIC_API_URL = (
    "https://store-site-backend-static.ak.epicgames.com"
    "/freeGamesPromotions?locale=en-US"
)
# Telegram API 端点
TG_API_BASE = "https://api.telegram.org/bot{token}"
# 请求重试参数
MAX_RETRIES = 3
RETRY_BACKOFF = 2  # 秒，指数退避基数

# ─────────────────────────────────────────────
# 工具函数
# ─────────────────────────────────────────────

def _request_with_retry(method: str, url: str, **kwargs):
    """带自动重试的 HTTP 请求（指数退避）。"""
    last_exc = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            if method == "GET":
                resp = requests.get(url, timeout=30, **kwargs)
            else:
                resp = requests.post(url, timeout=30, **kwargs)
            resp.raise_for_status()
            return resp
        except Exception as exc:
            last_exc = exc
            wait = RETRY_BACKOFF ** attempt
            log.warning(
                "请求失败 (%d/%d): %s ｜ %ds 后重试…",
                attempt, MAX_RETRIES, exc, wait,
            )
            time.sleep(wait)
    raise last_exc  # type: ignore[misc]


def _parse_date(raw: str | None) -> datetime | None:
    """安全解析 Epic 返回的 ISO 日期字符串，返回 timezone-aware datetime。"""
    if not raw:
        return None
    try:
        # Epic 格式形如 "2025-12-18T17:00:00.000Z"
        # datetime.fromisoformat 在 3.11+ 支持 'Z'，兼容处理
        clean = raw.split(".")[0] + "Z" if "." in raw else raw
        dt = datetime.fromisoformat(clean.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception as exc:
        log.debug("日期解析失败: %s → %s", raw, exc)
        return None


# ─────────────────────────────────────────────
# 核心逻辑
# ─────────────────────────────────────────────

def get_epic_free_games() -> list[dict]:
    """
    从 Epic Games Store 获取当前免费游戏列表。

    返回格式：
        [{"title", "description", "link", "image", "end_date"}, ...]
    """
    try:
        resp = _request_with_retry("GET", EPIC_API_URL)
        data = resp.json()
        games = data["data"]["Catalog"]["searchStore"]["elements"]
    except Exception as exc:
        log.error("❌ 获取 Epic 免费游戏列表失败: %s", exc)
        return []

    now = datetime.now(timezone.utc)
    threshold = timedelta(hours=NOTIFY_HOURS)
    free_games: list[dict] = []

    for game in games:
        # ── 1. 促销筛选
        promotions = game.get("promotions")
        if not promotions or not promotions.get("promotionalOffers"):
            continue

        offers = promotions["promotionalOffers"]
        is_free = False
        end_date_str = "未知"
        is_new_game = False   # 上架时间在窗口内 → 新游戏 → 推送；否则跳过

        for offer_group in offers:
            for offer in offer_group.get("promotionalOffers", []):
                if offer["discountSetting"]["discountPercentage"] == 0:
                    is_free = True

                    # ── 截止时间
                    raw_end = offer.get("endDate")
                    dt_end = _parse_date(raw_end)
                    if dt_end:
                        end_date_str = dt_end.strftime("%Y-%m-%d %H:%M UTC")

                    # ── 上架时间 → 去重判断
                    raw_start = offer.get("startDate")
                    dt_start = _parse_date(raw_start)

                    if dt_start:
                        time_diff = now - dt_start
                        if time_diff < threshold:
                            is_new_game = True
                        else:
                            log.info(
                                "⏭️  跳过旧游戏: %s (已上架 %s)",
                                game.get("title"),
                                _humanize_timedelta(time_diff),
                            )
                    else:
                        # 无法确定上架时间 → 保守推送（宁可多发不漏发）
                        log.warning("⚠️ 无法解析上架时间，默认推送: %s", game.get("title"))
                        is_new_game = True
                    break  # 找到第一个免费 offer 即可
            if is_free:
                break

                # ── 2. 只收集「免费 + 新上架」的游戏
        if is_free and is_new_game:
            title       = game.get("title", "未知游戏")
            description = game.get("description", "暂无简介")
            slug        = game.get("productSlug") or game.get("urlSlug") or ""
            if slug:
                product_id = game.get("id", "")
                id_suffix = f"-{product_id[:6]}" if product_id else ""
                link = f"https://store.epicgames.com/p/{slug}{id_suffix}"
            else:
                link = "https://store.epicgames.com/free-games"
          
          # ── 封面图：优先 Thumbnail，其次 OfferImageWide
            image_url = ""
            for img in game.get("keyImages", []):
                if img.get("type") == "Thumbnail":
                    image_url = img.get("url", "")
                    break
                if img.get("type") == "OfferImageWide":
                    image_url = img.get("url", "")

            free_games.append({
                "title":       title,
                "description": description,
                "link":        link,
                "image":       image_url,
                "end_date":    end_date_str,
            })

    return free_games


def _humanize_timedelta(td: timedelta) -> str:
    """将 timedelta 转为人类可读字符串。"""
    total_seconds = int(td.total_seconds())
    if total_seconds < 3600:
        return f"{total_seconds // 60}分钟"
    if total_seconds < 86400:
        return f"{total_seconds // 3600}小时"
    return f"{total_seconds // 86400}天"


def build_message(game: dict) -> str:
    """构建 Telegram HTML 消息。"""
    safe_title = html.escape(game["title"])
    safe_desc = html.escape(game["description"])

    # 利用 Telegram 预览功能显示封面图
    image_tag = (
        f"<a href='{game['image']}'>&#8205;</a>\n"
        if game["image"]
        else ""
    )

    msg = (
        f"{image_tag}"
        f"🆓 <b>Epic Games 限时免费</b> 🆓\n\n"
        f"🎮 <b>{safe_title}</b>\n"
        f"⏰ 截止：{game['end_date']}\n\n"
        f"📋 {safe_desc}\n\n"
        f"👉 <a href='{game['link']}'>点击此处领取</a>"
    )
    return msg


def send_telegram_message(text: str):
    """通过 Telegram Bot API 发送消息。"""
    if not BOT_TOKEN or not CHAT_ID:
        log.error("❌ 缺少配置：请设置 TG_BOT_TOKEN 和 TG_CHAT_ID")
        return

    url = f"{TG_API_BASE.format(token=BOT_TOKEN)}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,  # 开启预览以显示封面图
    }
    try:
        _request_with_retry("POST", url, json=payload)
        log.info("✅ Telegram 消息发送成功")
    except Exception as exc:
        log.error("❌ Telegram 消息发送失败: %s", exc)


# ─────────────────────────────────────────────
# 入口
# ─────────────────────────────────────────────

def main():
    log.info("🚀 开始检测 Epic Games 免费游戏 (通知窗口: %d小时)…", NOTIFY_HOURS)
    games = get_epic_free_games()

    if not games:
        log.info("😴 当前没有需要推送的免费游戏 (可能是旧游戏被去重跳过)")
        return

    log.info("🔍 发现 %d 款免费游戏，开始推送通知…", len(games))
    for game in games:
        log.info("📨 推送: %s (截止: %s)", game["title"], game["end_date"])
        msg = build_message(game)
        send_telegram_message(msg)

    log.info("✨ 全部完成！")


if __name__ == "__main__":
    main()
