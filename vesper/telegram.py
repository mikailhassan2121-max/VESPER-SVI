"""Optional phone alerts. Delivery uncertainty is surfaced, never blindly retried."""
import asyncio
import json
from datetime import timedelta

import httpx

from vesper.calendar import utcnow


def signal_text(payload):
    lines = [f"VESPER · {payload['session']}", payload["decision"]]
    if payload["decision"] == "BUY":
        lines += [f"Stock: {payload['winner']}", f"Entry estimate: ${payload['entry']:.2f}",
                  f"Max entry: ${payload['max_entry']:.2f}", f"Expected return: {payload['expected_return']:.2%}",
                  "Manual execution only. Do not chase above max entry.",
                  f"Exit window: {payload.get('exit_start', 'unavailable')} to {payload.get('exit_end', 'unavailable')}"]
    else:
        lines += payload.get("reasons", [])[:8]
    return "\n".join(lines)


class Telegram:
    def __init__(self, settings, store, status):
        self.token = settings.telegram_bot_token.get_secret_value()
        self.chat = settings.telegram_chat_id
        self.store, self.status = store, status
        self.http = httpx.AsyncClient(timeout=35)
        self.health = "NOT_CONFIGURED" if not self.token or not self.chat else "READY"

    async def close(self):
        await self.http.aclose()

    async def delivery(self):
        if not self.token or not self.chat:
            return
        self.store.recover_alerts()
        while True:
            row = self.store.pending_alert(utcnow().isoformat())
            if not row:
                await asyncio.sleep(1)
                continue
            key, text = row
            if self.store.get_state("telegram_muted", False) and key.startswith("signal:"):
                self.store.alert_state(key, "MUTED")
                continue
            self.store.alert_state(key, "SENDING")
            try:
                response = await self.http.post(f"https://api.telegram.org/bot{self.token}/sendMessage",
                                                json={"chat_id": self.chat, "text": text[:4000]})
                body = response.json()
                if response.status_code == 429:
                    delay = max(1, min(3600, int(body.get("parameters", {}).get("retry_after", 30))))
                    self.store.alert_state(key, "PENDING", "Rate limited",
                                           (utcnow()+timedelta(seconds=delay)).isoformat())
                elif response.status_code == 200 and body.get("ok"):
                    self.store.alert_state(key, "SENT", str(body["result"]["message_id"]))
                    self.health = "HEALTHY"
                else:
                    self.store.alert_state(key, "FAILED", f"HTTP {response.status_code}")
                    self.health = "DEGRADED"
            except asyncio.CancelledError:
                raise
            except (httpx.HTTPError, ValueError, KeyError):
                self.store.alert_state(key, "UNKNOWN", "Delivery acknowledgement unavailable; not retried")
                self.health = "DEGRADED"

    def command(self, text):
        command = text.split()[0].split("@")[0].lower() if text.strip() else ""
        if command in {"/start", "/help"}:
            return "VESPER manual signals. Commands: /status /health /top /signal /performance /why /mute /unmute"
        if command in {"/mute", "/unmute"}:
            muted = command == "/mute"
            self.store.set_state("telegram_muted", muted)
            return "Signal alerts muted." if muted else "Signal alerts enabled."
        if command == "/status":
            return str(self.status.get("decision", "Unavailable"))
        if command == "/health":
            return json.dumps({"provider": self.status.get("provider"), "failures": self.status.get("failures", [])})
        if command == "/why":
            return "\n".join(self.status.get("decision_reasons", [])) or "No explanation available yet."
        if command == "/top":
            rows = self.status.get("leaderboard", [])[:5]
            return self.status.get("leaderboard_label", "Unavailable") + "\n" + "\n".join(f"{i+1}. {r['ticker']}" for i, r in enumerate(rows))
        if command == "/signal":
            recent = self.store.recent(1)
            return signal_text(recent[0]) if recent else "No recorded signal."
        if command == "/performance":
            completed = self.store.shadow_positions(completed=True)
            if not completed:
                return "No completed shadow positions."
            values = [r["outcome"]["return"] for r in completed]
            return f"{len(values)} paper estimates; average return {sum(values)/len(values):.2%}. Not actual fills."
        return "Unknown command. Use /help."

    async def commands(self):
        if not self.token or not self.chat:
            return
        while True:
            try:
                offset = self.store.get_state("telegram_offset", 0)
                response = await self.http.post(f"https://api.telegram.org/bot{self.token}/getUpdates",
                    json={"offset": offset, "timeout": 20, "allowed_updates": ["message"]})
                body = response.json()
                if response.status_code != 200 or not body.get("ok"):
                    self.health = "DEGRADED"
                    await asyncio.sleep(10)
                    continue
                for update in body["result"]:
                    identity = int(update["update_id"])
                    message = update.get("message", {})
                    if str(message.get("chat", {}).get("id")) == self.chat:
                        reply = self.command(message.get("text", ""))
                        self.store.queue_alert(f"reply:{identity}", reply, (utcnow()+timedelta(minutes=5)).isoformat())
                    self.store.set_state("telegram_offset", identity+1)
            except asyncio.CancelledError:
                raise
            except (httpx.HTTPError, ValueError, KeyError):
                self.health = "DEGRADED"
                await asyncio.sleep(10)
