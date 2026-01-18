# WhatsApp Sender - Evolution API

Envie mensagens WhatsApp automaticamente para contatos coletados pelo Google Scraper.

## 🚀 Setup Rápido

### 1. Inicie a Evolution API
```bash
cd /home/devaleixo/code/whatsapp_sender
docker-compose up -d
```

### 2. Instale dependências Python
```bash
pip install -r requirements.txt
```

### 3. Gere a lista de contatos (Google Scraper)
```bash
cd /home/devaleixo/code/google_scraper
python3 google_scraper.py 'escritorio advocacia sobradinho' 50
```

### 4. Envie as mensagens
```bash
cd /home/devaleixo/code/whatsapp_sender
python3 whatsapp_sender.py ../google_scraper/escritorio_advocacia_sobradinho_resultados.xlsx
```

Na primeira execução, escaneie o QR Code com seu WhatsApp.

---

## 📱 Uso Completo

### Mensagem Padrão
```bash
python3 whatsapp_sender.py contatos.xlsx
```

### Mensagem Personalizada
```bash
python3 whatsapp_sender.py contatos.xlsx "Olá {nome}! Vi seu negócio no Google e gostei muito!"
```

### Variáveis Disponíveis
| Variável | Descrição |
|----------|-----------|
| `{nome}` | Nome do negócio |
| `{telefone}` | Telefone |
| `{endereco}` | Endereço completo |
| `{avaliacao}` | Nota no Google |
| `{website}` | Site |

---

## 🔧 API Evolution

A API roda em `http://localhost:8080`

- **API Key**: `whatsapp_sender_secret_key_2024`
- **Instância padrão**: `business_sender`

### Endpoints Úteis
```bash
# Verificar se está rodando
curl http://localhost:8080/

# Listar instâncias
curl -H "apikey: whatsapp_sender_secret_key_2024" http://localhost:8080/instance/fetchInstances
```

---

## 🐳 Docker

```bash
# Iniciar
docker-compose up -d

# Parar
docker-compose down

# Ver logs
docker-compose logs -f

# Reiniciar
docker-compose restart
```

---

## ⚠️ Avisos Importantes

1. **Delay entre mensagens**: O script aguarda 5 segundos entre cada envio para evitar bloqueio
2. **Verificação de WhatsApp**: Números sem WhatsApp são pulados automaticamente
3. **Uso responsável**: Envie mensagens apenas para contatos relevantes
4. **Backup**: Seus dados de sessão ficam em um volume Docker persistente
