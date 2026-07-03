#!/usr/bin/env python3
"""微信视频号直播弹幕抓取工具（Python 版）

使用 Playwright 打开微信视频号管理后台，拦截 mmfinderassistant-bin/live/msg 接口，
实时解析并打印弹幕、礼物、点赞等事件。

使用方法：
1. 运行本脚本
2. 弹出的浏览器窗口中扫码登录
3. 进入直播间后，终端会实时显示弹幕和礼物信息
"""
import argparse
import asyncio
import base64
import json
import logging
import os
import sys
import time
from contextlib import suppress
from typing import Any, Dict, List



def _configure_bundled_browser() -> None:
    """让 PyInstaller 版本使用安装目录中自带的 Chromium。"""
    if not getattr(sys, "frozen", False):
        return
    browser_dir = os.path.join(os.path.dirname(sys.executable), "pw-browsers")
    if os.path.isdir(browser_dir):
        os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", browser_dir)


_configure_bundled_browser()

from playwright.async_api import Page, Response, async_playwright

DEFAULT_SPY_URL = "https://channels.weixin.qq.com/platform/live/liveBuild"

logger = logging.getLogger("wx_live_spy")


def _default_user_data_dir() -> str:
    if sys.platform == "win32":
        base_dir = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        return os.path.join(base_dir, "WXLiveSpy", "browser-profile")
    return os.path.join(os.path.expanduser("~"), ".wx_live_spy")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture WeChat live danmaku with Playwright.")
    parser.add_argument("--spy-url", default=DEFAULT_SPY_URL, help="登录后需要进入的直播后台地址")
    parser.add_argument(
        "--user-data-dir",
        default=_default_user_data_dir(),
        help="Chromium 用户目录，复用登录态",
    )
    parser.add_argument("--headless", action="store_true", help="以 headless 模式运行")
    parser.add_argument("--verbose", action="store_true", help="输出调试日志")
    return parser.parse_args()


def configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(message)s")


def _now_ms() -> int:
    return int(time.time() * 1000)


def _decode_payload(payload_base64: str) -> Dict[str, Any]:
    if not payload_base64:
        return {}
    try:
        decoded = base64.b64decode(payload_base64)
        return json.loads(decoded)
    except Exception as exc:  # pylint: disable=broad-except
        logger.debug("payload decode failed: %s", exc)
        return {}


def _msg_from_comment(obj: Dict[str, Any]) -> Dict[str, Any]:
    msg_type = obj.get("type")
    decoded_type = {1: "comment", 10005: "enter"}.get(msg_type, "unknown")
    return {
        "seq": obj.get("seq", 0),
        "type": decoded_type,
        "nickname": obj.get("nickname", ""),
        "content": obj.get("content", ""),
        "openid": obj.get("username", ""),
        "msg_id": obj.get("clientMsgId", ""),
        "time": _now_ms(),
    }


def _msg_from_app(obj: Dict[str, Any]) -> Dict[str, Any]:
    msg_type = obj.get("msgType")
    payload = _decode_payload(obj.get("payload", ""))
    base_msg = {
        "seq": obj.get("seq", 0),
        "nickname": obj.get("fromUserContact", {}).get("contact", {}).get("nickname", ""),
        "openid": obj.get("fromUserContact", {}).get("contact", {}).get("username", ""),
        "msg_id": obj.get("clientMsgId", ""),
        "time": _now_ms(),
        "type": "unknown",
        "content": payload.get("content", ""),
    }

    if msg_type == 20009:
        base_msg.update(
            {
                "type": "gift",
                "gift_id": payload.get("reward_product_id"),
                "gift_num": payload.get("reward_product_count"),
                "gift_value": payload.get("reward_amount_in_wecoin"),
            },
        )
    elif msg_type == 20013:
        base_msg.update(
            {
                "type": "combogift",
                "gift_id": payload.get("reward_product_id"),
                "gift_num": payload.get("combo_product_count"),
            },
        )
    elif msg_type == 20006:
        base_msg["type"] = "like"
    elif msg_type == 20031:
        base_msg.update(
            {
                "type": "levelup",
                "from_level": payload.get("from_level"),
                "to_level": payload.get("to_level"),
            },
        )
    return base_msg


def _extract_events(response_json: Dict[str, Any]) -> List[Dict[str, Any]]:
    data = response_json.get("data") or {}
    events: List[Dict[str, Any]] = []
    for obj in data.get("msgList", []):
        events.append(_msg_from_comment(obj))
    for obj in data.get("appMsgList", []):
        events.append(_msg_from_app(obj))
    return events


class WXLiveSpy:
    def __init__(self, spy_url: str, user_data_dir: str, headless: bool) -> None:
        self.spy_url = spy_url
        self.user_data_dir = user_data_dir
        self.headless = headless

    async def run(self) -> None:
        os.makedirs(self.user_data_dir, exist_ok=True)

        chromium_args = [
            "--disable-setuid-sandbox",
            "--disable-gpu",
            "--hide-crash-restore-bubble",
            "--window-size=1200,900",
        ]

        async with async_playwright() as p:
            context = await p.chromium.launch_persistent_context(
                user_data_dir=self.user_data_dir,
                headless=self.headless,
                args=chromium_args,
            )
            page = context.pages[0] if context.pages else await context.new_page()
            page.on("response", lambda resp: asyncio.create_task(self._handle_response(resp)))

            logger.info("打开微信视频号后台: %s", self.spy_url)
            await page.goto(self.spy_url, wait_until="networkidle")
            logger.info("请扫码登录并进入直播间，终端会实时显示弹幕。")

            ensure_task = asyncio.create_task(self._ensure_live_page(page))
            try:
                while True:
                    await asyncio.sleep(3600)
            except asyncio.CancelledError:
                raise
            except KeyboardInterrupt:
                logger.info("Stopping...")
            finally:
                ensure_task.cancel()
                with suppress(asyncio.CancelledError):
                    await ensure_task
                await context.close()

    async def _handle_response(self, response: Response) -> None:
        if not self._should_inspect(response):
            return

        try:
            response_json = await response.json()
        except Exception as exc:  # pylint: disable=broad-except
            logger.debug("response parse failed: %s", exc)
            return

        events = _extract_events(response_json)
        for event in events:
            self._print_event(event)

    def _print_event(self, event: Dict[str, Any]) -> None:
        event_type = event.get("type")
        nickname = event.get("nickname", "")
        if event_type in {"comment", "enter"}:
            logger.info("[%s] %s: %s", event_type, nickname, event.get("content", ""))
        elif event_type in {"gift", "combogift"}:
            logger.info(
                "[%s] %s -> %s x%s (worth %s)",
                event_type,
                nickname,
                event.get("gift_id"),
                event.get("gift_num"),
                event.get("gift_value"),
            )
        elif event_type == "like":
            logger.info("[like] %s 点赞", nickname)
        elif event_type == "levelup":
            logger.info(
                "[levelup] %s %s -> %s",
                nickname,
                event.get("from_level"),
                event.get("to_level"),
            )
        else:
            logger.debug("[unknown] %s", event)

    async def _ensure_live_page(self, page: Page) -> None:
        try:
            while True:
                url = page.url or ""
                if "channels.weixin.qq.com" in url and "live/liveBuild" not in url:
                    logger.info("重定向回直播后台: %s", self.spy_url)
                    await page.goto(self.spy_url, wait_until="networkidle")
                await asyncio.sleep(5)
        except asyncio.CancelledError:
            raise

    def _should_inspect(self, response: Response) -> bool:
        url = response.url
        if "mmfinderassistant-bin/live/msg" not in url:
            return False
        if response.request.method.upper() != "POST":
            return False
        content_type = (response.headers.get("content-type") or "").split(";")[0].strip()
        return content_type in ("application/json", "application/octet-stream")


async def main_async(args: argparse.Namespace) -> None:
    spy = WXLiveSpy(args.spy_url, args.user_data_dir, args.headless)
    await spy.run()


def main() -> None:
    args = parse_args()
    configure_logging(args.verbose)
    try:
        asyncio.run(main_async(args))
    except KeyboardInterrupt:
        logger.info("Exited by user")
        sys.exit(0)


if __name__ == "__main__":
    main()
