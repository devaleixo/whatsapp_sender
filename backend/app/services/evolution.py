import time
from typing import Optional

import requests


class EvolutionAPI:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.headers = {"apikey": api_key, "Content-Type": "application/json"}

    def _request(self, method: str, endpoint: str, json_data: dict | None = None) -> dict:
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.request(method, url, headers=self.headers, json=json_data, timeout=30)
            if response.status_code >= 400:
                return {"error": True, "status": response.status_code, "message": response.text}
            return response.json() if response.text else {}
        except requests.exceptions.RequestException as e:
            return {"error": True, "message": str(e)}

    # Instance

    def create_instance(self, instance_name: str) -> dict:
        return self._request("POST", "/instance/create", {
            "instanceName": instance_name,
            "qrcode": True,
            "integration": "WHATSAPP-BAILEYS",
        })

    def list_instances(self) -> dict:
        return self._request("GET", "/instance/fetchInstances")

    def delete_instance(self, instance_name: str) -> dict:
        return self._request("DELETE", f"/instance/delete/{instance_name}")

    def restart_instance(self, instance_name: str) -> dict:
        return self._request("POST", f"/instance/restart/{instance_name}")

    # Connection

    def get_qrcode(self, instance_name: str) -> dict:
        return self._request("GET", f"/instance/connect/{instance_name}")

    def get_connection_state(self, instance_name: str) -> dict:
        return self._request("GET", f"/instance/connectionState/{instance_name}")

    def is_connected(self, instance_name: str) -> bool:
        state = self.get_connection_state(instance_name)
        return state.get("instance", {}).get("state") == "open"

    # Messages

    def send_presence(self, instance_name: str, phone: str, presence: str = "composing", delay: float = 2.0) -> dict:
        return self._request("POST", f"/chat/sendPresence/{instance_name}", {
            "number": phone,
            "presence": presence,
            "delay": int(delay * 1000),
        })

    def send_text(self, instance_name: str, phone: str, message: str) -> dict:
        return self._request("POST", f"/message/sendText/{instance_name}", {
            "number": phone,
            "textMessage": {"text": message},
        })

    def send_text_with_typing(self, instance_name: str, phone: str, message: str, typing_delay: float = 3.0) -> dict:
        self.send_presence(instance_name, phone, "composing", typing_delay)
        time.sleep(typing_delay)
        return self.send_text(instance_name, phone, message)

    def check_number(self, instance_name: str, phone: str) -> dict:
        return self._request("POST", f"/chat/whatsappNumbers/{instance_name}", {"numbers": [phone]})

    def has_whatsapp(self, instance_name: str, phone: str) -> bool:
        result = self.check_number(instance_name, phone)
        if isinstance(result, list) and len(result) > 0:
            return result[0].get("exists", False)
        return False

    # Webhook

    def set_webhook(self, instance_name: str, url: str, events: list[str] | None = None) -> dict:
        events = events or ["MESSAGES_UPSERT", "MESSAGES_UPDATE", "CONNECTION_UPDATE"]
        return self._request("POST", f"/webhook/set/{instance_name}", {
            "enabled": True,
            "url": url,
            "events": events,
            "webhook_by_events": False,
        })

    def get_webhook(self, instance_name: str) -> dict:
        return self._request("GET", f"/webhook/find/{instance_name}")


def get_client() -> EvolutionAPI:
    from ..config import settings
    return EvolutionAPI(settings.evolution_url, settings.evolution_api_key)
