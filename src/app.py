"""
Dashboard de Leitura - Clipagem Diario de Santa Maria
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List

import requests
import streamlit as st


DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "clipagem_hoje.json")
PDF_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "diario_sm_atual.pdf")


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

    [data-testid="stSidebar"] {
        background-color: #ffffff !important;
        border-right: 1px solid #e8e8e8;
    }

    .sidebar-card {
        background-color: #ffffff;
        border: 1px solid #e8e8e8;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }

    .sidebar-title {
        font-size: 0.95rem;
        font-weight: 700;
        color: #333333;
        margin-bottom: 0.75rem;
    }

    [data-testid="stDataFrame"] {
        border: 1px solid #e8e8e8;
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }

    [data-testid="stDataFrame"] thead tr th {
        background-color: #f7f7f7;
        color: #333333;
        font-weight: 600;
    }

    .card {
        background-color: #ffffff;
        border: 1px solid #e8e8e8;
        border-radius: 8px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }

    .header-date {
        text-align: center;
        color: #666666;
        font-size: 0.95rem;
        margin-bottom: 2rem;
        padding-bottom: 1rem;
        border-bottom: 1px solid #e0e0e0;
    }

    .waiting-message {
        text-align: center;
        color: #999999;
        padding: 3rem;
        font-size: 1.1rem;
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
</style>
"""


@st.cache_data(show_spinner=False)
def load_clipagem() -> Dict[str, Any] | None:
    if not os.path.exists(DATA_PATH):
        return None

    try:
        with open(DATA_PATH, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None


def pick_summary(payload: Dict[str, Any]) -> str:
    for key in ("resumo_gemini", "resumo", "observacao"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def find_licitacoes(noticias: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for noticia in noticias:
        titulo = str(noticia.get("titulo", ""))
        resumo = str(noticia.get("resumo_120_chars", ""))
        texto = f"{titulo} {resumo}".lower()
        if "licit" in texto:
            results.append(
                {
                    "pagina": noticia.get("pagina", "-"),
                    "titulo": titulo,
                    "resumo": resumo,
                    "relevancia": noticia.get("relevancia", ""),
                }
            )
    return results


def format_timestamp(path: str) -> str:
    if not os.path.exists(path):
        return "Arquivo ausente"
    try:
        timestamp = datetime.fromtimestamp(os.path.getmtime(path))
    except OSError:
        return "Horario indisponivel"
    return timestamp.strftime("%d/%m/%Y %H:%M:%S")


def trigger_github_action() -> tuple[bool, str]:
    url = (
        "https://api.github.com/repos/lenondpaula/clipagem/"
        "actions/workflows/daily_run.yml/dispatches"
    )
    try:
        token = st.secrets.get("GH_TOKEN", "")
    except Exception:
        return False, "GH_TOKEN nao configurado no Streamlit Secrets."
    if not token:
        return False, "GH_TOKEN nao configurado no Streamlit Secrets."

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    payload = {"ref": "main"}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=20)
    except requests.RequestException as exc:
        return False, f"Erro ao chamar GitHub API: {exc}"

    if response.status_code == 204:
        return True, "Solicitacao enviada! O robo iniciou o processamento. Aguarde cerca de 2 minutos."

    message = response.text.strip() or "Resposta inesperada da API."
    return False, f"Falha ao disparar workflow ({response.status_code}): {message}"


st.set_page_config(page_title="Clipagem - Dashboard", page_icon="🗞️", layout="wide")
st.markdown(CSS_STYLE, unsafe_allow_html=True)

st.markdown(
    "<h1 style='text-align: center; color: #333333; margin-bottom: 0;'>Dashboard de Leitura</h1>",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("<div class='sidebar-card'>", unsafe_allow_html=True)
    st.markdown("<div class='sidebar-title'>Acoes rapidas</div>", unsafe_allow_html=True)
    if st.button("Recarregar Dados"):
        st.cache_data.clear()
        st.rerun()

    if st.button("🔄 Verificar Edicao Agora"):
        ok, info_message = trigger_github_action()
        if ok:
            st.sidebar.info(info_message)
        else:
            st.sidebar.error(info_message)
    st.markdown("</div>", unsafe_allow_html=True)

clipagem = load_clipagem()

if not clipagem:
    st.markdown(
        "<div class='waiting-message'>"
        "⏳ Aguardando o processamento da edicao de hoje<br/>"
        "<small>(previsto para as 06:15)</small>"
        "</div>",
        unsafe_allow_html=True,
    )
else:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("**Status da ultima geracao**")
    col_json, col_pdf = st.columns(2)
    with col_json:
        st.caption(f"JSON: {format_timestamp(DATA_PATH)}")
    with col_pdf:
        st.caption(f"PDF: {format_timestamp(PDF_PATH)}")
    st.markdown("</div>", unsafe_allow_html=True)

    data_clipping = clipagem.get("data_clipping", "")
    if data_clipping:
        st.markdown(
            f"<div class='header-date'>📅 {data_clipping}</div>",
            unsafe_allow_html=True,
        )

    st.subheader("Resumo em destaque")
    summary = pick_summary(clipagem)
    if summary:
        st.markdown(
            f"<div class='card'>{summary}</div>",
            unsafe_allow_html=True,
        )
    else:
        st.info("Resumo ainda nao disponivel.")

    st.subheader("Licitacoes encontradas")
    noticias = clipagem.get("noticias", [])
    licitacoes = find_licitacoes(noticias) if isinstance(noticias, list) else []

    if licitacoes:
        st.dataframe(licitacoes, use_container_width=True)
    else:
        st.warning("Nenhuma licitacao identificada no clipping de hoje.")

st.subheader("PDF original")
if os.path.exists(PDF_PATH):
    with open(PDF_PATH, "rb") as pdf_file:
        st.download_button(
            label="Baixar PDF do Diario",
            data=pdf_file,
            file_name="diario_sm_atual.pdf",
            mime="application/pdf",
        )
else:
    st.info("PDF do dia ainda nao disponivel.")

st.markdown(
    """
    <div class='footer'>
        <p>
            Desenvolvido por <a href='https://github.com/lenondpaula' target='_blank'>Lenon de Paula</a>
            para a Secretaria de Comunicacao - PMSM
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
    unsafe_allow_html=True,
)
