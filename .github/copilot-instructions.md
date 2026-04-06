# Instrucoes para Agentes de IA - Clipagem Digital (Playwright)

## Visao geral

Clipagem Digital automatiza:

1. Login e download do PDF do Diario de Santa Maria via Playwright (Chromium headless).
2. Analise de conteudo com Groq Mixtral 8x7B.
3. Exibicao na interface Streamlit.
4. Commit automatico dos dados gerados em `data/`.

## URLs e credenciais

- Login: https://diariosm.com.br/assinante/login?redirect=/newflip
- Acesso: https://diariosm.com.br/assinante/newflip
- App: https://clipagem-secom.streamlit.app/

As credenciais e chaves sao carregadas por variaveis de ambiente (secret `SECRETES` no Actions).

## Estado tecnico atual

- `src/daily_scraper.py`: fluxo principal em Playwright.
- `src/analyzer.py`: analise com Groq.
- `src/app.py`: dashboard Streamlit + trigger de workflow via GH API.
- `.github/workflows/daily_run.yml`: instala Playwright + Chromium e executa scraper/analyzer.
- `.github/workflows/keep_alive.yml`: keep alive com Playwright (workflow pode permanecer pausado por `if: false`).
- `keep_alive.py`: acesso periodico da app com Playwright.

## Logs e debug obrigatorios

O scraper deve manter logs por etapa e artifacts de erro:

- `/tmp/scraper_stage.txt`
- `/tmp/scraper_stage_history.txt`
- `/tmp/login_page_loaded.*`
- `/tmp/login_error.*`
- `/tmp/playwright_error.*`
- `/tmp/playwright_timeout.*`
- `/tmp/listagem_logada.*`
- `/tmp/listagem_not_ready.*`
- `/tmp/jornal_not_found.*`

## Convencoes

- Priorizar seletores de elementos visiveis e editaveis.
- Evitar estrategias paralelas agressivas no login.
- Corrigir com mudancas pequenas e previsiveis.
- Em caso de falha, sempre salvar screenshot + HTML antes de encerrar.

## Execucao local

```bash
python -m pip install -r requirements.txt
python -m playwright install --with-deps chromium
python src/daily_scraper.py
python src/analyzer.py
streamlit run src/app.py --server.port 8501
```

## Operacao via Streamlit Cloud

- A app dispara `workflow_dispatch` no GitHub Actions com `GH_TOKEN`.
- Confirmar no run: login concluido, PDF gerado e JSON atualizado.

## Observacao

Este repositorio deve ser mantido com stack de automacao baseada em Playwright.
