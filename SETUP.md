# Guia de Setup - Clipagem Digital (Playwright)

## 1) Clone e ambiente

```bash
git clone https://github.com/lenondpaula/clipagem.git
cd clipagem
python -m venv .venv
source .venv/bin/activate
```

## 2) Dependencias

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m playwright install --with-deps chromium
```

## 3) Variaveis

Crie `.env` com:

```env
DIARIO_LOGIN_URL=https://diariosm.com.br/assinante/login?redirect=/newflip
DIARIO_ACCESS_URL=https://diariosm.com.br/assinante/newflip
DIARIO_USER=seu_email
DIARIO_PASS=sua_senha
GROQ_API_KEY=sua_chave
```

## 4) Testes manuais

```bash
python src/daily_scraper.py
python src/analyzer.py
streamlit run src/app.py
```

## 5) GitHub Actions

No secret `SECRETES`, inclua:

```env
DIARIO_LOGIN_URL=...
DIARIO_ACCESS_URL=...
DIARIO_USER=...
DIARIO_PASS=...
GROQ_API_KEY=...
```

No Streamlit Cloud, para disparo manual via app:

```toml
GH_TOKEN="ghp_..."
```

## Troubleshooting Playwright

### Erro de navegador nao instalado

```text
Executable doesn't exist .../chromium
```

Solucao:

```bash
python -m playwright install --with-deps chromium
```

### Timeout de login/listagem

Verifique artifacts do run:

- `/tmp/login_error.*`
- `/tmp/playwright_timeout.*`
- `/tmp/listagem_not_ready.*`

### Falha no trigger pelo Streamlit

- Confirmar `GH_TOKEN` valido no Streamlit Cloud.
- Confirmar workflow com `on: workflow_dispatch` ativo em `main`.

