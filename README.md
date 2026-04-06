# Clipagem Digital - Diario de Santa Maria

Sistema automatizado de clipping diario do Diario de Santa Maria.

- Scraper: Playwright (Chromium headless)
- Analise: Groq Mixtral 8x7B
- Interface: Streamlit Cloud
- Orquestracao: GitHub Actions

App em producao: https://clipagem-secom.streamlit.app/

## Resumo do fluxo

1. `src/daily_scraper.py` faz login e baixa o PDF mais recente da edicao JORNAL.
2. `src/analyzer.py` extrai texto do PDF e gera `data/clipagem_hoje.json`.
3. `src/app.py` exibe os dados na interface.

## Stack

- Python 3.11+
- Playwright 1.52.0
- PyMuPDF 1.24.9
- Groq 0.9.0
- Streamlit 1.53.1

## Variaveis de ambiente

```env
DIARIO_LOGIN_URL=https://diariosm.com.br/assinante/login?redirect=/newflip
DIARIO_ACCESS_URL=https://diariosm.com.br/assinante/newflip
DIARIO_USER=seu_email
DIARIO_PASS=sua_senha
GROQ_API_KEY=sua_chave
```

## Execucao local

```bash
python -m pip install -r requirements.txt
python -m playwright install --with-deps chromium
python src/daily_scraper.py
python src/analyzer.py
streamlit run src/app.py
```

## Workflows

- `daily_run.yml`: executa scraper + analyzer e auto-commit em `data/`.
- `keep_alive.yml`: acesso periodico da app por Playwright.

## Trigger via Streamlit Cloud

A app pode disparar `workflow_dispatch` com GH API (token `GH_TOKEN`).

Checklist rapido apos disparo:

1. Run entrou em `queued/running` no Actions.
2. Scraper finalizou com `data/diario_sm_atual.pdf`.
3. Analyzer gerou `data/clipagem_hoje.json`.

## Logs e debug

O scraper registra estagios em `/tmp/scraper_stage.txt` e historico em `/tmp/scraper_stage_history.txt`.

Em erro, sao salvos artifacts com:

- `/tmp/login_page_loaded.*`
- `/tmp/login_error.*`
- `/tmp/playwright_error.*`
- `/tmp/playwright_timeout.*`
- `/tmp/listagem_logada.*`
- `/tmp/listagem_not_ready.*`
- `/tmp/jornal_not_found.*`

