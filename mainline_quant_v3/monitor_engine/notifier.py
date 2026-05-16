# -*- coding: utf-8 -*-
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum


class NotifyLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class NotifyHandler:

    def send(self, title: str, content: str, level: str = "INFO"):
        raise NotImplementedError


class ConsoleHandler(NotifyHandler):

    def send(self, title: str, content: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n{'=' * 60}")
        print(f"[{timestamp}] [{level}] {title}")
        print(f"{'-' * 60}")
        print(content)
        print(f"{'=' * 60}\n")


class DingTalkHandler(NotifyHandler):

    def __init__(self, webhook_url: str, secret: Optional[str] = None):
        self.webhook_url = webhook_url
        self.secret = secret

    def send(self, title: str, content: str, level: str = "INFO"):
        try:
            import requests
            import time
            import hmac
            import hashlib
            import base64
            from urllib.parse import quote_plus

            timestamp = str(round(time.time() * 1000))
            sign = ""

            if self.secret:
                secret_enc = self.secret.encode("utf-8")
                string_to_sign = f"{timestamp}\n{self.secret}"
                string_to_sign_enc = string_to_sign.encode("utf-8")
                hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
                sign = quote_plus(base64.b64encode(hmac_code))

            url = self.webhook_url
            if sign:
                url = f"{url}&timestamp={timestamp}&sign={sign}"

            payload = {
                "msgtype": "markdown",
                "markdown": {
                    "title": f"[{level}] {title}",
                    "text": f"## [{level}] {title}\n\n{content}\n\n> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                },
            }

            resp = requests.post(url, json=payload, timeout=10)
            if resp.status_code == 200:
                print(f"DingTalk sent: {title}")
            else:
                print(f"DingTalk failed: {resp.status_code} {resp.text}")

        except ImportError:
            print(f"DingTalk (no requests): [{level}] {title}\n{content}")
        except Exception as e:
            print(f"DingTalk error: {e}")


class FeishuHandler(NotifyHandler):

    def __init__(self, webhook_url: str, secret: Optional[str] = None):
        self.webhook_url = webhook_url
        self.secret = secret

    def send(self, title: str, content: str, level: str = "INFO"):
        try:
            import requests

            color_map = {
                "DEBUG": "grey",
                "INFO": "blue",
                "WARNING": "yellow",
                "ERROR": "red",
            }

            payload = {
                "msg_type": "interactive",
                "card": {
                    "header": {
                        "title": {
                            "tag": "plain_text",
                            "content": f"[{level}] {title}",
                        },
                        "template": color_map.get(level, "blue"),
                    },
                    "elements": [
                        {
                            "tag": "markdown",
                            "content": content,
                        },
                        {
                            "tag": "note",
                            "elements": [
                                {
                                    "tag": "plain_text",
                                    "content": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                }
                            ],
                        },
                    ],
                },
            }

            resp = requests.post(self.webhook_url, json=payload, timeout=10)
            if resp.status_code == 200:
                result = resp.json()
                if result.get("code") == 0:
                    print(f"Feishu sent: {title}")
                else:
                    print(f"Feishu failed: {result}")
            else:
                print(f"Feishu failed: {resp.status_code} {resp.text}")

        except ImportError:
            print(f"Feishu (no requests): [{level}] {title}\n{content}")
        except Exception as e:
            print(f"Feishu error: {e}")


class Notifier:

    def __init__(self):
        self.handlers: List[NotifyHandler] = []
        self.add_console()

    def add_dingtalk(self, webhook_url: str, secret: Optional[str] = None):
        handler = DingTalkHandler(webhook_url, secret)
        self.handlers.append(handler)
        print(f"Notifier add dingtalk: {webhook_url[:50]}...")

    def add_feishu(self, webhook_url: str, secret: Optional[str] = None):
        handler = FeishuHandler(webhook_url, secret)
        self.handlers.append(handler)
        print(f"Notifier add feishu: {webhook_url[:50]}...")

    def add_console(self):
        if not any(isinstance(h, ConsoleHandler) for h in self.handlers):
            self.handlers.append(ConsoleHandler())

    def send(self, title: str, content: str, level: str = "INFO"):
        for handler in self.handlers:
            try:
                handler.send(title, content, level)
            except Exception as e:
                print(f"Notify handler error: {e}")

    def debug(self, title: str, content: str):
        self.send(title, content, "DEBUG")

    def info(self, title: str, content: str):
        self.send(title, content, "INFO")

    def warning(self, title: str, content: str):
        self.send(title, content, "WARNING")

    def error(self, title: str, content: str):
        self.send(title, content, "ERROR")