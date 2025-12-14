"""Discord 알림 전송"""

import os
import requests
from typing import Optional


class DiscordNotifier:
    """Discord Webhook으로 메시지 전송"""

    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or os.getenv("DISCORD_WEBHOOK_URL")

    def send(self, title: str, content: str) -> bool:
        """Discord로 메시지 전송"""
        if not self.webhook_url:
            print("[Discord] Webhook URL이 설정되지 않았습니다.")
            return False

        # Discord 메시지 길이 제한 (2000자)
        # 긴 메시지는 여러 개로 분할
        messages = self._split_message(content, 1900)

        try:
            # 첫 번째 메시지는 제목과 함께
            first_payload = {
                "embeds": [{
                    "title": title,
                    "description": messages[0] if messages else "내용 없음",
                    "color": 5814783  # 파란색
                }]
            }

            response = requests.post(
                self.webhook_url,
                json=first_payload,
                timeout=30
            )
            response.raise_for_status()

            # 나머지 메시지들 전송
            for msg in messages[1:]:
                payload = {
                    "embeds": [{
                        "description": msg,
                        "color": 5814783
                    }]
                }
                response = requests.post(
                    self.webhook_url,
                    json=payload,
                    timeout=30
                )
                response.raise_for_status()

            print("[Discord] 메시지 전송 성공")
            return True

        except Exception as e:
            print(f"[Discord] 메시지 전송 실패: {e}")
            return False

    def _split_message(self, text: str, max_length: int) -> list:
        """긴 메시지를 여러 개로 분할"""
        if len(text) <= max_length:
            return [text]

        messages = []
        lines = text.split('\n')
        current_msg = ""

        for line in lines:
            if len(current_msg) + len(line) + 1 > max_length:
                if current_msg:
                    messages.append(current_msg.strip())
                current_msg = line + '\n'
            else:
                current_msg += line + '\n'

        if current_msg.strip():
            messages.append(current_msg.strip())

        return messages

    def send_simple(self, message: str) -> bool:
        """간단한 텍스트 메시지 전송"""
        if not self.webhook_url:
            print("[Discord] Webhook URL이 설정되지 않았습니다.")
            return False

        payload = {"content": message}

        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"[Discord] 메시지 전송 실패: {e}")
            return False
