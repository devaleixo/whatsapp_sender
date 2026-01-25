#!/bin/bash
# =============================================================================
# WhatsApp Marketing Automation Script
# Integra google_scraper com whatsapp_sender para campanhas de marketing
# =============================================================================

set -e

# Diretórios
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRAPER_DIR="/home/devaleixo/code/google_scraper"
CAMPANHAS_DIR="$SCRIPT_DIR/campanhas"

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# =============================================================================
# FUNÇÕES AUXILIARES
# =============================================================================

print_header() {
    echo -e "${PURPLE}=====================================${NC}"
    echo -e "${PURPLE}  📣 WhatsApp Marketing Automation${NC}"
    echo -e "${PURPLE}=====================================${NC}"
}

print_separator() {
    echo -e "${BLUE}-------------------------------------${NC}"
}

# Formata nome de pasta (remove acentos, espaços -> underscores)
format_folder_name() {
    echo "$1" | sed 's/[áàãâä]/a/g; s/[éèêë]/e/g; s/[íìîï]/i/g; s/[óòõôö]/o/g; s/[úùûü]/u/g; s/[ç]/c/g' | \
    tr '[:upper:]' '[:lower:]' | tr ' ' '_' | tr -cd '[:alnum:]_'
}

# Conta linhas válidas no XLSX (aproximado via strings)
count_contacts_xlsx() {
    local xlsx_file="$1"
    # Conta linhas do xlsx usando python
    python3 -c "
from openpyxl import load_workbook
wb = load_workbook('$xlsx_file')
ws = wb.active
count = sum(1 for row in ws.iter_rows(min_row=2, values_only=True) if row[0] and row[1] and str(row[1]) != 'N/A')
print(count)
" 2>/dev/null || echo "0"
}

# Conta enviados no log
count_sent() {
    local log_file="$1"
    if [[ -f "$log_file" ]]; then
        wc -l < "$log_file" | tr -d ' '
    else
        echo "0"
    fi
}

# =============================================================================
# 1. NOVA PESQUISA (Buscar contatos no Google)
# =============================================================================

nova_pesquisa() {
    print_separator
    echo -e "${CYAN}🔎 Nova Pesquisa de Contatos${NC}"
    print_separator
    
    # Pergunta tipo de negócio
    echo -e "${YELLOW}1. Qual o tipo de negócio?${NC}"
    echo -e "   ${CYAN}(ex: escritório advocacia, imobiliária, corretor imóveis, pizzaria)${NC}"
    read -r tipo_negocio
    
    if [[ -z "$tipo_negocio" ]]; then
        echo -e "${RED}❌ Tipo de negócio não pode ser vazio${NC}"
        return 1
    fi
    
    # Pergunta cidade/região
    echo ""
    echo -e "${YELLOW}2. Qual a cidade/região?${NC}"
    echo -e "   ${CYAN}(ex: brasília, asa norte, goiânia, são paulo)${NC}"
    read -r cidade
    
    if [[ -z "$cidade" ]]; then
        echo -e "${RED}❌ Cidade não pode ser vazia${NC}"
        return 1
    fi
    
    # Formata nomes das pastas
    local tipo_folder=$(format_folder_name "$tipo_negocio")
    local cidade_folder=$(format_folder_name "$cidade")
    
    # Estrutura hierárquica: campanhas/tipo_negocio/cidade/
    local campanha_dir="$CAMPANHAS_DIR/$tipo_folder/$cidade_folder"
    
    # Variável para saber se é nova ou existente
    local is_new_campaign=true
    local existing_xlsx=""
    
    # Verifica se já existe
    if [[ -d "$campanha_dir" ]] && [[ -f "$campanha_dir/contatos.xlsx" ]]; then
        is_new_campaign=false
        existing_xlsx="$campanha_dir/contatos.xlsx"
        
        local total_atual=$(count_contacts_xlsx "$existing_xlsx")
        echo ""
        echo -e "${YELLOW}📂 Campanha '$tipo_folder/$cidade_folder' já existe com $total_atual contatos${NC}"
        echo -e "${CYAN}   Os novos resultados serão adicionados (sem duplicatas)${NC}"
        echo ""
    else
        echo ""
        echo -e "${BLUE}📂 Criando nova campanha: $tipo_folder/$cidade_folder${NC}"
    fi
    
    # Cria estrutura da campanha
    mkdir -p "$campanha_dir/mensagens"
    
    # Monta termo de busca completo
    local termo_busca="$tipo_negocio $cidade"
    
    # Executa o scraper
    echo -e "${CYAN}🔍 Buscando: '$termo_busca'...${NC}"
    cd "$SCRAPER_DIR"
    
    python3 google_scraper.py "$termo_busca" 60
    
    # Move o arquivo gerado
    local xlsx_generated=$(ls -t *_resultados.xlsx 2>/dev/null | head -1)
    
    if [[ -n "$xlsx_generated" ]]; then
        
        if [[ "$is_new_campaign" == "true" ]]; then
            # Campanha nova: apenas move o arquivo
            mv "$xlsx_generated" "$campanha_dir/contatos.xlsx"
            touch "$campanha_dir/enviados.log"
            
            # Cria mensagens de exemplo
            local tipo_mensagens="$CAMPANHAS_DIR/$tipo_folder/mensagens_padrao"
            if [[ -d "$tipo_mensagens" ]]; then
                cp "$tipo_mensagens"/*.txt "$campanha_dir/mensagens/" 2>/dev/null || true
            else
                criar_mensagens_exemplo "$campanha_dir/mensagens"
            fi
        else
            # Campanha existente: merge e remove duplicatas
            echo -e "${CYAN}🔄 Mesclando com contatos existentes...${NC}"
            
            python3 << EOF
from openpyxl import load_workbook, Workbook
from openpyxl.styles import Font, PatternFill

# Carrega contatos existentes
wb_existing = load_workbook('$existing_xlsx')
ws_existing = wb_existing.active

# Coleta telefones existentes para evitar duplicatas
existing_phones = set()
existing_rows = []
for row in ws_existing.iter_rows(min_row=2, values_only=True):
    telefone = row[1] if len(row) > 1 else None
    if telefone and str(telefone) != 'N/A':
        existing_phones.add(str(telefone).strip())
        existing_rows.append(row)

# Carrega novos contatos
wb_new = load_workbook('$xlsx_generated')
ws_new = wb_new.active

# Filtra apenas contatos novos (não duplicados)
new_contacts = []
for row in ws_new.iter_rows(min_row=2, values_only=True):
    telefone = row[1] if len(row) > 1 else None
    if telefone and str(telefone) != 'N/A':
        telefone_str = str(telefone).strip()
        if telefone_str not in existing_phones:
            new_contacts.append(row)
            existing_phones.add(telefone_str)

# Cria novo arquivo mesclado
wb_merged = Workbook()
ws_merged = wb_merged.active
ws_merged.title = "Resultados"

# Cabeçalhos
headers = ["Nome", "Telefone", "Endereço", "Avaliação", "Website"]
header_font = Font(bold=True, color="FFFFFF")
header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")

for col, header in enumerate(headers, 1):
    cell = ws_merged.cell(row=1, column=col, value=header)
    cell.font = header_font
    cell.fill = header_fill

# Adiciona contatos existentes
row_idx = 2
for row_data in existing_rows:
    for col_idx, value in enumerate(row_data[:5], 1):
        ws_merged.cell(row=row_idx, column=col_idx, value=value)
    row_idx += 1

# Adiciona novos contatos
for row_data in new_contacts:
    for col_idx, value in enumerate(row_data[:5], 1):
        ws_merged.cell(row=row_idx, column=col_idx, value=value)
    row_idx += 1

# Ajusta larguras
ws_merged.column_dimensions['A'].width = 40
ws_merged.column_dimensions['B'].width = 18
ws_merged.column_dimensions['C'].width = 50
ws_merged.column_dimensions['D'].width = 10
ws_merged.column_dimensions['E'].width = 35

wb_merged.save('$campanha_dir/contatos.xlsx')

print(f"MERGED:{len(new_contacts)}")
EOF
            
            # Remove arquivo temporário
            rm -f "$xlsx_generated"
            
            local merge_result=$(python3 -c "print('OK')" 2>/dev/null)
        fi
        
        local total=$(count_contacts_xlsx "$campanha_dir/contatos.xlsx")
        
        echo ""
        echo -e "${GREEN}✅ Operação concluída com sucesso!${NC}"
        echo -e "   📂 Tipo: $tipo_folder"
        echo -e "   📍 Cidade: $cidade_folder"
        echo -e "   📊 Total de contatos: $total"
        
        if [[ "$is_new_campaign" == "false" ]]; then
            echo -e "   🆕 Novos contatos adicionados (duplicatas removidas)"
        else
            echo -e "   📝 Mensagens de exemplo criadas"
        fi
    else
        echo -e "${RED}❌ Erro: Nenhum resultado encontrado${NC}"
        if [[ "$is_new_campaign" == "true" ]]; then
            rm -rf "$campanha_dir"
        fi
        return 1
    fi
    
    cd "$SCRIPT_DIR"
}

# =============================================================================
# 2. ENVIAR MENSAGENS (Selecionar campanha e enviar lote de 20)
# =============================================================================

enviar_mensagens() {
    print_separator
    echo -e "${CYAN}📱 Enviar Mensagens WhatsApp${NC}"
    print_separator
    
    # Lista campanhas disponíveis (estrutura hierárquica: tipo/cidade)
    if [[ ! -d "$CAMPANHAS_DIR" ]] || [[ -z "$(ls -A "$CAMPANHAS_DIR" 2>/dev/null)" ]]; then
        echo -e "${RED}❌ Nenhuma campanha encontrada. Crie uma primeiro com 'Nova Pesquisa'${NC}"
        return 1
    fi
    
    echo -e "${YELLOW}Campanhas disponíveis:${NC}"
    echo ""
    
    local i=1
    local campanhas=()
    
    # Itera sobre estrutura tipo/cidade
    for tipo_dir in "$CAMPANHAS_DIR"/*/; do
        if [[ -d "$tipo_dir" ]]; then
            local tipo_name=$(basename "$tipo_dir")
            
            for cidade_dir in "$tipo_dir"/*/; do
                if [[ -d "$cidade_dir" ]] && [[ -f "$cidade_dir/contatos.xlsx" ]]; then
                    local cidade_name=$(basename "$cidade_dir")
                    local total=$(count_contacts_xlsx "$cidade_dir/contatos.xlsx")
                    local sent=$(count_sent "$cidade_dir/enviados.log")
                    local pending=$((total - sent))
                    
                    echo -e "  ${GREEN}$i)${NC} ${PURPLE}$tipo_name${NC}/${CYAN}$cidade_name${NC}"
                    echo -e "     📊 Total: $total | ✅ Enviados: $sent | ⏳ Pendentes: $pending"
                    
                    campanhas+=("$cidade_dir")
                    ((i++))
                fi
            done
        fi
    done
    
    if [[ ${#campanhas[@]} -eq 0 ]]; then
        echo -e "${RED}❌ Nenhuma campanha encontrada${NC}"
        return 1
    fi
    
    echo ""
    echo -e "  ${RED}0)${NC} Voltar"
    echo ""
    
    read -rp "Escolha a campanha: " campanha_choice
    
    if [[ "$campanha_choice" == "0" ]] || [[ -z "$campanha_choice" ]]; then
        return 0
    fi
    
    local idx=$((campanha_choice - 1))
    if [[ $idx -lt 0 ]] || [[ $idx -ge ${#campanhas[@]} ]]; then
        echo -e "${RED}❌ Opção inválida${NC}"
        return 1
    fi
    
    local campanha_selecionada="${campanhas[$idx]}"
    local campanha_name=$(basename "$campanha_selecionada")
    
    echo ""
    echo -e "${BLUE}📂 Campanha selecionada: $campanha_name${NC}"
    
    # Lista mensagens disponíveis
    selecionar_e_enviar "$campanha_selecionada"
}

selecionar_e_enviar() {
    local campanha_dir="$1"
    local mensagens_dir="$campanha_dir/mensagens"
    
    print_separator
    echo -e "${YELLOW}Mensagens disponíveis:${NC}"
    echo ""
    
    local i=1
    local mensagens=()
    
    for msg in "$mensagens_dir"/*.txt; do
        if [[ -f "$msg" ]]; then
            local name=$(basename "$msg" .txt)
            echo -e "  ${GREEN}$i)${NC} $name"
            
            # Mostra preview (primeiras 2 linhas)
            echo -e "     ${CYAN}$(head -2 "$msg" | tr '\n' ' ' | cut -c1-60)...${NC}"
            
            mensagens+=("$msg")
            ((i++))
        fi
    done
    
    if [[ ${#mensagens[@]} -eq 0 ]]; then
        echo -e "${RED}❌ Nenhuma mensagem encontrada em $mensagens_dir${NC}"
        return 1
    fi
    
    echo ""
    echo -e "  ${RED}0)${NC} Voltar"
    echo ""
    
    read -rp "Escolha a mensagem: " msg_choice
    
    if [[ "$msg_choice" == "0" ]] || [[ -z "$msg_choice" ]]; then
        return 0
    fi
    
    local msg_idx=$((msg_choice - 1))
    if [[ $msg_idx -lt 0 ]] || [[ $msg_idx -ge ${#mensagens[@]} ]]; then
        echo -e "${RED}❌ Opção inválida${NC}"
        return 1
    fi
    
    local mensagem_selecionada="${mensagens[$msg_idx]}"
    local mensagem_conteudo=$(cat "$mensagem_selecionada")
    
    # Gera batch de 20 contatos
    gerar_e_enviar_batch "$campanha_dir" "$mensagem_conteudo"
}

gerar_e_enviar_batch() {
    local campanha_dir="$1"
    local mensagem="$2"
    local contatos_xlsx="$campanha_dir/contatos.xlsx"
    local enviados_log="$campanha_dir/enviados.log"
    local batch_xlsx="$campanha_dir/batch_atual.xlsx"
    
    echo ""
    echo -e "${CYAN}📋 Gerando lote de 20 contatos...${NC}"
    
    # Gera batch usando Python
    python3 << EOF
from openpyxl import load_workbook, Workbook
from openpyxl.styles import Font, Alignment, PatternFill
import re

# Carrega contatos
wb = load_workbook('$contatos_xlsx')
ws = wb.active

# Carrega enviados (suporta formato antigo e novo)
enviados = set()
try:
    with open('$enviados_log', 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                # Novo formato: telefone|timestamp|msg_num
                # Antigo formato: apenas telefone
                telefone = line.split('|')[0]
                enviados.add(telefone)
except FileNotFoundError:
    pass

# Carrega blocklist global (NUNCA envia para esses números)
blocklist = set()
try:
    with open('$CAMPANHAS_DIR/blocklist.log', 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                telefone = line.split('|')[0]
                blocklist.add(telefone)
except FileNotFoundError:
    pass

# Plataformas genéricas (não tem site profissional próprio)
GENERIC_PLATFORMS = [
    # Redes sociais
    'instagram.com', 'facebook.com', 'fb.com', 'fb.me',
    'twitter.com', 'x.com', 'linkedin.com', 'tiktok.com',
    'youtube.com', 'youtu.be', 'pinterest.com',
    # Plataformas de sites gratuitos/genéricos
    'wix.com', 'wixsite.com', 'weebly.com', 'squarespace.com',
    'wordpress.com', 'blogspot.com', 'blogger.com',
    'sites.google.com', 'google.com/maps', 'g.page',
    'carrd.co', 'linktree', 'linktr.ee', 'bio.link',
    # Marketplaces e diretórios
    'ifood.com', 'rappi.com', 'uber.com', 'ubereas.com',
    'mercadolivre.com', 'olx.com', 'enjoei.com',
    'getninjas.com', 'habitissimo.com',
    # Outros genéricos
    'whatsapp.com', 'wa.me', 'bit.ly', 'goo.gl',
    'page.link', 't.me', 'telegram.me',
]

def needs_professional_site(website):
    """
    Retorna True se o negócio PRECISA de um site profissional.
    - Sem website = True
    - Website genérico (Instagram, Wix, etc) = True
    - Website próprio com domínio = False
    """
    if not website or website == 'N/A' or website.strip() == '':
        return True
    
    website_lower = website.lower().strip()
    
    # Verifica se é uma plataforma genérica
    for platform in GENERIC_PLATFORMS:
        if platform in website_lower:
            return True
    
    return False

# Filtra contatos não enviados E que precisam de site profissional
pendentes = []
for row in ws.iter_rows(min_row=2, values_only=True):
    nome = row[0] if len(row) > 0 else None
    telefone = row[1] if len(row) > 1 else None
    website = row[4] if len(row) > 4 else None
    
    if nome and telefone and str(telefone) != 'N/A':
        telefone_str = str(telefone).strip()
        # Checa: não enviado + não bloqueado + precisa de site
        if telefone_str not in enviados and telefone_str not in blocklist and needs_professional_site(website):
            pendentes.append(row)

# Pega os primeiros 20
batch = pendentes[:20]

if not batch:
    print("EMPTY")
    exit(0)

# Cria novo XLSX com o batch
wb_batch = Workbook()
ws_batch = wb_batch.active
ws_batch.title = "Batch"

# Cabeçalhos
headers = ["Nome", "Telefone", "Endereço", "Avaliação", "Website"]
header_font = Font(bold=True, color="FFFFFF")
header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")

for col, header in enumerate(headers, 1):
    cell = ws_batch.cell(row=1, column=col, value=header)
    cell.font = header_font
    cell.fill = header_fill

# Dados
for row_idx, row_data in enumerate(batch, 2):
    for col_idx, value in enumerate(row_data[:5], 1):
        ws_batch.cell(row=row_idx, column=col_idx, value=value)

# Ajusta larguras
ws_batch.column_dimensions['A'].width = 40
ws_batch.column_dimensions['B'].width = 18
ws_batch.column_dimensions['C'].width = 50
ws_batch.column_dimensions['D'].width = 10
ws_batch.column_dimensions['E'].width = 35

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
        echo -e "${YELLOW}⚠️  Todos os contatos desta campanha já foram enviados!${NC}"
        return 0
    fi
    
    local batch_count=$(echo "$result" | cut -d: -f2)
    
    echo -e "${GREEN}✅ Batch criado com $batch_count contatos${NC}"
    
    # Mostra preview da mensagem
    echo ""
    print_separator
    echo -e "${YELLOW}📝 Mensagem que será enviada:${NC}"
    print_separator
    echo "$mensagem"
    print_separator
    echo ""
    
    read -rp "⚠️  Deseja enviar para $batch_count contatos? (s/N): " confirma
    
    if [[ "$confirma" != "s" ]] && [[ "$confirma" != "S" ]]; then
        echo -e "${YELLOW}Operação cancelada${NC}"
        rm -f "$batch_xlsx"
        return 0
    fi
    
    # Executa o whatsapp_sender
    echo ""
    echo -e "${CYAN}📤 Iniciando envio...${NC}"
    
    cd "$SCRIPT_DIR"
    python3 whatsapp_sender.py "$batch_xlsx" "$mensagem" -y
    
    # Atualiza log de enviados COM TIMESTAMP (para remarketing)
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
            # Formato: telefone|timestamp|mensagem_numero
            f.write(f"{str(telefone).strip()}|{timestamp}|1\n")

print("Log atualizado")
EOF
    
    echo ""
    echo -e "${GREEN}✅ Envio concluído! Log de enviados atualizado.${NC}"
    
    # Remove batch temporário
    rm -f "$batch_xlsx"
}

# =============================================================================
# 3. VER ESTATÍSTICAS DAS CAMPANHAS
# =============================================================================

ver_estatisticas() {
    print_separator
    echo -e "${CYAN}📊 Estatísticas das Campanhas${NC}"
    print_separator
    
    if [[ ! -d "$CAMPANHAS_DIR" ]] || [[ -z "$(ls -A "$CAMPANHAS_DIR" 2>/dev/null)" ]]; then
        echo -e "${YELLOW}Nenhuma campanha encontrada${NC}"
        return 0
    fi
    
    echo ""
    printf "%-35s %10s %10s %10s\n" "TIPO/CIDADE" "TOTAL" "ENVIADOS" "PENDENTES"
    echo "-------------------------------------------------------------------"
    
    # Itera sobre estrutura tipo/cidade
    for tipo_dir in "$CAMPANHAS_DIR"/*/; do
        if [[ -d "$tipo_dir" ]]; then
            local tipo_name=$(basename "$tipo_dir")
            
            for cidade_dir in "$tipo_dir"/*/; do
                if [[ -d "$cidade_dir" ]] && [[ -f "$cidade_dir/contatos.xlsx" ]]; then
                    local cidade_name=$(basename "$cidade_dir")
                    local total=$(count_contacts_xlsx "$cidade_dir/contatos.xlsx")
                    local sent=$(count_sent "$cidade_dir/enviados.log")
                    local pending=$((total - sent))
                    
                    printf "%-35s %10s %10s %10s\n" "$tipo_name/$cidade_name" "$total" "$sent" "$pending"
                fi
            done
        fi
    done
    
    echo ""
}

# =============================================================================
# 4. EDITAR MENSAGENS
# =============================================================================

editar_mensagens() {
    print_separator
    echo -e "${CYAN}✏️  Editar Mensagens${NC}"
    print_separator
    
    if [[ ! -d "$CAMPANHAS_DIR" ]] || [[ -z "$(ls -A "$CAMPANHAS_DIR" 2>/dev/null)" ]]; then
        echo -e "${RED}❌ Nenhuma campanha encontrada${NC}"
        return 1
    fi
    
    echo -e "${YELLOW}Campanhas disponíveis:${NC}"
    echo ""
    
    local i=1
    local campanhas=()
    
    # Itera sobre estrutura tipo/cidade
    for tipo_dir in "$CAMPANHAS_DIR"/*/; do
        if [[ -d "$tipo_dir" ]]; then
            local tipo_name=$(basename "$tipo_dir")
            
            for cidade_dir in "$tipo_dir"/*/; do
                if [[ -d "$cidade_dir" ]] && [[ -f "$cidade_dir/contatos.xlsx" ]]; then
                    local cidade_name=$(basename "$cidade_dir")
                    echo -e "  ${GREEN}$i)${NC} ${PURPLE}$tipo_name${NC}/${CYAN}$cidade_name${NC}"
                    campanhas+=("$cidade_dir")
                    ((i++))
                fi
            done
        fi
    done
    
    if [[ ${#campanhas[@]} -eq 0 ]]; then
        echo -e "${RED}❌ Nenhuma campanha encontrada${NC}"
        return 1
    fi
    
    echo ""
    echo -e "  ${RED}0)${NC} Voltar"
    echo ""
    
    read -rp "Escolha a campanha: " choice
    
    if [[ "$choice" == "0" ]] || [[ -z "$choice" ]]; then
        return 0
    fi
    
    local idx=$((choice - 1))
    if [[ $idx -lt 0 ]] || [[ $idx -ge ${#campanhas[@]} ]]; then
        echo -e "${RED}❌ Opção inválida${NC}"
        return 1
    fi
    
    local mensagens_dir="${campanhas[$idx]}/mensagens"
    
    echo ""
    echo -e "${CYAN}Abrindo pasta de mensagens...${NC}"
    
    # Tenta abrir com editor padrão
    if command -v code &> /dev/null; then
        code "$mensagens_dir"
    elif command -v nano &> /dev/null; then
        nano "$mensagens_dir"/*.txt
    else
        echo -e "${YELLOW}Pasta: $mensagens_dir${NC}"
        ls -la "$mensagens_dir"
    fi
}

# =============================================================================
# CRIAR MENSAGENS DE EXEMPLO
# =============================================================================

criar_mensagens_exemplo() {
    local mensagens_dir="$1"
    
    # Mensagem 1: Apresentação
    cat > "$mensagens_dir/01_apresentacao.txt" << 'EOFMSG'
Olá! Tudo bem?

Sou desenvolvedor especializado em *sites e automações* para empresas.

Vi que a *{nome}* pode se beneficiar de uma presença digital mais profissional.

Posso ajudar com:
✅ Sites modernos e responsivos
✅ Sistemas de agendamento online
✅ Automação de WhatsApp
✅ Aparecer no topo do Google

Gostaria de saber mais? Me responda aqui!
EOFMSG

    # Mensagem 2: Site Profissional
    cat > "$mensagens_dir/02_site_profissional.txt" << 'EOFMSG'
Olá! 👋

Percebi que a *{nome}* ainda não tem um site profissional.

Hoje em dia, *90% dos clientes pesquisam no Google* antes de fechar negócio.

Desenvolvo sites modernos por um valor acessível:
💼 Design exclusivo
📱 Funciona em celular e computador
🔍 Otimizado para aparecer no Google
⚡ Entrega em até 7 dias

Quer ver alguns exemplos do meu trabalho?
EOFMSG

    # Mensagem 3: Automação
    cat > "$mensagens_dir/03_automacao.txt" << 'EOFMSG'
Olá!

Você sabia que é possível *automatizar o atendimento* da *{nome}*?

Com automação via WhatsApp você pode:
🤖 Responder clientes 24h por dia
📅 Agendar serviços automaticamente
📊 Organizar todos os leads
💰 Aumentar suas vendas

Já ajudei várias empresas a economizar tempo e vender mais.

Posso te mostrar como funciona?
EOFMSG

    # Mensagem 4: Follow-up (Auto cron)
    cat > "$mensagens_dir/followup_48h.txt" << 'EOFMSG'
Olá {nome}! 👋 Passando aqui só porque esqueci de comentar um detalhe...

Além do sistema próprio, eu também configuro toda a parte de *automação de WhatsApp* para você não perder nenhum lead (como este aqui).

O sistema responde na hora, qualifica o cliente e já agenda a visita. 🤖

Se quiser, posso te mandar um vídeo de 1min mostrando isso funcionando na prática. O que acha?
EOFMSG

    echo -e "${GREEN}✅ Mensagens de exemplo criadas${NC}"
}

# =============================================================================
# 5. REMARKETING (Follow-up após 48h)
# =============================================================================

remarketing_followup() {
    print_separator
    echo -e "${CYAN}🔄 Remarketing - Follow-up 48h${NC}"
    print_separator
    
    # Lista campanhas disponíveis
    if [[ ! -d "$CAMPANHAS_DIR" ]] || [[ -z "$(ls -A "$CAMPANHAS_DIR" 2>/dev/null)" ]]; then
        echo -e "${RED}❌ Nenhuma campanha encontrada${NC}"
        return 1
    fi
    
    echo -e "${YELLOW}Campanhas disponíveis:${NC}"
    echo ""
    
    local i=1
    local campanhas=()
    
    for tipo_dir in "$CAMPANHAS_DIR"/*/; do
        if [[ -d "$tipo_dir" ]]; then
            local tipo_name=$(basename "$tipo_dir")
            
            for cidade_dir in "$tipo_dir"/*/; do
                if [[ -d "$cidade_dir" ]] && [[ -f "$cidade_dir/contatos.xlsx" ]]; then
                    local cidade_name=$(basename "$cidade_dir")
                    
                    # Conta elegíveis para remarketing
                    local remarketing_count=$(python3 << EOF
from datetime import datetime, timedelta

eligible = 0
try:
    with open('${cidade_dir}enviados.log', 'r') as f:
        for line in f:
            parts = line.strip().split('|')
            if len(parts) >= 3:
                timestamp_str = parts[1]
                msg_num = int(parts[2])
                try:
                    sent_time = datetime.fromisoformat(timestamp_str)
                    hours_ago = (datetime.now() - sent_time).total_seconds() / 3600
                    # Elegível: 48h+ desde último envio E menos de 3 mensagens enviadas
                    if hours_ago >= 48 and msg_num < 3:
                        eligible += 1
                except:
                    pass
except:
    pass
print(eligible)
EOF
)
                    
                    echo -e "  ${GREEN}$i)${NC} ${PURPLE}$tipo_name${NC}/${CYAN}$cidade_name${NC}"
                    echo -e "     🔄 Elegíveis para remarketing: $remarketing_count"
                    
                    campanhas+=("$cidade_dir")
                    ((i++))
                fi
            done
        fi
    done
    
    if [[ ${#campanhas[@]} -eq 0 ]]; then
        echo -e "${RED}❌ Nenhuma campanha encontrada${NC}"
        return 1
    fi
    
    echo ""
    echo -e "  ${RED}0)${NC} Voltar"
    echo ""
    
    read -rp "Escolha a campanha: " campanha_choice
    
    if [[ "$campanha_choice" == "0" ]] || [[ -z "$campanha_choice" ]]; then
        return 0
    fi
    
    local idx=$((campanha_choice - 1))
    if [[ $idx -lt 0 ]] || [[ $idx -ge ${#campanhas[@]} ]]; then
        echo -e "${RED}❌ Opção inválida${NC}"
        return 1
    fi
    
    local campanha_selecionada="${campanhas[$idx]}"
    
    # Gera batch de remarketing
    gerar_batch_remarketing "$campanha_selecionada"
}

gerar_batch_remarketing() {
    local campanha_dir="$1"
    local contatos_xlsx="$campanha_dir/contatos.xlsx"
    local enviados_log="$campanha_dir/enviados.log"
    local batch_xlsx="$campanha_dir/batch_remarketing.xlsx"
    local mensagens_dir="$campanha_dir/mensagens"
    
    echo ""
    echo -e "${CYAN}📋 Gerando lote de remarketing (48h+)...${NC}"
    
    # Gera batch de remarketing usando Python
    python3 << EOF
from openpyxl import load_workbook, Workbook
from openpyxl.styles import Font, PatternFill
from datetime import datetime, timedelta

# Carrega contatos
wb = load_workbook('$contatos_xlsx')
ws = wb.active

# Carrega log de enviados e identifica elegíveis para remarketing
remarketing_eligible = {}  # telefone -> (timestamp, msg_num)
try:
    with open('$enviados_log', 'r') as f:
        for line in f:
            parts = line.strip().split('|')
            if len(parts) >= 3:
                telefone = parts[0]
                timestamp_str = parts[1]
                msg_num = int(parts[2])
                try:
                    sent_time = datetime.fromisoformat(timestamp_str)
                    hours_ago = (datetime.now() - sent_time).total_seconds() / 3600
                    
                    # Elegível: 48h+ desde último envio E menos de 3 mensagens
                    if hours_ago >= 48 and msg_num < 3:
                        # Guarda o mais recente para cada telefone
                        if telefone not in remarketing_eligible or sent_time > remarketing_eligible[telefone][0]:
                            remarketing_eligible[telefone] = (sent_time, msg_num)
                except:
                    pass
            elif len(parts) == 1:
                # Formato antigo (só telefone) - assume 48h+
                telefone = parts[0]
                remarketing_eligible[telefone] = (datetime.now() - timedelta(hours=48), 1)
except:
    pass

# Busca dados dos contatos elegíveis
batch = []
for row in ws.iter_rows(min_row=2, values_only=True):
    telefone = row[1] if len(row) > 1 else None
    if telefone and str(telefone) != 'N/A':
        telefone_str = str(telefone).strip()
        if telefone_str in remarketing_eligible:
            batch.append((row, remarketing_eligible[telefone_str][1]))

# Limita a 20
batch = batch[:20]

if not batch:
    print("EMPTY")
    exit(0)

# Cria XLSX com batch de remarketing
wb_batch = Workbook()
ws_batch = wb_batch.active
ws_batch.title = "Remarketing"

headers = ["Nome", "Telefone", "Endereço", "Avaliação", "Website", "Msg_Anterior"]
header_font = Font(bold=True, color="FFFFFF")
header_fill = PatternFill(start_color="E67E22", end_color="E67E22", fill_type="solid")

for col, header in enumerate(headers, 1):
    cell = ws_batch.cell(row=1, column=col, value=header)
    cell.font = header_font
    cell.fill = header_fill

for row_idx, (row_data, msg_num) in enumerate(batch, 2):
    for col_idx, value in enumerate(row_data[:5], 1):
        ws_batch.cell(row=row_idx, column=col_idx, value=value)
    ws_batch.cell(row=row_idx, column=6, value=msg_num)

ws_batch.column_dimensions['A'].width = 40
ws_batch.column_dimensions['B'].width = 18
ws_batch.column_dimensions['C'].width = 50

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
        echo -e "${YELLOW}⚠️  Nenhum contato elegível para remarketing (48h+)${NC}"
        return 0
    fi
    
    local batch_count=$(echo "$result" | cut -d: -f2)
    
    echo -e "${GREEN}✅ $batch_count contatos elegíveis para follow-up${NC}"
    
    # Mensagem de follow-up padrão
    local mensagem_followup="Olá! 👋

Entrei em contato há alguns dias sobre desenvolvimento de *sites profissionais* para a *{nome}*.

Sei que você deve estar ocupado(a), mas queria saber se teve a chance de pensar sobre isso?

🎁 *Oferta especial*: Se fechar até o fim da semana, ganhe:
✅ Hospedagem grátis por 1 ano
✅ Domínio .com.br incluso
✅ Suporte prioritário

Posso esclarecer alguma dúvida? 😊"
    
    # Verifica se existe mensagem de follow-up personalizada
    if [[ -f "$mensagens_dir/followup_48h.txt" ]]; then
        mensagem_followup=$(cat "$mensagens_dir/followup_48h.txt")
    fi
    
    echo ""
    print_separator
    echo -e "${YELLOW}📝 Mensagem de Follow-up:${NC}"
    print_separator
    echo "$mensagem_followup"
    print_separator
    echo ""
    
    read -rp "⚠️  Deseja enviar follow-up para $batch_count contatos? (s/N): " confirma
    
    if [[ "$confirma" != "s" ]] && [[ "$confirma" != "S" ]]; then
        echo -e "${YELLOW}Operação cancelada${NC}"
        rm -f "$batch_xlsx"
        return 0
    fi
    
    # Envia mensagens
    echo ""
    echo -e "${CYAN}📤 Enviando follow-up...${NC}"
    
    cd "$SCRIPT_DIR"
    python3 whatsapp_sender.py "$batch_xlsx" "$mensagem_followup" -y
    
    # Atualiza log incrementando o número da mensagem
    python3 << EOF
from openpyxl import load_workbook
from datetime import datetime

wb = load_workbook('$batch_xlsx')
ws = wb.active

timestamp = datetime.now().isoformat()

# Lê log atual
log_entries = {}
try:
    with open('$enviados_log', 'r') as f:
        for line in f:
            parts = line.strip().split('|')
            if len(parts) >= 3:
                telefone = parts[0]
                log_entries[telefone] = parts
except:
    pass

# Atualiza com novo envio
with open('$enviados_log', 'w') as f:
    updated_phones = set()
    
    for row in ws.iter_rows(min_row=2, values_only=True):
        telefone = row[1] if len(row) > 1 else None
        msg_anterior = row[5] if len(row) > 5 else 1
        
        if telefone and str(telefone) != 'N/A':
            telefone_str = str(telefone).strip()
            new_msg_num = int(msg_anterior) + 1 if msg_anterior else 2
            f.write(f"{telefone_str}|{timestamp}|{new_msg_num}\n")
            updated_phones.add(telefone_str)
    
    # Mantém os outros registros que não foram atualizados
    for telefone, parts in log_entries.items():
        if telefone not in updated_phones:
            f.write('|'.join(parts) + '\n')

print("Log atualizado")
EOF
    
    echo ""
    echo -e "${GREEN}✅ Follow-up enviado com sucesso!${NC}"
    
    rm -f "$batch_xlsx"
}

# =============================================================================
# 6. GERENCIAR CONTATOS (Leads e Blocklist)
# =============================================================================

LEADS_FILE="$CAMPANHAS_DIR/leads.log"
BLOCKLIST_FILE="$CAMPANHAS_DIR/blocklist.log"

gerenciar_contatos() {
    while true; do
        print_separator
        echo -e "${CYAN}👥 Gerenciar Contatos${NC}"
        print_separator
        echo ""
        echo -e "  ${GREEN}1)${NC} ⭐ Marcar como Lead (interessado)"
        echo -e "  ${GREEN}2)${NC} 🚫 Adicionar à Blocklist (não enviar)"
        echo -e "  ${GREEN}3)${NC} 📋 Ver Leads"
        echo -e "  ${GREEN}4)${NC} 📋 Ver Blocklist"
        echo -e "  ${GREEN}5)${NC} ❌ Remover da Blocklist"
        echo ""
        echo -e "  ${RED}0)${NC} Voltar"
        echo ""
        
        read -rp "Escolha uma opção: " opcao
        
        case $opcao in
            1) marcar_lead ;;
            2) adicionar_blocklist ;;
            3) ver_leads ;;
            4) ver_blocklist ;;
            5) remover_blocklist ;;
            0) return ;;
            *) echo -e "${RED}❌ Opção inválida${NC}" ;;
        esac
    done
}

marcar_lead() {
    echo ""
    echo -e "${YELLOW}⭐ Marcar contato como Lead${NC}"
    
    # Lista campanhas disponíveis
    echo -e "${CYAN}   Campanhas disponíveis:${NC}"
    local i=1
    local campanhas=()
    
    for tipo_dir in "$CAMPANHAS_DIR"/*/; do
        if [[ -d "$tipo_dir" ]]; then
            local tipo_name=$(basename "$tipo_dir")
            for cidade_dir in "$tipo_dir"/*/; do
                if [[ -d "$cidade_dir" ]] && [[ -f "$cidade_dir/contatos.xlsx" ]]; then
                    local cidade_name=$(basename "$cidade_dir")
                    echo -e "     ${GREEN}$i)${NC} $tipo_name/$cidade_name"
                    campanhas+=("$tipo_name/$cidade_name")
                    ((i++))
                fi
            done
        fi
    done
    
    if [[ ${#campanhas[@]} -eq 0 ]]; then
        echo -e "${YELLOW}   Nenhuma campanha disponível${NC}"
        return
    fi
    
    echo ""
    read -rp "   Qual campanha? (número): " camp_choice
    
    local camp_idx=$((camp_choice - 1))
    if [[ $camp_idx -lt 0 ]] || [[ $camp_idx -ge ${#campanhas[@]} ]]; then
        echo -e "${RED}❌ Opção inválida${NC}"
        return
    fi
    
    local campanha="${campanhas[$camp_idx]}"
    
    echo ""
    echo -e "${CYAN}   Digite o número de telefone do lead:${NC}"
    read -r telefone
    
    if [[ -z "$telefone" ]]; then
        echo -e "${RED}❌ Telefone não pode ser vazio${NC}"
        return
    fi
    
    # Formata número
    local numero=$(echo "$telefone" | tr -cd '0-9')
    
    echo -e "${CYAN}   Qual o interesse? (ex: site, automação, ambos):${NC}"
    read -r interesse
    
    local timestamp=$(date -Iseconds)
    
    # Adiciona ao arquivo de leads
    touch "$LEADS_FILE"
    # Formato: telefone|interesse|campanha|timestamp
    echo "${numero}|${interesse:-geral}|${campanha}|${timestamp}" >> "$LEADS_FILE"
    
    echo ""
    echo -e "${GREEN}✅ Lead adicionado com sucesso!${NC}"
    echo -e "   📞 Telefone: $numero"
    echo -e "   ⭐ Interesse: ${interesse:-geral}"
    echo -e "   📂 Campanha: $campanha"
}

adicionar_blocklist() {
    echo ""
    echo -e "${YELLOW}🚫 Adicionar à Blocklist (Não Enviar Mais)${NC}"
    echo -e "${CYAN}   Digite o número de telefone:${NC}"
    read -r telefone
    
    if [[ -z "$telefone" ]]; then
        echo -e "${RED}❌ Telefone não pode ser vazio${NC}"
        return
    fi
    
    # Formata número
    local numero=$(echo "$telefone" | tr -cd '0-9')
    
    echo -e "${CYAN}   Motivo (opcional):${NC}"
    read -r motivo
    
    local timestamp=$(date -Iseconds)
    
    # Adiciona ao arquivo de blocklist
    touch "$BLOCKLIST_FILE"
    
    # Verifica se já existe
    if grep -q "^${numero}|" "$BLOCKLIST_FILE" 2>/dev/null; then
        echo -e "${YELLOW}⚠️  Este número já está na blocklist${NC}"
        return
    fi
    
    echo "${numero}|${motivo:-pediu para não receber}|${timestamp}" >> "$BLOCKLIST_FILE"
    
    echo ""
    echo -e "${GREEN}✅ Número adicionado à blocklist!${NC}"
    echo -e "   📞 Telefone: $numero"
    echo -e "   🚫 Este número não receberá mais mensagens"
}

ver_leads() {
    echo ""
    echo -e "${CYAN}⭐ Leads Cadastrados${NC}"
    print_separator
    
    if [[ ! -f "$LEADS_FILE" ]] || [[ ! -s "$LEADS_FILE" ]]; then
        echo -e "${YELLOW}Nenhum lead cadastrado${NC}"
        return
    fi
    
    echo ""
    printf "%-16s %-15s %-25s %-12s\n" "TELEFONE" "INTERESSE" "CAMPANHA" "DATA"
    echo "-----------------------------------------------------------------------"
    
    while IFS='|' read -r telefone interesse campanha timestamp; do
        local data=$(echo "$timestamp" | cut -d'T' -f1)
        printf "%-16s %-15s %-25s %-12s\n" "$telefone" "${interesse:0:13}" "${campanha:0:23}" "$data"
    done < "$LEADS_FILE"
    
    echo ""
    local total=$(wc -l < "$LEADS_FILE")
    echo -e "${GREEN}Total: $total leads${NC}"
}

ver_blocklist() {
    echo ""
    echo -e "${CYAN}🚫 Blocklist (Não Enviar)${NC}"
    print_separator
    
    if [[ ! -f "$BLOCKLIST_FILE" ]] || [[ ! -s "$BLOCKLIST_FILE" ]]; then
        echo -e "${YELLOW}Blocklist vazia${NC}"
        return
    fi
    
    echo ""
    printf "%-18s %-30s %-12s\n" "TELEFONE" "MOTIVO" "DATA"
    echo "-----------------------------------------------------------"
    
    while IFS='|' read -r telefone motivo timestamp; do
        local data=$(echo "$timestamp" | cut -d'T' -f1)
        printf "%-18s %-30s %-12s\n" "$telefone" "${motivo:0:28}" "$data"
    done < "$BLOCKLIST_FILE"
    
    echo ""
    local total=$(wc -l < "$BLOCKLIST_FILE")
    echo -e "${RED}Total: $total bloqueados${NC}"
}

remover_blocklist() {
    echo ""
    echo -e "${YELLOW}❌ Remover da Blocklist${NC}"
    echo -e "${CYAN}   Digite o número de telefone para remover:${NC}"
    read -r telefone
    
    if [[ -z "$telefone" ]]; then
        echo -e "${RED}❌ Telefone não pode ser vazio${NC}"
        return
    fi
    
    local numero=$(echo "$telefone" | tr -cd '0-9')
    
    if [[ ! -f "$BLOCKLIST_FILE" ]]; then
        echo -e "${YELLOW}Blocklist vazia${NC}"
        return
    fi
    
    if grep -q "^${numero}|" "$BLOCKLIST_FILE"; then
        grep -v "^${numero}|" "$BLOCKLIST_FILE" > "$BLOCKLIST_FILE.tmp"
        mv "$BLOCKLIST_FILE.tmp" "$BLOCKLIST_FILE"
        echo -e "${GREEN}✅ Número removido da blocklist${NC}"
    else
        echo -e "${YELLOW}⚠️  Número não encontrado na blocklist${NC}"
    fi
}

# =============================================================================
# MENU PRINCIPAL
# =============================================================================

menu_principal() {
    while true; do
        echo ""
        print_header
        echo ""
        echo -e "  ${GREEN}1)${NC} 🔎 Nova pesquisa (buscar contatos)"
        echo -e "  ${GREEN}2)${NC} 📱 Enviar mensagens (lote de 20)"
        echo -e "  ${GREEN}3)${NC} 🔄 Remarketing (follow-up 48h)"
        echo -e "  ${GREEN}4)${NC} 📊 Ver estatísticas"
        echo -e "  ${GREEN}5)${NC} ✏️  Editar mensagens"
        echo -e "  ${GREEN}6)${NC} 👥 Gerenciar contatos (leads/blocklist)"
        echo ""
        echo -e "  ${RED}0)${NC} 🔙 Sair"
        echo ""
        
        read -rp "Escolha uma opção: " opcao
        
        case $opcao in
            1) nova_pesquisa ;;
            2) enviar_mensagens ;;
            3) remarketing_followup ;;
            4) ver_estatisticas ;;
            5) editar_mensagens ;;
            6) gerenciar_contatos ;;
            0) echo -e "${CYAN}👋 Até mais!${NC}"; break ;;
            *) echo -e "${RED}❌ Opção inválida${NC}" ;;
        esac
    done
}

# =============================================================================
# INICIALIZAÇÃO
# =============================================================================

# Cria diretório de campanhas se não existir
mkdir -p "$CAMPANHAS_DIR"

# Executa menu se chamado diretamente
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    menu_principal
fi
