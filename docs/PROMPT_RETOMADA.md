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

## Exemplo pronto para uso

```text
Continuar exatamente do ponto anterior no projeto Clipagem Digital.

Objetivo desta retomada:
- Corrigir o trigger manual da aplicacao Streamlit para acionar o workflow diario sem status Skipped.

Estado atual conhecido:
- O botao da app envia dispatch para daily_run.yml com ref main.
- No GitHub Actions, o run abre e termina como Skipped em poucos segundos.
- Preciso conseguir testar fim a fim pelo botao da app.

Tarefas:
1. Revisar o .github/workflows/daily_run.yml e identificar condicoes de skip.
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
