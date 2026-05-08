# WhatsApp Sender v2 — Sistema Completo

Aplicação local com backend FastAPI + SQLite, frontend React, bot conversacional e Evolution API.
Tudo roda via docker-compose na sua máquina.

## Arquitetura

- **evolution-api** (`:8080`): gateway WhatsApp
- **backend** (`:8000`): FastAPI + APScheduler + SQLite em `backend/data/app.db`
- **frontend** (`:5173`): React + Vite + Tailwind (build servido por nginx, proxy `/api` → backend)

## Subir tudo (primeira vez)

```bash
cd /home/devaleixo/code/whatsapp_sender
docker compose up -d --build
```

Depois abra: http://localhost:5173

Passos iniciais:

1. **WhatsApp** → escaneie o QR Code
2. **Tipos** → crie `advocacia`, `imobiliaria`, etc.
3. **Templates** → crie templates para cada tipo (use `{nome}`, `{endereco}`, `{avaliacao}`, `{website}`)
4. **Campanhas** → crie uma campanha ligando tipo + template, importe um XLSX de contatos
5. **Campanha → Enfileirar pendentes** → ativa o envio. O worker manda respeitando horário (08–18h) e delay
6. **Dashboard** acompanha envios em tempo real
7. **Inbox** quando um contato responder, aparece aqui. Toggle bot/humano. O bot só responde se um provider LLM estiver configurado (ver abaixo)
8. **Bot** configure system prompt, keywords de handoff, horário. Ao detectar keyword, bot envia alerta para `5561993226767`

## Auto-start no boot da máquina

```bash
# Garante que o Docker inicie no boot:
sudo systemctl enable docker

# O docker-compose já tem `restart: always`.
# Basta deixar o projeto subido uma vez e o Docker sobe tudo ao ligar a máquina.
```

## Conectar um LLM real (bot começa a responder)

Hoje o bot está com provider `stub` — grava a mensagem e não responde. Para ativar:

Edite `backend/app/services/llm/` e adicione um provider, ex. `anthropic.py`:

```python
class AnthropicProvider:
    name = "claude"
    def generate_reply(self, system_prompt, history, model=None, temperature=0.7):
        # Chame a API Anthropic aqui, retorne ReplyDecision(text=..., should_handoff=...)
        ...
```

E plugue em `backend/app/services/llm/__init__.py`:

```python
if name == "claude":
    return AnthropicProvider(api_key=os.environ["ANTHROPIC_API_KEY"])
```

Depois no frontend **Bot → provider = claude** e o bot passa a responder.

## Logs

```bash
docker compose logs -f backend
docker compose logs -f evolution-api
```

## Sistema antigo

O CLI antigo (`whatsapp_sender.py`, `marketing_auto.sh`, pasta `campanhas/`) continua no repositório,
intocado. Remova manualmente quando o sistema novo estiver validado:

```bash
# Desativar cron antigo:
crontab -e  # remova a linha do marketing_auto.sh
```
