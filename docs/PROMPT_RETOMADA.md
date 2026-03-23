# Prompt de Retomada - Clipagem Digital

Use este prompt quando quiser continuar o trabalho em uma nova conversa sem perder contexto.

## Template

```text
Continuar exatamente do ponto anterior no projeto Clipagem Digital.

Contexto operacional:
- Repositorio: lenondpaula/clipagem (branch main)
- Stack: Python + Selenium + Streamlit + GitHub Actions
- Fluxo: daily_scraper.py -> analyzer.py -> data/clipagem_hoje.json -> src/app.py
- Trigger manual via app: botao "Verificar Edicao Agora" chama workflow_dispatch do daily_run.yml

Objetivo desta retomada:
- [descreva aqui em 1-3 linhas o que precisa terminar]

Estado atual conhecido:
- [adicione o que ja foi feito]
- [adicione erros, logs ou prints]

Tarefas que devem ser executadas agora:
1. Diagnosticar causa raiz.
2. Aplicar correcao minima com seguranca.
3. Validar com teste local ou por workflow_dispatch.
4. Entregar resumo objetivo com arquivos alterados e proximo passo.

Regras de execucao:
- Nao reverter alteracoes nao relacionadas.
- Preservar estilo do codigo existente.
- Fazer mudancas pequenas e verificaveis.
- Se houver bloqueio externo (secret/permissao/quota), explicar claramente e sugerir acao objetiva.
```

## Status Atual (Sessão 2026-03-23 - 18:25+)

### 🔴 PROBLEMA IDENTIFICADO: Login não estava sendo validado efetivamente

**Diagnóstico:**
- Scraper dizia que fazia login, mas na realidade não faziam
- Após clicar em "Entrar", apenas aguardava cegamente 5 segundos sem validação
- Navagava para página de acesso SEM usuário autenticado
- Resultado: Listagem mostrava apenas publicações legais (públicas), zero cards JORNAL
- Screenshot da página continha mensagem: "Efetue login para acessar as edições do jornal"
- Artifact listagem_cards_summary.txt confirmou: `title=VALVI, EDITAL SINDITAXI...` nenhum JORNAL

**Root cause:** Credenciais corretas, site correto, mas **validação de login ausente**

### ✅ SOLUÇÃO IMPLEMENTADA (Commit f3dd909 → f4xxxxx)

**Mudanças em `src/daily_scraper.py`:**

1. **Nova formação `_is_user_logged_in()`** (linha ~507)
	- Valida ATIVAMENTE se usuário está logado
	- Estratégia 1: Procura por elementos de usuário logado (botão Sair, menu de perfil, etc.)
	- Estratégia 2: Procura por mensagens de erro de login
	- Estratégia 3: Procura por formulário de login ainda visível → se presente, login falhou
	- Estratégia 4: Verifica URL (se ainda em `/login`, falhou)
	- Retorna: True (logado), False (falhou), None (ambíguo)

2. **Função `perform_login()` REFATORADA** (linha ~605)
	- Substituiu `time.sleep(5)` cego por loop de validação ativo
	- Aguarda até 20 segundos para validar login bem-sucedido
	- A cada iteração (a cada ~1s), chama `_is_user_logged_in()` para verificar estado
	- Se `False`: levanta Exception com diagnóstico claro ("Credenciais inválidas", "Página mudou", etc.)
	- Se `True`: sai do loop e continua (login confirmado)
	- Se `None`: continua tentando (estado ambíguo, aguarda mais)
	- Se timeout (20s): levanta Exception com diagnóstico ("Não foi possível confirmar login")

**Impacto esperado:**
- ✅ Login agora é verificado ANTES de ir para página de acesso
- ✅ Se login falhar, scraper falha fast com erro claro (não silencioso)
- ✅ Se login suceder, scraper tem usuário autenticado ao buscar PDFs
- ✅ Deve aparecer cards JORNAL na listagem (não apenas publicações legais)
- ✅ Detecção H5 exata para JORNAL agora fará sentido (haverá JORNAIs na página)

## Exemplo pronto para uso - Próximas sessões

```text
Continuar exatamente do ponto anterior no projeto Clipagem Digital.

Objetivo desta retomada:
- Validar que login agora funciona corretamente e aparece cards JORNAL na listagem
- Se necessário, debugar problema de PDF trigger ou refinar seletores

Estado atual conhecido (último commit f3dd909 incluiu validação de login):
- Função _is_user_logged_in() implementada com 4 estratégias de validação
- perform_login() agora faz loop ativo de validação (20s timeout) em vez de sleep(5)
- Se login falhar, levanta erro claro imediatamente
- Próximo run deve mostrar cards JORNAL (não só publicações legais)

Tarefas se houver falha no próximo run:
1. Verificar artifact listagem_cards_summary.txt no GitHub Actions
	- Se `title=JORNAL has_pdf=True` aparece: login OK, problema é em outro lugar
	- Se `title=VALVI, EDITAL...` (sem JORNAL): login ainda falha, debugar _is_user_logged_in
2. Se login falhar novamente:
	- Ler screenshot login_failed_after_click.png ou login_timeout_validation.png
	- Verificar se site mudou estrutura HTML
	- Possível: adicionar mais indicadores em _is_user_logged_in() ou revisar credenciais
3. Se login OK mas ainda zero PDFs encontrados:
	- H5 detection está OK, problema é XPath para PDF trigger
	- Rever last artifact card_jornal.html e pdf_icon_context.html
	- Pode ser que PDF button tenha outra estrutura (vai necessário outro inspect no Chrome)
```
2. Corrigir o workflow com o menor diff possivel.
3. Validar sintaxe e orientar teste de workflow_dispatch.
4. Reportar resultado e qualquer dependencia de permissao/token.
```

## Prompt de Retomada (Pos-Teste do Scraper)

```text
Continuar a partir do teste manual que acabei de executar no projeto Clipagem Digital.

Objetivo desta retomada:
- Avaliar o exito do scraper apos o trigger manual da app Streamlit.
- Se houve falha, diagnosticar causa raiz e aplicar correcao minima segura.

Contexto fixo:
- O botao "Verificar Edicao Agora" dispara workflow_dispatch de daily_run.yml.
- O workflow diario foi reativado (nao deve mais ficar Skipped por pausa fixa no job).

Checklist obrigatorio de avaliacao:
1. Confirmar status final do run no GitHub Actions.
2. Validar se `data/diario_sm_atual.pdf` foi gerado/atualizado.
3. Validar se `data/clipagem_hoje.json` foi gerado/atualizado.
4. Revisar logs do scraper: login, filtro, selecao do card JORNAL, download.
5. Se falhar, coletar artifacts de debug e apontar o primeiro erro causal.
6. Propor e aplicar fix minimo, depois orientar novo reteste.

Formato de entrega esperado:
- Resultado: sucesso ou falha.
- Evidencias: etapas que passaram/falharam.
- Arquivos alterados (se houver).
- Proximo passo objetivo para novo teste.
```

## Prompt de Retomada (Amanha - Estado Atual Consolidado)

```text
Continuar exatamente do ponto onde paramos no projeto Clipagem Digital e focar no reteste do scraper no GitHub Actions.

Estado atual do codigo (ja aplicado em main):
- Commit 9558fa8:
	- Fast-path no scraper para tentar clicar imediatamente no icone PDF do JORNAL mais recente apos login.
	- Workflow daily_run com fail-fast real no step do scraper (timeout retorna erro corretamente).
	- Mascaramento de secrets carregados do blob SECRETES para evitar vazamento em log.
	- Timeout padrao do scraper reduzido para 90s (SCRAPER_TIMEOUT_SECONDS).
- Commit dc128ad:
	- Restricao de clique ao gatilho de PDF (icone mdi-file-pdf / Visualizar PDF), evitando clique em card.
	- Diagnostico extra em artifacts: listagem_cards_summary.txt e jornal_not_found.*

Ultimo problema confirmado antes deste prompt:
- Em run anterior, o scraper nao entregou PDF e o analyzer quebrou com FileNotFoundError de data/diario_sm_atual.pdf.
- O erro estava mascarado por logica de exit code no workflow, ja corrigida.

Objetivo da retomada:
1. Executar novo workflow_dispatch pelo botao da app ou via Actions.
2. Verificar se o fast-path clicou no icone PDF do JORNAL rapidamente.
3. Confirmar geracao de data/diario_sm_atual.pdf e data/clipagem_hoje.json.
4. Se falhar, diagnosticar com base nos artifacts e aplicar fix minimo.

Checklist obrigatorio da analise no proximo terminal:
1. Ler status e steps do run mais recente.
2. Inspecionar logs do step "Executar Daily Scraper" (tempo total, tentativa fast-path, motivo da falha).
3. Inspecionar artifacts, especialmente:
	 - /tmp/listagem_cards_summary.txt
	 - /tmp/jornal_not_found.html
	 - /tmp/card_jornal.html
	 - /tmp/pdf_icon_context.html
4. Validar se houve timeout (exit code 124) ou falha funcional (exit != 0).
5. Se necessario, ajustar somente os seletores do icone PDF mantendo a regra: nunca clicar no card.

Criterio de sucesso:
- O scraper baixa o PDF do JORNAL dentro do timeout objetivo e o analyzer conclui gerando clipagem_hoje.json.

Formato da resposta esperada:
- Resultado do run: sucesso/falha.
- Causa raiz (1 frase).
- Correcoes aplicadas (se houver).
- Proximo passo unico e objetivo.
```
