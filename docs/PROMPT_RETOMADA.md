# Prompt de Retomada - Clipagem (Playwright)

Projeto: Clipagem Digital (Diario de Santa Maria)

Estado de referencia:

- Branch: `main`
- Scraper migrado para Playwright em `src/daily_scraper.py`
- Workflow diario instala Chromium via Playwright
- Trigger principal via Streamlit Cloud usando GH API

Objetivo da retomada:

1. Validar execucao ponta a ponta via `workflow_dispatch`.
2. Confirmar login, listagem e download do PDF JORNAL.
3. Confirmar geracao de `data/clipagem_hoje.json`.

Checklist de diagnostico:

1. Ver `Actions` e status da run.
2. Conferir ultima etapa em `/tmp/scraper_stage.txt` (artifact).
3. Se falhar, baixar artifacts e analisar:
   - `/tmp/login_error.*`
   - `/tmp/playwright_error.*`
   - `/tmp/playwright_timeout.*`
   - `/tmp/listagem_not_ready.*`
   - `/tmp/jornal_not_found.*`

Comandos uteis:

```bash
git log --oneline -n 8
git status --short
python src/daily_scraper.py
python src/analyzer.py
streamlit run src/app.py --server.port 8501
```

Diretriz:

- Priorizar correcoes pequenas, objetivas e verificaveis por log/artifact.
- Evitar complexidade desnecessaria no login.
