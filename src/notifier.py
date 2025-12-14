"""Slack 알림 전송"""

import os
import requests
from typing import Optional


class SlackNotifier:
    """Slack Incoming Webhook으로 메시지 전송"""

    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or os.getenv("SLACK_WEBHOOK_URL")

    def send(self, title: str, content: str) -> bool:
        """Slack으로 메시지 전송"""
        if not self.webhook_url:
            print("[Slack] Webhook URL이 설정되지 않았습니다.")
            return False

        # Slack 메시지 길이 제한 (약 40,000자)
        # 안전하게 35,000자로 제한
        if len(content) > 35000:
            content = content[:35000] + "\n\n... (내용이 잘렸습니다)"

        # Block Kit 형식으로 보기 좋게 전송
        payload = {
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": title,
                        "emoji": True
                    }
                },
                {
                    "type": "divider"
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": self._format_for_slack(content)
                    }
                }
            ]
        }

        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            print("[Slack] 메시지 전송 성공")
            return True
        except Exception as e:
            print(f"[Slack] 메시지 전송 실패: {e}")
            return False

    def _format_for_slack(self, text: str) -> str:
        """Slack mrkdwn 형식으로 변환"""
        # Markdown 헤더를 볼드로 변환
        lines = text.split('\n')
        formatted = []

        for line in lines:
            if line.startswith('### '):
                formatted.append(f"*{line[4:]}*")
            elif line.startswith('## '):
                formatted.append(f"*{line[3:]}*")
            elif line.startswith('# '):
                formatted.append(f"*{line[2:]}*")
            else:
                formatted.append(line)

        return '\n'.join(formatted)

    def send_simple(self, message: str) -> bool:
        """간단한 텍스트 메시지 전송"""
        if not self.webhook_url:
            print("[Slack] Webhook URL이 설정되지 않았습니다.")
            return False

        payload = {"text": message}

        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"[Slack] 메시지 전송 실패: {e}")
            return False
