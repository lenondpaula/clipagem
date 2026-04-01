# Instruções para Agentes de IA - Clipagem Digital

## Visão Geral do Projeto

**Clipagem Digital** é um sistema de automação de clipping do **Diário de Santa Maria**. O projeto automatiza:
1. Download diário do PDF do jornal (via Selenium + Chrome headless)
2. Análise de conteúdo com IA (Groq Mixtral 8x7B)
3. Exibição em interface web (Streamlit Cloud)
4. Commit automático dos dados gerados

**URL Login**: https://diariosm.com.br/assinante/login?redirect=/newflip  
**URL Acesso**: https://diariosm.com.br/assinante/newflip  
**Credenciais**: publicacaopmsm@gmail.com / AgysIOldtw  
**Horário de Execução**: 06:15 BRT (09:00 UTC) diariamente  
**App Streamlit**: https://clipagem-secom.streamlit.app/

## Atualização de Retomada (01/04/2026)

### ✅ Mudanças Recentes Publicadas
- **Scraper endurecido para CI/CD** (commit `b23715b`):
  - `setup_chrome_driver()` usa `--headless=new`
  - User-Agent realista de Chrome recente
  - `Page.setDownloadBehavior` via CDP para download em modo headless
- **Login Vuetify simplificado e robusto**:
  - Digitação humanizada com `ActionChains` (caractere a caractere) em usuário/senha
  - Remoção dos fallbacks de eventos reativos redundantes
  - Espera explícita para botão Entrar: clicável + `disabled` ausente/falso
  - Clique principal do botão via `ActionChains.move_to_element(...).click().perform()`
- **Download monitorado com critérios de estabilidade**:
  - PDF só é aceito quando `size > 0`
  - Tamanho deve permanecer estável por 2 segundos consecutivos
  - Abort específico para `.crdownload` travado por mais de 15s (falha de tráfego de rede)

### ✅ Correção de Workflow (Trigger da App)
- **Causa raiz do "Skipped" resolvida** (commit `6548934`):
  - Removido `if: ${{ false }}` do job principal em `.github/workflows/daily_run.yml`
- Resultado esperado: trigger via Streamlit Cloud passa a executar o job `clipagem-automation`.

### ⚠ Estado Atual dos Workflows
- `.github/workflows/daily_run.yml`: habilitado para `workflow_dispatch`.
- `.github/workflows/keep_alive.yml`: ainda com `if: ${{ false }}` (pausado provisoriamente).

### ⚠ Alinhamento de Stack para Próxima Sessão
- `src/analyzer.py` está em **Groq** (não Gemini).
- `requirements.txt` atual:
  - `webdriver-manager==4.0.1`
  - `pymupdf==1.24.9`
  - `requests==2.32.3`

---

## Status Atual do Projeto (01/04/2026)

### ✅ Componentes 100% Funcionais
- **src/daily_scraper.py**: Selenium scraper com seletores robustos, iframe search, login automático
- **src/analyzer.py**: Extração PDF (PyMuPDF) + análise Groq Mixtral 8x7B
- **src/app.py**: Interface Streamlit com layout AgroPulse-style, cards, tabela de licitações
- **.github/workflows/daily_run.yml**: GitHub Actions via workflow_dispatch, secrets loading, auto-commit
- **.github/workflows/keep_alive.yml**: Keep alive pausado provisoriamente
- **keep_alive.py**: Script Selenium Chrome headless para manter app ativa
- **data/**: Armazena `diario_sm_atual.pdf` e `clipagem_hoje.json`

### ✅ Resolução de Problemas (18/02/2026)

#### Problema 1: URL de Login Errada ✅ RESOLVIDO
- **Erro**: `https://diariosm.com.br/login` (404)
- **Correto**: `https://diariosm.com.br/assinante/login?redirect=/newflip`
- **Solução**: Atualizado secret `SECRETES` com URL completa

#### Problema 2: Filtro "Public. Legal" Não Aplicado ✅ RESOLVIDO
- **Erro**: Baixava PDF de publicações legais (VALVI) em vez de edições jornalísticas
- **Solução Implementada**:
  - Debug completo que lista todas as opções do menu dropdown
  - 7+ seletores XPath diferentes para encontrar opção "Exceto"
  - Busca manual por texto como fallback
  - Tempo de espera aumentado para 3s para menu carregar
  - Log detalhado de qual seletor funcionou

#### Problema 3: PDF Errado (VALVI) ✅ RESOLVIDO
- **Erro**: Clicava no primeiro PDF disponível (VALVI)
- **Solução Implementada**:
  - Busca específica por card/container com texto "JORNAL"
  - Usa seletor `[1]` para pegar primeira edição (mais recente)
  - Clica no ícone PDF **dentro** do card JORNAL identificado
  - Fallback: se não encontrar "JORNAL", pega primeiro PDF (comportamento anterior)

#### Problema 4: Gemini API Quota Esgotada ✅ RESOLVIDO
- **Erro**: 429 Quota exceeded (free tier limit: 0)
- **Solução**: Nova API Key gerada e configurada nos secrets
- **Modelo**: Mantido `gemini-2.0-flash`

#### Problema 5: Secrets Não Carregados ✅ RESOLVIDO
- **Erro**: `GEMINI_API_KEY` vazio no step analyzer
- **Solução**: Removido bloco `env:` redundante, usa apenas `$GITHUB_ENV` carregado do blob `SECRETES`

---

## Arquitetura e Componentes

### Estrutura de Arquivos
```
clipagem/
├── src/
│   ├── daily_scraper.py      # 779 linhas - Selenium automation
│   ├── analyzer.py            # 242 linhas - Gemini analysis
│   └── app.py                 # 369 linhas - Streamlit interface
├── data/
│   ├── diario_sm_atual.pdf   # PDF baixado diariamente
│   └── clipagem_hoje.json    # Análise gerada pelo Gemini
├── .github/
│   └── workflows/
│       ├── daily_run.yml      # Workflow principal (cron 09:00 UTC)
│       └── keep_alive.yml     # Keep alive (cron 0 */6 * * *)
├── keep_alive.py              # 82 linhas - Selenium keep alive
├── requirements.txt           # Dependências
├── .env                       # Secrets locais (não commitado)
└── .env.example               # Template de secrets
```

### Padrões de Design Implementados

#### daily_scraper.py
- **Função**: `setup_chrome_driver()` - Detecta Chrome em 5 locais, normaliza path do ChromeDriver, aplica chmod +x
- **Função**: `perform_login()` - 20+ seletores para username, 15+ para password, 12+ para botão
- **Função**: `find_element_with_fallback_any_frame()` - Busca em main document + iframes, mantém contexto
- **Função**: `set_publication_filter()` - Aplica filtro "Exceto" em "Public. Legal" com debug completo
- **Função**: `access_and_download_pdf()` - Busca card JORNAL específico, clica no PDF dentro dele
- **Função**: `wait_for_download_completion()` - Monitora pasta data/ por .pdf ou .crdownload
- **Padrão**: Screenshot + HTML dump em `/tmp/` quando falha login
- **Logging**: Prefixos `[ENV]`, `[CHROME]`, `[LOGIN]`, `[FILTRO]`, `[PDF]`, `[DOWNLOAD]`

#### analyzer.py
- **Função**: `extract_pdf_text()` - PyMuPDF extrai texto página por página
- **Função**: `configure_gemini()` - Configura API key, valida modelo gemini-2.0-flash
- **Função**: `analyze_with_gemini()` - Envia prompt + texto para Gemini, recebe JSON
- **Função**: `parse_gemini_response()` - Extrai JSON da resposta (remove markdown)
- **Função**: `save_clipagem_json()` - Salva em `data/clipagem_hoje.json`
- **Prompt**: Critérios de inclusão (PMSM, Câmara, Segurança, Boate Kiss, Licitações)

#### app.py
- **Função**: `load_clipagem()` - Cached, carrega `clipagem_hoje.json`
- **Função**: `trigger_github_action()` - Dispatch manual via GitHub API (requer GH_TOKEN)
- **Layout**: Header com título + subtítulo, cards com resumo, tabela de licitações, footer com contatos
- **Sidebar**: Botões "Recarregar Dados" e "🔄 Verificar Edição Agora"
- **CSS**: Tema light (branco/cinza), estilo AgroPulse

#### keep_alive.py
- **Método**: Apenas Selenium Chrome headless (sem HTTP GET)
- **Função**: `build_driver()` - Chrome com --headless, --no-sandbox
- **Função**: `run()` - Acessa target URL, aguarda 10s, salva screenshot com timestamp
- **Execução**: A cada 6 horas (00:00, 06:00, 12:00, 18:00 UTC)

---

## Convenções de Código

### Stack Tecnológico
- **Python**: 3.11.14 (Actions), 3.12.3 (local dev container)
- **Selenium**: 4.40.0
- **Google Chrome**: 144.0.7559.132 (headless)
- **webdriver-manager**: 4.0.2
- **Google Gemini**: 2.0 Flash via `google-generativeai` 0.8.6
- **Streamlit**: 1.53.1
- **PyMuPDF**: 1.26.7
- **python-dotenv**: 1.2.1
- **requests**: 2.32.5

### Nomeação e Estrutura
- **Funções**: snake_case com docstrings descritivas
- **Variáveis de ambiente**: `DIARIO_LOGIN_URL`, `DIARIO_ACCESS_URL`, `DIARIO_USER`, `DIARIO_PASS`, `GEMINI_API_KEY`, `GOOGLE_API_KEY`
- **Secrets no Actions**: Blob `SECRETES` com linhas `KEY=VALUE` (carregado para `$GITHUB_ENV`)
- **Arquivos de dados**: `diario_sm_atual.pdf`, `clipagem_hoje.json`
- **Prefixos de log**: `[ENV]`, `[CHROME]`, `[LOGIN]`, `[FILTRO]`, `[PDF]`, `[DOWNLOAD]`, `[GEMINI]`, `[KEEP_ALIVE]`

### Patterns de Implementação
- **Seletores Robustos**: Listas com 7-20 fallbacks XPath para cada elemento
- **WebDriverWait**: Timeout mínimo 5s, padrão 15-20s
- **Chrome Options**: `--headless`, `--no-sandbox`, `--disable-dev-shm-usage`, `--disable-gpu`, `--window-size=1920,1080`
- **Download Dir**: Configurado via `prefs` do Chrome para `data/`
- **Tratamento de Erros**: Screenshot PNG + HTML source em `/tmp/` antes de raise
- **Iframe Handling**: Switch to default → busca main → itera iframes → switch back

---

## Workflows de Desenvolvimento

### Execução Local
```bash
# Download do PDF
cd /workspaces/clipagem
python src/daily_scraper.py

# Análise com Gemini (requer GEMINI_API_KEY em .env)
python src/analyzer.py

# Interface web (porta 8501)
streamlit run src/app.py --server.port 8501

# Keep alive (opcional)
python keep_alive.py
```

### Estrutura de Dados

**clipagem_hoje.json**:
```json
{
  "data_clipping": "18 de Fevereiro de 2026",
  "resumo_gemini": "Resumo executivo das principais notícias...",
  "noticias": [
    {
      "pagina": 3,
      "titulo": "Prefeitura anuncia obras",
      "resumo_120_chars": "Secretaria de Obras inicia revitalização...",
      "relevancia": "alta"
    }
  ]
}
```

### Diagnóstico e Debug
- **Chrome Binary**: `/usr/bin/google-chrome` (Actions), detectado automaticamente em 5 locais
- **Screenshot de erro**: `/tmp/login_error.png`
- **HTML source**: `/tmp/login_error.html`
- **Screenshot filtro**: `/tmp/filtro_debug.png`
- **Logs estruturados**: Prefixos identificam etapa claramente
- **PDF baixado**: `/workspaces/clipagem/data/diario_sm_atual.pdf`
- **GitHub Artifacts**: Arquivos `/tmp/login_error.*` salvos como `login-debug-<run_id>` (retention: 7 dias)

### Secrets Management

**No GitHub Actions (secret `SECRETES`)**:
```
DIARIO_LOGIN_URL=https://diariosm.com.br/assinante/login?redirect=/newflip
DIARIO_ACCESS_URL=https://diariosm.com.br/assinante/newflip
DIARIO_USER=publicacaopmsm@gmail.com
DIARIO_PASS=AgysIOldtw
GEMINI_API_KEY=AIzaSyA...
GOOGLE_API_KEY=AIzaSyA...
```

**No Streamlit Cloud (opcional, para botão dispatch)**:
```toml
GH_TOKEN = "ghp_..."
```

**No .env local**:
```env
DIARIO_LOGIN_URL=https://diariosm.com.br/assinante/login?redirect=/newflip
DIARIO_ACCESS_URL=https://diariosm.com.br/assinante/newflip
DIARIO_USER=publicacaopmsm@gmail.com
DIARIO_PASS=AgysIOldtw
GOOGLE_API_KEY=AIzaSyA...
GEMINI_API_KEY=AIzaSyA...
```

---

## Workflows GitHub Actions

### daily_run.yml
- **Trigger**: Cron `0 9 * * *` (09:00 UTC = 06:15 BRT)
- **Trigger**: workflow_dispatch (manual)
- **Steps**:
  1. Checkout código
  2. Setup Python 3.11 com cache pip
  3. Instalar dependências (requirements.txt)
  4. Instalar Google Chrome (apt-get ou wget .deb)
  5. **Carregar secrets do arquivo**: Parse blob `SECRETES` → `$GITHUB_ENV`
  6. **Executar Daily Scraper**: `python src/daily_scraper.py`
  7. **Verificar PDF**: Valida `data/diario_sm_atual.pdf` existe
  8. **Executar Gemini Analyzer**: `python src/analyzer.py` (usa vars do `$GITHUB_ENV`)
  9. **Verificar JSON**: Valida `data/clipagem_hoje.json` existe
  10. **Auto-Commit**: Git add data/, commit com mensagem template, push
  11. **Notificação de Sucesso**: Mostra arquivos gerados
  12. **Upload de Debug** (if failure): Upload `/tmp/login_error.*` como artifact
  13. **Notificação de Erro** (if failure): Mostra URL do artifact

### keep_alive.yml
- **Trigger**: Cron `0 */6 * * *` (a cada 6 horas: 00:00, 06:00, 12:00, 18:00 UTC)
- **Trigger**: workflow_dispatch (manual)
- **Steps**:
  1. Checkout código
  2. Setup Python 3.11 com cache pip
  3. Instalar dependências (selenium, webdriver-manager)
  4. Instalar Google Chrome
  5. **Rodar keep alive (Selenium)**: `python keep_alive.py`
- **Env vars**:
  - `KEEP_ALIVE_URL=https://clipagem-secom.streamlit.app/`
  - `KEEP_ALIVE_WAIT_SECONDS=10`
  - `KEEP_ALIVE_SCREENSHOT=keep_alive_screenshot.png`

---

## Problemas Conhecidos e Soluções

### 1. API Gemini Quota Exceeded
**Sintoma**: Erro 429 "You exceeded your current quota"  
**Causa**: Free tier tem limite de requests/tokens por dia/minuto  
**Solução**: Gerar nova API Key em https://makersuite.google.com/app/apikey

### 2. Seletores Dinâmicos (Vuetify)
**Sintoma**: IDs mudam entre sessões (`input-v-98` → `input-v-15`)  
**Causa**: Framework Vuetify gera IDs aleatórios  
**Solução**: Usar múltiplos seletores (aria-label, placeholder, text contains, class)

### 3. ChromeDriver Path (THIRD_PARTY_NOTICES)
**Sintoma**: webdriver-manager retorna path para arquivo de licença  
**Causa**: Bug conhecido do webdriver-manager  
**Solução**: Normalizar path com `driver_path.with_name("chromedriver")` + chmod +x

### 4. Iframe Hidden Forms
**Sintoma**: Formulário de login não encontrado apesar da página carregar  
**Causa**: Form pode estar dentro de iframe  
**Solução**: Funções `find_element_with_fallback_any_frame()` iteram por todos iframes

### 5. Download Não Completa
**Sintoma**: Timeout aguardando PDF  
**Causa**: Download lento ou rede instável  
**Solução**: Monitorar arquivos `.crdownload`, timeout de 30s, espera ativa

---

## Próximos Passos (Se Necessário)

### Melhorias Potenciais
1. **Retry Logic**: Adicionar retry com backoff exponencial em caso de falha temporária
2. **Notificações**: Enviar email/Telegram em caso de sucesso/falha do workflow
3. **Multi-fonte**: Expandir para outros jornais (Zero Hora, Correio do Povo)
4. **Dashboard Avançado**: Gráficos de tendências, histórico de notícias
5. **Cache Inteligente**: Evitar re-processar mesmo PDF se já baixado hoje
6. **Testes Automatizados**: Unit tests para parser, integration tests para scraper

### Monitoramento
- **GitHub Actions**: Verificar status diário em https://github.com/lenondpaula/clipagem/actions
- **Streamlit App**: Acessar https://clipagem-secom.streamlit.app/ para validar dados atualizados
- **Logs**: Revisar logs dos workflows em caso de falha
- **Artifacts**: Baixar `/tmp/login_error.*` para debug visual

---

## Referências

- **Selenium Docs**: https://www.selenium.dev/documentation/
- **Gemini API Docs**: https://ai.google.dev/gemini-api/docs
- **Streamlit Docs**: https://docs.streamlit.io/
- **GitHub Actions**: https://docs.github.com/en/actions
- **PyMuPDF Docs**: https://pymupdf.readthedocs.io/

---

**Última Atualização**: 01 de Abril de 2026  
**Status**: ✅ Sistema em Produção - Funcionando 100%  
**Próxima Revisão**: Conforme necessidade de novas features ou mudanças no site fonte
