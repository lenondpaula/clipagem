# Prompt de Retomada - Clipagem (01/04/2026)

Use este prompt ao iniciar uma nova sessão do agente neste repositório.

---

Você está no projeto Clipagem Digital (Diário de Santa Maria).

Contexto atual:
- Branch: main
- Últimos commits relevantes:
  - b23715b: hardening do scraper para CI/CD
  - 6548934: remoção do bloqueio do job no daily_run.yml
- Objetivo imediato: validar execução ponta a ponta do workflow diário via trigger do Streamlit Cloud.

Mudanças recentes já aplicadas:
1. src/daily_scraper.py
- setup_chrome_driver:
  - usa --headless=new
  - usa User-Agent realista de Chrome recente
  - habilita download em headless via CDP (Page.setDownloadBehavior)
- perform_login:
  - preenchimento de usuário/senha com ActionChains, caractere a caractere
  - remoção de fallback de eventos reativos redundantes
  - espera explícita de botão Entrar habilitado (disabled ausente/falso)
  - clique do botão via ActionChains move_to_element(...).click().perform()
- wait_for_download_completion:
  - só valida PDF com tamanho > 0
  - exige tamanho estável por 2 segundos consecutivos
  - aborta com erro específico se .crdownload travar por mais de 15s

2. .github/workflows/daily_run.yml
- removido if: ${{ false }} do job clipagem-automation
- workflow_dispatch deve executar normalmente

Estado atual dos workflows:
- daily_run.yml: habilitado
- keep_alive.yml: ainda pausado com if: ${{ false }}

Atenções para a sessão:
- O analyzer atual usa Groq (mixtral-8x7b-32768), não Gemini.
- Se houver run em "skipped", verificar novamente condições no job do workflow e branch/ref do dispatch.
- Não misturar alterações de debug/docs no commit de produção do scraper.

Checklist recomendado de retomada:
1. Conferir última run no GitHub Actions e motivo de falha, se houver.
2. Validar se data/diario_sm_atual.pdf foi gerado no run.
3. Validar se data/clipagem_hoje.json foi gerado no run.
4. Se falhar no login/download, coletar artifacts de /tmp para diagnóstico.

Comandos úteis:
- git log --oneline -n 8
- git status --short
- python src/daily_scraper.py
- python src/analyzer.py
- streamlit run src/app.py --server.port 8501

---

Orientação para o agente:
- Priorizar correções objetivas que destravem a execução no Actions.
- Sempre validar com evidência (log, status de run, artifact, exit code).
- Em correções do scraper, manter foco em robustez de login, clique no PDF certo (JORNAL) e consistência de download.
