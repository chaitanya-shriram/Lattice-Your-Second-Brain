"""
Telegram bot: text-in from your phone without exposing a port.
Long-polls Telegram's servers (outbound-only connection), so it works from
behind any NAT/firewall and the message just waits on Telegram's side until
this process is back online. Each message is run through the same brain-dump
pipeline as the desktop "Brain Dump" page — same task/reminder extraction.
"""
import asyncio
import httpx

from config.settings import get_settings
from utils.logger import get_logger

log = get_logger("engines.telegram_bot")

POLL_TIMEOUT = 30  # seconds; Telegram long-poll
TELEGRAM_MSG_LIMIT = 3500  # stay under Telegram's 4096-char cap with headroom


def _api_url(token: str, method: str) -> str:
    return f"https://api.telegram.org/bot{token}/{method}"


async def send_telegram(text: str):
    """Fire-and-forget push to the configured chat. No-op if not configured."""
    settings = get_settings()
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        return
    text = text[:TELEGRAM_MSG_LIMIT]
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                _api_url(settings.telegram_bot_token, "sendMessage"),
                json={"chat_id": settings.telegram_chat_id, "text": text},
            )
    except Exception as e:
        log.warning(f"Telegram send failed: {e}")


async def _handle_message(chat_id: str, text: str):
    from engines.brain_dump import get_brain_dump_engine

    result = await get_brain_dump_engine().process(text, source="telegram")
    if "error" in result:
        reply = f"Couldn't process that: {result['error']}"
    elif result["total_items"] == 0:
        reply = "Got it — nothing extractable in there (no tasks/ideas/questions detected)."
    else:
        lines = [f"Filed {result['total_items']} item(s):"]
        lines += [f"- task: {t['title']} [{t['priority']}]" for t in result["tasks"]]
        lines += [f"- intent: {i['title']}" for i in result["intents"]]
        lines += [f"- idea: {i['text'][:60]}" for i in result["ideas"]]
        lines += [f"- question: {q['text'][:60]}" for q in result["questions"]]
        reply = "\n".join(lines)

    settings = get_settings()
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(
            _api_url(settings.telegram_bot_token, "sendMessage"),
            json={"chat_id": chat_id, "text": reply[:TELEGRAM_MSG_LIMIT]},
        )


async def poll_forever():
    """Background loop: long-poll getUpdates, dispatch text messages. Runs until process exit."""
    settings = get_settings()
    token = settings.telegram_bot_token
    if not token:
        return

    offset = 0
    log.info("Telegram bot polling started")
    async with httpx.AsyncClient(timeout=POLL_TIMEOUT + 10) as client:
        while True:
            try:
                resp = await client.get(
                    _api_url(token, "getUpdates"),
                    params={"offset": offset, "timeout": POLL_TIMEOUT},
                )
                resp.raise_for_status()
                updates = resp.json().get("result", [])
            except Exception as e:
                log.warning(f"Telegram poll failed, retrying in 5s: {e}")
                await asyncio.sleep(5)
                continue

            for update in updates:
                offset = update["update_id"] + 1
                msg = update.get("message") or {}
                text = msg.get("text")
                chat_id = str(msg.get("chat", {}).get("id", ""))
                if not text or not chat_id:
                    continue

                # First-run: no chat id configured yet — log it so the user can set
                # TELEGRAM_CHAT_ID, and don't process messages from an unverified sender.
                allowed = settings.telegram_chat_id
                if not allowed:
                    log.warning(f"Telegram message from unconfigured chat_id={chat_id} — "
                                f"set TELEGRAM_CHAT_ID={chat_id} in .env to enable it")
                    continue
                if chat_id != allowed:
                    log.warning(f"Ignoring Telegram message from unauthorized chat_id={chat_id}")
                    continue

                try:
                    await _handle_message(chat_id, text)
                except Exception as e:
                    log.error(f"Telegram message handling failed: {e}", exc_info=True)
