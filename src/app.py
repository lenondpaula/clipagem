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
    token = st.secrets.get("GH_TOKEN", "")
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

st.title("Dashboard de Leitura")

with st.sidebar:
    if st.button("Recarregar Dados"):
        st.cache_data.clear()
        st.rerun()

    if st.button("🔄 Verificar Edicao Agora"):
        ok, info_message = trigger_github_action()
        if ok:
            st.sidebar.info(info_message)
        else:
            st.sidebar.error(info_message)

clipagem = load_clipagem()

if not clipagem:
    st.info("Aguardando primeira clipagem...")
else:
    with st.container(border=True):
        st.markdown("**Status da ultima geracao**")
        col_json, col_pdf = st.columns(2)
        with col_json:
            st.caption(f"JSON: {format_timestamp(DATA_PATH)}")
        with col_pdf:
            st.caption(f"PDF: {format_timestamp(PDF_PATH)}")

    data_clipping = clipagem.get("data_clipping", "")
    if data_clipping:
        st.caption(f"Data da clipagem: {data_clipping}")

    st.subheader("Resumo em destaque")
    summary = pick_summary(clipagem)
    if summary:
        st.markdown(summary)
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
