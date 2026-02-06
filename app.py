"""
Clipagem Digital Interface - Streamlit App
Interface para visualização e compartilhamento de clipping automático do Diário de SM
"""

import os
import json
import streamlit as st
from pathlib import Path
from datetime import datetime


# ==================== CONFIGURAÇÃO STREAMLIT ====================
st.set_page_config(
    page_title="Clipagem Digital | PMSM",
    page_icon="📰",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ==================== ESTILOS CSS ====================
CSS_STYLE = """
<style>
    * {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
    }
    
    html, body {
        background-color: #ffffff !important;
        color: #333333 !important;
    }
    
    .main {
        background-color: #ffffff !important;
        padding: 2rem;
        color: #333333 !important;
    }
    
    [data-testid="stAppViewContainer"] {
        background-color: #ffffff !important;
        color: #333333 !important;
    }
    
    [data-testid="stHeader"] {
        background-color: #ffffff !important;
    }
    
    .stButton > button {
        border-radius: 6px;
        border: 1px solid #e0e0e0;
        background-color: #ffffff !important;
        color: #333333 !important;
        font-weight: 600;
        padding: 0.75rem 1.5rem;
        transition: all 0.2s ease;
    }
    
    .stButton > button:hover {
        background-color: #f5f5f5 !important;
        border-color: #999999;
        color: #333333 !important;
    }
    
    .card {
        background-color: #ffffff;
        border: 1px solid #e8e8e8;
        border-radius: 8px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    
    .card-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: #1a1a1a;
        margin-bottom: 0.5rem;
    }
    
    .card-page {
        font-size: 0.85rem;
        color: #666666;
        font-weight: 500;
        margin-left: 0.5rem;
    }
    
    .card-summary {
        font-size: 0.95rem;
        color: #555555;
        margin: 1rem 0;
        line-height: 1.5;
    }
    
    .badge {
        display: inline-block;
        padding: 0.35rem 0.75rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-top: 0.5rem;
    }
    
    .badge-alta {
        background-color: #fee2e2;
        color: #991b1b;
    }
    
    .badge-media {
        background-color: #fef3c7;
        color: #92400e;
    }
    
    .badge-baixa {
        background-color: #dbeafe;
        color: #1e40af;
    }
    
    .header-date {
        text-align: center;
        color: #666666;
        font-size: 0.95rem;
        margin-bottom: 2rem;
        padding-bottom: 1rem;
        border-bottom: 1px solid #e0e0e0;
    }
    
    .footer {
        text-align: center;
        color: #999999;
        font-size: 0.85rem;
        padding-top: 2rem;
        margin-top: 3rem;
        border-top: 1px solid #e0e0e0;
    }
    
    .footer a {
        color: #999999;
        text-decoration: none;
    }
    
    .footer a:hover {
        text-decoration: underline;
    }
    
    .waiting-message {
        text-align: center;
        color: #999999;
        padding: 3rem;
        font-size: 1.1rem;
    }
    
    .primary-button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white !important;
    }
    
    .primary-button:hover {
        background: linear-gradient(135deg, #5568d3 0%, #6a3fa3 100%);
        color: white !important;
    }
</style>
"""

st.markdown(CSS_STYLE, unsafe_allow_html=True)


# ==================== CONFIGURAÇÕES DE CAMINHOS ====================
BASE_DIR = Path(__file__).parent
JSON_PATH = BASE_DIR / "data" / "clipagem_hoje.json"
PDF_PATH = BASE_DIR / "data" / "diario_sm_atual.pdf"


# ==================== FUNÇÕES AUXILIARES ====================
def load_clipagem_data():
    """Carrega dados da clipagem do arquivo JSON"""
    if not JSON_PATH.exists():
        return None
    
    try:
        with open(JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return None


def load_pdf_for_download():
    """Carrega arquivo PDF para download"""
    if not PDF_PATH.exists():
        return None
    
    try:
        with open(PDF_PATH, "rb") as f:
            return f.read()
    except Exception as e:
        st.error(f"Erro ao carregar PDF: {e}")
        return None


def get_relevancia_badge(relevancia):
    """Retorna badge HTML baseado na relevância"""
    relevancia_lower = str(relevancia).lower().strip()
    
    if "alta" in relevancia_lower:
        return '<span class="badge badge-alta">🔴 Alta</span>'
    elif "média" in relevancia_lower or "media" in relevancia_lower:
        return '<span class="badge badge-media">🟡 Média</span>'
    elif "baixa" in relevancia_lower:
        return '<span class="badge badge-baixa">🔵 Baixa</span>'
    else:
        return f'<span class="badge badge-media">ℹ️ {relevancia}</span>'


def format_for_whatsapp(noticias, data_clipping):
    """Formata notícias para compartilhar no WhatsApp"""
    mensagem = f"📰 CLIPAGEM DIÁRIO DE SM - {data_clipping}\n\n"
    
    for noticia in noticias:
        pagina = noticia.get("pagina", "?")
        titulo = noticia.get("titulo", "Sem título")
        resumo = noticia.get("resumo_120_chars", "Sem resumo")
        relevancia = noticia.get("relevância", "N/A")
        
        mensagem += f"📄 Pág. {pagina} | {titulo}\n"
        mensagem += f"└ {resumo}\n"
        mensagem += f"└ Relevância: {relevancia}\n\n"
    
    return mensagem


# ==================== INTERFACE PRINCIPAL ====================
def main():
    # Header
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(
            "<h1 style='text-align: center; color: #333333; margin-bottom: 0;'>📰 Clipagem Digital</h1>",
            unsafe_allow_html=True
        )
    
    # Carrega dados
    clipagem_data = load_clipagem_data()
    
    # Se não houver dados, mostra mensagem de espera
    if clipagem_data is None:
        st.markdown(
            "<div class='waiting-message'>"
            "⏳ Aguardando o processamento da edição de hoje<br/>"
            "<small>(previsto para as 06:15)</small>"
            "</div>",
            unsafe_allow_html=True
        )
        return
    
    # Exibe data da clipagem
    data_clipping = clipagem_data.get("data_clipping", "Data indisponível")
    st.markdown(
        f"<div class='header-date'>📅 {data_clipping}</div>",
        unsafe_allow_html=True
    )
    
    # Botão de download do PDF
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        pdf_data = load_pdf_for_download()
        if pdf_data:
            st.download_button(
                label="📥 DESCARREGAR PDF DA EDIÇÃO",
                data=pdf_data,
                file_name="diario_sm_atual.pdf",
                mime="application/pdf",
                key="download_pdf"
            )
    
    st.markdown("---")
    
    # Exibe notícias
    noticias = clipagem_data.get("noticias", [])
    
    if not noticias:
        st.info("ℹ️ Nenhuma notícia relevante encontrada nesta edição.")
    else:
        st.markdown(f"### 📋 Notícias Identificadas ({len(noticias)})")
        
        for idx, noticia in enumerate(noticias, 1):
            pagina = noticia.get("pagina", "?")
            titulo = noticia.get("titulo", "Sem título")
            resumo = noticia.get("resumo_120_chars", "Sem resumo")
            relevancia = noticia.get("relevância", "N/A")
            
            # Card da notícia
            st.markdown(
                f"""
                <div class='card'>
                    <div style='display: flex; justify-content: space-between; align-items: baseline;'>
                        <span class='card-title'>{titulo}</span>
                        <span class='card-page'>Pág. {pagina}</span>
                    </div>
                    <div class='card-summary'>{resumo}</div>
                    <div>{get_relevancia_badge(relevancia)}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
    
    st.markdown("---")
    
    # Funcionalidade WhatsApp
    st.markdown("### 📱 Compartilhar no WhatsApp")
    
    whatsapp_text = format_for_whatsapp(noticias, data_clipping)
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.code(whatsapp_text, language="text")
    
    with col2:
        st.write("")
        st.write("")
        if st.button("📋 Copiar Texto"):
            st.success("✓ Clique para copiar o texto acima")
    
    st.markdown("---")
    
    # Rodapé
    st.markdown(
        """
        <div class='footer'>
            <p>
                Desenvolvido por <a href='https://github.com/lenondpaula' target='_blank'>Lenon de Paula</a> 
                para a Secretaria de Comunicação - PMSM
            </p>
            <p>
                Powered by Google Gemini 2.0 Flash | 
                <a href='https://github.com/lenondpaula/clipagem' target='_blank'>GitHub</a>
            </p>
            <p style='margin-top: 1rem; font-size: 0.8rem;'>
                © 2026 Lenon de Paula. Todos os direitos reservados.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
