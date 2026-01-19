#!/usr/bin/env python3
"""
Evolution API Client
Cliente Python para interagir com a Evolution API (WhatsApp)
"""

import time
from typing import Optional
import requests


class EvolutionAPI:
    """Cliente para a Evolution API"""
    
    def __init__(self, base_url: str = "http://localhost:8080", api_key: str = "whatsapp_sender_secret_key_2024"):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.headers = {
            "apikey": api_key,
            "Content-Type": "application/json"
        }
    
    def _request(self, method: str, endpoint: str, json_data: dict = None) -> dict:
        """Faz uma requisição para a API"""
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.request(method, url, headers=self.headers, json=json_data, timeout=30)
            if response.status_code >= 400:
                return {"error": True, "status": response.status_code, "message": response.text}
            return response.json() if response.text else {}
        except requests.exceptions.RequestException as e:
            return {"error": True, "message": str(e)}
    
    # ==================== Instância ====================
    
    def create_instance(self, instance_name: str) -> dict:
        """Cria uma nova instância do WhatsApp"""
        data = {
            "instanceName": instance_name,
            "qrcode": True,
            "integration": "WHATSAPP-BAILEYS"
        }
        return self._request("POST", "/instance/create", data)
    
    def get_instance(self, instance_name: str) -> dict:
        """Obtém informações de uma instância"""
        return self._request("GET", f"/instance/fetchInstances?instanceName={instance_name}")
    
    def list_instances(self) -> dict:
        """Lista todas as instâncias"""
        return self._request("GET", "/instance/fetchInstances")
    
    def delete_instance(self, instance_name: str) -> dict:
        """Remove uma instância"""
        return self._request("DELETE", f"/instance/delete/{instance_name}")
    
    def logout_instance(self, instance_name: str) -> dict:
        """Desconecta o WhatsApp da instância"""
        return self._request("DELETE", f"/instance/logout/{instance_name}")
    
    def restart_instance(self, instance_name: str) -> dict:
        """Reinicia uma instância"""
        return self._request("POST", f"/instance/restart/{instance_name}")
    
    # ==================== Conexão ====================
    
    def get_qrcode(self, instance_name: str) -> dict:
        """Obtém o QR Code para conectar o WhatsApp"""
        return self._request("GET", f"/instance/connect/{instance_name}")
    
    def get_connection_state(self, instance_name: str) -> dict:
        """Verifica o estado da conexão"""
        return self._request("GET", f"/instance/connectionState/{instance_name}")
    
    def is_connected(self, instance_name: str) -> bool:
        """Verifica se a instância está conectada"""
        state = self.get_connection_state(instance_name)
        return state.get("instance", {}).get("state") == "open"
    
    # ==================== Mensagens ====================
    
    def send_text(self, instance_name: str, phone: str, message: str) -> dict:
        """
        Envia uma mensagem de texto
        
        Args:
            instance_name: Nome da instância
            phone: Número do telefone (com código do país, ex: 5561999999999)
            message: Texto da mensagem
        """
        data = {
            "number": self._format_phone(phone),
            "textMessage": {
                "text": message
            }
        }
        return self._request("POST", f"/message/sendText/{instance_name}", data)
    
    def send_media(self, instance_name: str, phone: str, media_url: str, 
                   media_type: str = "image", caption: str = "") -> dict:
        """
        Envia mídia (imagem, vídeo, áudio, documento)
        
        Args:
            instance_name: Nome da instância
            phone: Número do telefone
            media_url: URL da mídia
            media_type: Tipo (image, video, audio, document)
            caption: Legenda opcional
        """
        data = {
            "number": self._format_phone(phone),
            "mediatype": media_type,
            "media": media_url,
            "caption": caption
        }
        return self._request("POST", f"/message/sendMedia/{instance_name}", data)
    
    def check_number(self, instance_name: str, phone: str) -> dict:
        """Verifica se um número tem WhatsApp"""
        data = {
            "numbers": [self._format_phone(phone)]
        }
        return self._request("POST", f"/chat/whatsappNumbers/{instance_name}", data)
    
    def has_whatsapp(self, instance_name: str, phone: str) -> bool:
        """Verifica se um número tem WhatsApp (retorna bool)"""
        result = self.check_number(instance_name, phone)
        if isinstance(result, list) and len(result) > 0:
            return result[0].get("exists", False)
        return False
    
    # ==================== Utilitários ====================
    
    @staticmethod
    def _format_phone(phone: str) -> str:
        """Formata o telefone para o padrão da API (somente números)"""
        # Remove tudo que não é número
        numbers = ''.join(filter(str.isdigit, phone))
        
        # Se não tem código do país (começa com 0 ou tem menos de 12 dígitos), adiciona 55 (Brasil)
        if numbers.startswith('0'):
            numbers = numbers[1:]
        if len(numbers) <= 11:
            numbers = f"55{numbers}"
        
        return numbers
    
    def wait_for_connection(self, instance_name: str, timeout: int = 120) -> bool:
        """
        Aguarda a conexão do WhatsApp (após escanear QR Code)
        
        Args:
            instance_name: Nome da instância
            timeout: Tempo máximo de espera em segundos
        
        Returns:
            True se conectou, False se timeout
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.is_connected(instance_name):
                return True
            time.sleep(2)
        return False


def main():
    """Exemplo de uso"""
    api = EvolutionAPI()
    
    instance_name = "meu_whatsapp"
    
    # Lista instâncias existentes
    print("📋 Instâncias existentes:")
    instances = api.list_instances()
    print(instances)
    
    # Cria uma nova instância se não existir
    print(f"\n🔧 Criando instância '{instance_name}'...")
    result = api.create_instance(instance_name)
    
    if result.get("error"):
        print(f"   Erro: {result.get('message')}")
    else:
        print("   ✓ Instância criada!")
        
        # Obtém QR Code
        print("\n📱 QR Code para conexão:")
        qr = api.get_qrcode(instance_name)
        if qr.get("base64"):
            print("   QR Code disponível - escaneie com seu WhatsApp")
            print(f"   Código: {qr.get('code', '')[:50]}...")
        
        # Aguarda conexão
        print("\n⏳ Aguardando conexão (escaneie o QR Code)...")
        if api.wait_for_connection(instance_name, timeout=60):
            print("   ✓ WhatsApp conectado!")
        else:
            print("   ✗ Timeout - QR Code não foi escaneado")


if __name__ == "__main__":
    main()
