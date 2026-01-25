#!/bin/bash
# =============================================================================
# WhatsApp Marketing - Script Automático (para cron)
# Envia mensagens automaticamente sem interação do usuário
# =============================================================================

set -e

# Diretórios
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CAMPANHAS_DIR="$SCRIPT_DIR/campanhas"
LOG_DIR="$SCRIPT_DIR/logs"
BLOCKLIST_FILE="$CAMPANHAS_DIR/blocklist.log"

# Cria diretório de logs
mkdir -p "$LOG_DIR"

# Arquivo de log do dia
LOG_FILE="$LOG_DIR/auto_$(date +%Y-%m-%d).log"

# Função de log
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# =============================================================================
# FUNÇÕES AUXILIARES (copiadas do script principal)
# =============================================================================

count_contacts_xlsx() {
    local xlsx_file="$1"
    python3 -c "
from openpyxl import load_workbook
wb = load_workbook('$xlsx_file')
ws = wb.active
count = sum(1 for row in ws.iter_rows(min_row=2, values_only=True) if row[0] and row[1] and str(row[1]) != 'N/A')
print(count)
" 2>/dev/null || echo "0"
}

count_sent() {
    local log_file="$1"
    if [[ -f "$log_file" ]]; then
        wc -l < "$log_file" | tr -d ' '
    else
        echo "0"
    fi
}

# =============================================================================
# ENVIO AUTOMÁTICO
# =============================================================================

enviar_auto() {
    local campanha_path="$1"
    local mensagem_file="$2"
    local limite="${3:-20}"
    
    local contatos_xlsx="$campanha_path/contatos.xlsx"
    local enviados_log="$campanha_path/enviados.log"
    local batch_xlsx="$campanha_path/batch_auto.xlsx"
    
    # Verifica se campanha existe
    if [[ ! -f "$contatos_xlsx" ]]; then
        log "❌ Campanha não encontrada: $campanha_path"
        return 1
    fi
    
    # Verifica se mensagem existe
    if [[ ! -f "$mensagem_file" ]]; then
        log "❌ Arquivo de mensagem não encontrado: $mensagem_file"
        return 1
    fi
    
    local mensagem=$(cat "$mensagem_file")
    
    log "📂 Campanha: $campanha_path"
    log "📝 Mensagem: $mensagem_file"
    log "📋 Gerando batch de até $limite contatos..."
    
    # Gera batch usando Python
    python3 << EOF
from openpyxl import load_workbook, Workbook
from openpyxl.styles import Font, PatternFill

# Carrega contatos
wb = load_workbook('$contatos_xlsx')
ws = wb.active

# Carrega enviados
enviados = set()
try:
    with open('$enviados_log', 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                telefone = line.split('|')[0]
                enviados.add(telefone)
except FileNotFoundError:
    pass

# Carrega blocklist
blocklist = set()
try:
    with open('$BLOCKLIST_FILE', 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                telefone = line.split('|')[0]
                blocklist.add(telefone)
except FileNotFoundError:
    pass

# Plataformas genéricas
GENERIC_PLATFORMS = [
    'instagram.com', 'facebook.com', 'fb.com', 'fb.me',
    'twitter.com', 'x.com', 'linkedin.com', 'tiktok.com',
    'youtube.com', 'youtu.be', 'pinterest.com',
    'wix.com', 'wixsite.com', 'weebly.com', 'squarespace.com',
    'wordpress.com', 'blogspot.com', 'blogger.com',
    'sites.google.com', 'google.com/maps', 'g.page',
    'carrd.co', 'linktree', 'linktr.ee', 'bio.link',
    'ifood.com', 'rappi.com', 'uber.com',
    'whatsapp.com', 'wa.me', 'bit.ly',
]

def needs_professional_site(website):
    if not website or website == 'N/A' or website.strip() == '':
        return True
    website_lower = website.lower().strip()
    for platform in GENERIC_PLATFORMS:
        if platform in website_lower:
            return True
    return False

# Filtra contatos
pendentes = []
for row in ws.iter_rows(min_row=2, values_only=True):
    nome = row[0] if len(row) > 0 else None
    telefone = row[1] if len(row) > 1 else None
    website = row[4] if len(row) > 4 else None
    
    if nome and telefone and str(telefone) != 'N/A':
        telefone_str = str(telefone).strip()
        if telefone_str not in enviados and telefone_str not in blocklist and needs_professional_site(website):
            pendentes.append(row)

# Pega os primeiros N
batch = pendentes[:$limite]

if not batch:
    print("EMPTY")
    exit(0)

# Cria XLSX
wb_batch = Workbook()
ws_batch = wb_batch.active
ws_batch.title = "Batch"

headers = ["Nome", "Telefone", "Endereço", "Avaliação", "Website"]
header_font = Font(bold=True, color="FFFFFF")
header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")

for col, header in enumerate(headers, 1):
    cell = ws_batch.cell(row=1, column=col, value=header)
    cell.font = header_font
    cell.fill = header_fill

for row_idx, row_data in enumerate(batch, 2):
    for col_idx, value in enumerate(row_data[:5], 1):
        ws_batch.cell(row=row_idx, column=col_idx, value=value)

ws_batch.column_dimensions['A'].width = 40
ws_batch.column_dimensions['B'].width = 18

wb_batch.save('$batch_xlsx')
print(f"OK:{len(batch)}")
EOF
    
    local result=$(python3 -c "
from openpyxl import load_workbook
try:
    wb = load_workbook('$batch_xlsx')
    ws = wb.active
    count = sum(1 for row in ws.iter_rows(min_row=2, values_only=True) if row[0])
    print(f'OK:{count}')
except:
    print('EMPTY')
" 2>/dev/null)
    
    if [[ "$result" == "EMPTY" ]] || [[ -z "$result" ]]; then
        log "⚠️ Nenhum contato pendente para enviar"
        return 0
    fi
    
    local batch_count=$(echo "$result" | cut -d: -f2)
    log "✅ Batch criado com $batch_count contatos"
    
    # Envia mensagens
    log "📤 Iniciando envio..."
    cd "$SCRIPT_DIR"
    python3 whatsapp_sender.py "$batch_xlsx" "$mensagem" -y >> "$LOG_FILE" 2>&1
    
    # Atualiza log de enviados
    python3 << EOF
from openpyxl import load_workbook
from datetime import datetime

wb = load_workbook('$batch_xlsx')
ws = wb.active

timestamp = datetime.now().isoformat()

with open('$enviados_log', 'a') as f:
    for row in ws.iter_rows(min_row=2, values_only=True):
        telefone = row[1] if len(row) > 1 else None
        if telefone and str(telefone) != 'N/A':
            f.write(f"{str(telefone).strip()}|{timestamp}|1\n")
EOF
    
    log "✅ Envio concluído! $batch_count mensagens enviadas"
    
    # Remove batch temporário
    rm -f "$batch_xlsx"
}

# =============================================================================
# ENVIO PARA TODAS AS CAMPANHAS (com limite global)
# =============================================================================

enviar_todas_campanhas_global() {
    local limite_global="${1:-20}"
    local mensagem_nome="01_apresentacao.txt"
    
    log "=========================================="
    log "🚀 Iniciando envio automático"
    log "   Limite global: $limite_global mensagens"
    log "=========================================="
    
    # Coleta TODOS os contatos pendentes de TODAS as campanhas
    local batch_global="$SCRIPT_DIR/batch_global.xlsx"
    
    python3 << EOF
from openpyxl import load_workbook, Workbook
from openpyxl.styles import Font, PatternFill
import os
import glob

campanhas_dir = '$CAMPANHAS_DIR'
blocklist_file = '$BLOCKLIST_FILE'
limite = $limite_global

# Carrega blocklist global
blocklist = set()
try:
    with open(blocklist_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                telefone = line.split('|')[0]
                blocklist.add(telefone)
except FileNotFoundError:
    pass

# Plataformas genéricas
GENERIC_PLATFORMS = [
    'instagram.com', 'facebook.com', 'fb.com', 'fb.me',
    'wix.com', 'wixsite.com', 'weebly.com', 'squarespace.com',
    'wordpress.com', 'blogspot.com', 'sites.google.com', 'g.page',
    'carrd.co', 'linktree', 'linktr.ee', 'wa.me',
]

def needs_professional_site(website):
    if not website or website == 'N/A' or website.strip() == '':
        return True
    website_lower = website.lower().strip()
    for platform in GENERIC_PLATFORMS:
        if platform in website_lower:
            return True
    return False

# Coleta todos os contatos pendentes
todos_pendentes = []

for tipo_dir in glob.glob(f"{campanhas_dir}/*/"):
    for cidade_dir in glob.glob(f"{tipo_dir}/*/"):
        contatos_xlsx = f"{cidade_dir}/contatos.xlsx"
        enviados_log = f"{cidade_dir}/enviados.log"
        mensagem_file = f"{cidade_dir}/mensagens/$mensagem_nome"
        
        if not os.path.exists(contatos_xlsx) or not os.path.exists(mensagem_file):
            continue
        
        # Carrega enviados desta campanha
        enviados = set()
        try:
            with open(enviados_log, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        telefone = line.split('|')[0]
                        enviados.add(telefone)
        except FileNotFoundError:
            pass
        
        # Carrega contatos
        try:
            wb = load_workbook(contatos_xlsx)
            ws = wb.active
            
            for row in ws.iter_rows(min_row=2, values_only=True):
                nome = row[0] if len(row) > 0 else None
                telefone = row[1] if len(row) > 1 else None
                website = row[4] if len(row) > 4 else None
                
                if nome and telefone and str(telefone) != 'N/A':
                    telefone_str = str(telefone).strip()
                    if (telefone_str not in enviados and 
                        telefone_str not in blocklist and 
                        needs_professional_site(website)):
                        # Guarda contato com info da campanha
                        todos_pendentes.append({
                            'row': row,
                            'campanha_dir': cidade_dir,
                            'mensagem_file': mensagem_file
                        })
        except:
            pass

# Pega os primeiros N do total
batch = todos_pendentes[:limite]

if not batch:
    print("EMPTY:0")
    exit(0)

# Cria XLSX global com todos os contatos
wb_batch = Workbook()
ws_batch = wb_batch.active
ws_batch.title = "Batch"

headers = ["Nome", "Telefone", "Endereço", "Avaliação", "Website", "Campanha", "Mensagem"]
header_font = Font(bold=True, color="FFFFFF")
header_fill = PatternFill(start_color="27AE60", end_color="27AE60", fill_type="solid")

for col, header in enumerate(headers, 1):
    cell = ws_batch.cell(row=1, column=col, value=header)
    cell.font = header_font
    cell.fill = header_fill

for row_idx, item in enumerate(batch, 2):
    row_data = item['row']
    for col_idx, value in enumerate(row_data[:5], 1):
        ws_batch.cell(row=row_idx, column=col_idx, value=value)
    ws_batch.cell(row=row_idx, column=6, value=item['campanha_dir'])
    ws_batch.cell(row=row_idx, column=7, value=item['mensagem_file'])

ws_batch.column_dimensions['A'].width = 35
ws_batch.column_dimensions['B'].width = 16
ws_batch.column_dimensions['F'].width = 40
ws_batch.column_dimensions['G'].width = 50

wb_batch.save('$batch_global')
print(f"OK:{len(batch)}")
EOF
    
    local result=$(python3 -c "
from openpyxl import load_workbook
try:
    wb = load_workbook('$batch_global')
    ws = wb.active
    count = sum(1 for row in ws.iter_rows(min_row=2, values_only=True) if row[0])
    print(f'OK:{count}')
except:
    print('EMPTY:0')
" 2>/dev/null)
    
    if [[ "$result" == "EMPTY:0" ]] || [[ -z "$result" ]]; then
        log "⚠️ Nenhum contato pendente para enviar"
        rm -f "$batch_global"
        return 0
    fi
    
    local batch_count=$(echo "$result" | cut -d: -f2)
    log "✅ Total de $batch_count contatos selecionados de todas as campanhas"
    
    # Envia cada contato individualmente (para usar a mensagem correta de cada campanha)
    log "📤 Iniciando envio..."
    
    python3 << EOF
from openpyxl import load_workbook
from datetime import datetime
import subprocess
import sys
import time

sys.path.insert(0, '$SCRIPT_DIR')
from evolution_client import EvolutionAPI
from whatsapp_sender import WhatsAppSender

wb = load_workbook('$batch_global')
ws = wb.active

api = EvolutionAPI()
sender = WhatsAppSender(api)

sucesso = 0
falha = 0

for row in ws.iter_rows(min_row=2, values_only=True):
    nome = row[0] if len(row) > 0 else ''
    telefone = row[1] if len(row) > 1 else None
    campanha_dir = row[5] if len(row) > 5 else None
    mensagem_file = row[6] if len(row) > 6 else None
    
    if not telefone or not mensagem_file:
        continue
    
    try:
        # Lê mensagem da campanha
        with open(mensagem_file, 'r') as f:
            mensagem = f.read()
        
        # Substitui variáveis
        mensagem = mensagem.replace('{nome}', str(nome) if nome else 'empresa')
        
        # Envia com digitando
        print(f"  📱 Enviando para {telefone}...")
        result = api.send_text_with_typing('marketing_sender', str(telefone), mensagem, typing_delay=5.0)
        
        if result.get('error'):
            print(f"     ❌ Erro: {result.get('message', 'Desconhecido')[:50]}")
            falha += 1
        else:
            print(f"     ✓ Enviado!")
            sucesso += 1
            
            # Atualiza log da campanha
            timestamp = datetime.now().isoformat()
            with open(f"{campanha_dir}/enviados.log", 'a') as log:
                log.write(f"{str(telefone).strip()}|{timestamp}|1\n")
        
        # Delay entre mensagens
        time.sleep(8)
        
    except Exception as e:
        print(f"     ❌ Erro: {str(e)[:50]}")
        falha += 1

print(f"\n✅ Enviados: {sucesso} | ❌ Falhas: {falha}")
EOF
    
    log ""
    log "=========================================="
    log "✅ Envio automático concluído!"
    log "=========================================="
    
    # Remove batch temporário
    rm -f "$batch_global"
}

# =============================================================================
# MODO DE USO
# =============================================================================

show_usage() {
    echo "Uso: $0 [opções]"
    echo ""
    echo "Opções:"
    echo "  --campanha <tipo/cidade>    Enviar para campanha específica"
    echo "  --mensagem <arquivo.txt>    Arquivo de mensagem (padrão: 01_apresentacao.txt)"
    echo "  --limite <N>                Máximo de contatos por campanha"
    echo "  --limite-global <N>         Máximo TOTAL de contatos (distribuído entre campanhas)"
    echo "  --todas                     Enviar para todas as campanhas (requer --limite ou --limite-global)"
    echo "  --help                      Mostrar esta ajuda"
    echo ""
    echo "Exemplos:"
    echo "  $0 --todas --limite-global 20   # 20 no total de todas as campanhas"
    echo "  $0 --todas --limite 5           # 5 por campanha"
    echo "  $0 --campanha corretor_imoveis/brasilia --limite 20"
}

# =============================================================================
# MAIN
# =============================================================================

main() {
    local campanha=""
    local mensagem="01_apresentacao.txt"
    local limite=20
    local limite_global=0
    local todas=false
    
    # Parseia argumentos
    while [[ $# -gt 0 ]]; do
        case $1 in
            --campanha)
                campanha="$2"
                shift 2
                ;;
            --mensagem)
                mensagem="$2"
                shift 2
                ;;
            --limite)
                limite="$2"
                shift 2
                ;;
            --limite-global)
                limite_global="$2"
                shift 2
                ;;
            --todas)
                todas=true
                shift
                ;;
            --help)
                show_usage
                exit 0
                ;;
            *)
                echo "Opção desconhecida: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # Executa
    if [[ "$todas" == true ]]; then
        if [[ $limite_global -gt 0 ]]; then
            # Limite global: N mensagens no total entre todas as campanhas
            enviar_todas_campanhas_global "$limite_global"
        else
            # Limite por campanha: N mensagens por campanha
            enviar_todas_campanhas "$mensagem" "$limite"
        fi
    elif [[ -n "$campanha" ]]; then
        local campanha_path="$CAMPANHAS_DIR/$campanha"
        local mensagem_file="$campanha_path/mensagens/$mensagem"
        enviar_auto "$campanha_path" "$mensagem_file" "$limite"
    else
        echo "❌ Especifique --campanha ou --todas"
        show_usage
        exit 1
    fi
}

# Executa
main "$@"
