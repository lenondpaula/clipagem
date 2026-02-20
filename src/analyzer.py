"""
Analisador de Clipping - Integração com Groq API
Extrai texto de PDF do Diário Oficial e realiza análise inteligente de conteúdo relevante
"""

import os
import json
import re
from pathlib import Path
from dotenv import load_dotenv
import fitz  # pymupdf
from groq import Groq


# ==================== CARREGAMENTO DE VARIÁVEIS DE AMBIENTE ====================
# Carregar variáveis do arquivo .env
env_file = os.path.join(os.path.dirname(__file__), "..", ".env")
if os.path.exists(env_file):
    print(f"[ENV] Carregando variáveis de {env_file}")
    load_dotenv(env_file, override=True)
else:
    print(f"[ENV] Arquivo .env não encontrado em {env_file}, usando variáveis do sistema")
    load_dotenv(override=True)  # Tenta carregar do .env na raiz do projeto


# ==================== CONFIGURAÇÕES ====================
PDF_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "diario_sm_atual.pdf")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "clipagem_hoje.json")
GROQ_MODEL = "mixtral-8x7b-32768"
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# Cliente Groq global
groq_client = None

# Prompt de análise de clipping - O cérebro da automação
CLIPAGEM_PROMPT = """Você é um analista de mídia da Prefeitura de Santa Maria. Analise o texto do jornal Diário de Santa Maria.

Critérios de Inclusão:
- Prefeitura de SM (Secretarias, obras, ações)
- Câmara de Vereadores
- Segurança Pública regional
- Política com impacto local
- Infraestrutura (Rodovias, UFSM)
- Caso Boate Kiss (Sempre incluir)

Formato de Saída: Retorne exclusivamente um JSON puro com: data_clipping, e uma lista chamada "noticias" contendo (pagina, titulo, resumo_120_chars, relevância).

Texto do Jornal:
{texto_extraido}"""


# ==================== EXTRAÇÃO DE PDF ====================
def extract_pdf_text():
    """Extrai texto do PDF com marcadores de página"""
    print(f"[PDF] Abrindo arquivo: {PDF_PATH}")
    
    if not os.path.exists(PDF_PATH):
        raise FileNotFoundError(f"Arquivo PDF não encontrado: {PDF_PATH}")
    
    try:
        # Abrir documento PDF
        doc = fitz.open(PDF_PATH)
        total_pages = doc.page_count
        print(f"[PDF] Total de páginas: {total_pages}")
        
        extracted_text = ""
        
        # Iterar por todas as páginas
        for page_num in range(total_pages):
            page = doc[page_num]
            text = page.get_text()
            
            # Adicionar marcador de página
            page_marker = f"\n--- Página {page_num + 1} ---\n"
            extracted_text += page_marker + text
            
            print(f"[PDF] Página {page_num + 1}/{total_pages} extraída ({len(text)} caracteres)")
        
        doc.close()
        
        total_chars = len(extracted_text)
        print(f"[PDF] Extração concluída. Total: {total_chars} caracteres")
        
        return extracted_text
        
        return extracted_text
        
    except Exception as e:
        print(f"[PDF] ERRO ao extrair texto: {e}")
        raise


# ==================== CONFIGURAÇÃO GROQ ====================
def configure_groq():
    """Configura cliente do Groq"""
    print(f"[GROQ] Configurando API do Groq...")
    
    if not GROQ_API_KEY:
        raise ValueError("Variável de ambiente GROQ_API_KEY não configurada")
    
    global groq_client
    groq_client = Groq(api_key=GROQ_API_KEY)
    print(f"[GROQ] API configurada com sucesso")


# ==================== ANÁLISE COM GROQ ====================
def analyze_with_groq(extracted_text):
    """Envia texto ao Groq para análise de clipping"""
    print(f"[GROQ] Iniciando análise com modelo {GROQ_MODEL}...")
    
    try:
        # Preparar prompt com o texto extraído
        prompt = CLIPAGEM_PROMPT.format(texto_extraido=extracted_text)
        
        print(f"[GROQ] Enviando texto para análise ({len(extracted_text)} caracteres)...")
        
        # Enviar para análise
        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,  # Baixa temperatura para consistência
            max_tokens=4000   # Limite de tokens para resposta
        )
        
        result_text = response.choices[0].message.content
        print(f"[GROQ] Resposta recebida ({len(result_text)} caracteres)")
        
        return result_text
        
    except Exception as e:
        print(f"[GEMINI] ERRO durante análise: {e}")
        raise


# ==================== LIMPEZA E PROCESSAMENTO ====================
def clean_groq_response(response_text):
    """Remove marcações de Markdown da resposta do Gemini"""
    print(f"[CLEANUP] Limpando resposta do Gemini...")
    
    # Remover blocos de código markdown ```json ... ```
    cleaned = re.sub(r"```json\s*", "", response_text)
    cleaned = re.sub(r"```\s*", "", cleaned)
    cleaned = cleaned.strip()
    
    print(f"[CLEANUP] Resposta limpa ({len(cleaned)} caracteres)")
    
    return cleaned


def validate_json(json_str):
    """Valida e faz parse do JSON"""
    print(f"[JSON] Validando JSON...")
    
    try:
        json_obj = json.loads(json_str)
        
        # Validar estrutura esperada
        if "noticias" not in json_obj:
            print("[JSON] AVISO: Campo 'noticias' não encontrado")
        
        if "data_clipping" not in json_obj:
            print("[JSON] AVISO: Campo 'data_clipping' não encontrado")
        
        print(f"[JSON] JSON válido. {len(json_obj.get('noticias', []))} notícias encontradas")
        
        return json_obj
        
    except json.JSONDecodeError as e:
        print(f"[JSON] ERRO ao fazer parse JSON: {e}")
        raise


# ==================== SALVAMENTO ====================
def save_json_output(json_obj):
    """Salva resultado JSON no arquivo de saída"""
    print(f"[OUTPUT] Salvando resultado em: {OUTPUT_PATH}")
    
    try:
        # Criar diretório se não existir
        os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
        
        # Salvar com formatação
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(json_obj, f, ensure_ascii=False, indent=2)
        
        file_size = os.path.getsize(OUTPUT_PATH)
        print(f"[OUTPUT] Arquivo salvo com sucesso ({file_size} bytes)")
        print(f"[OUTPUT] Caminho: {OUTPUT_PATH}")
        
        return OUTPUT_PATH
        
    except Exception as e:
        print(f"[OUTPUT] ERRO ao salvar arquivo: {e}")
        raise


# ==================== EXECUÇÃO PRINCIPAL ====================
def main():
    """Função principal do analisador"""
    print("=" * 70)
    print("INICIANDO ANALISADOR DE CLIPPING - GROQ MIXTRAL")
    print("=" * 70)
    
    try:
        # Etapa 1: Extrair PDF
        print("\n[ETAPA 1] Extração de PDF")
        print("-" * 70)
        extracted_text = extract_pdf_text()
        
        # Etapa 2: Configurar Groq
        print("\n[ETAPA 2] Configuração do Groq")
        print("-" * 70)
        configure_groq()
        
        # Etapa 3: Análise com Groq
        print("\n[ETAPA 3] Análise com Groq")
        print("-" * 70)
        groq_response = analyze_with_groq(extracted_text)
        
        # Etapa 4: Limpeza da resposta
        print("\n[ETAPA 4] Limpeza de Markdown")
        print("-" * 70)
        cleaned_response = clean_groq_response(groq_response)
        
        # Etapa 5: Validação JSON
        print("\n[ETAPA 5] Validação JSON")
        print("-" * 70)
        json_obj = validate_json(cleaned_response)
        
        # Etapa 6: Salvamento
        print("\n[ETAPA 6] Salvamento de Resultado")
        print("-" * 70)
        output_file = save_json_output(json_obj)
        
        print("\n" + "=" * 70)
        print(f"✓ SUCESSO! Análise concluída e salva em: {output_file}")
        print("=" * 70)
        
        return output_file
        
    except Exception as e:
        print("\n" + "=" * 70)
        print(f"✗ ERRO DURANTE EXECUÇÃO: {e}")
        print("=" * 70)
        raise


if __name__ == "__main__":
    main()
