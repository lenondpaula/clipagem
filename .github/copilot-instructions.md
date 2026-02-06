# Instruções para Agentes de IA - Clipagem Chatbot

## Visão Geral do Projeto

**Clipagem** é um sistema de automação de clipping do **Diário de Santa Maria**. O projeto automatiza:
1. Download diário do PDF do jornal (via Selenium)
2. Análise de conteúdo com IA (Google Gemini)
3. Exibição em interface web (Streamlit)

**URL Alvo**: https://diariosm.com.br/assinante/newflip  
**Credenciais**: publicacaopmsm@gmail.com / AgysIOldtw  
**Horário de Execução**: 06:15 BRT (09:00 UTC) de segunda a sábado

## Status Atual do Projeto (04/02/2026)

### ✅ Componentes Funcionais
- **src/daily_scraper.py** (521 linhas): Selenium scraper com 14+ seletores robustos
- **src/analyzer.py** (230 linhas): Extração PDF + análise Gemini 2.0 Flash
- **app.py** (349 linhas): Interface Streamlit com tema light forçado
- **.github/workflows/daily_run.yml**: GitHub Actions com cron schedule
- **data/**: Armazena PDF e JSON de clipping

### ⚠️ Problema Atual - EM ANDAMENTO
**Filtro "Public. Legal" não está sendo aplicado**

O scraper está baixando PDF de publicações legais (VALVI Companhia) em vez das edições jornalísticas.

**Solução em desenvolvimento:**
- Após login e navegação para `/newflip`, selecionar "Exceto" no dropdown "Public. Legal"
- Elemento identificado: `<input role="combobox" id="input-v-98" ...>`
- Função `set_publication_filter()` precisa ser implementada/ajustada
- Edição alvo confirmada: **Edição Nº 7328 - Data: 04/02/2026**

### 🔧 Últimas Ações Realizadas
1. Scraper executado com sucesso - login OK, download OK
2. PDF baixado incorretamente (VALVI em vez de Diário SM)
3. Identificado filtro necessário através de inspeção manual
4. Tentativas de implementação do filtro iniciadas (combobox não encontrado)

## Arquitetura e Componentes

### Estrutura Real
- `src/daily_scraper.py`: Selenium + Chrome headless para login e download de PDF
- `src/analyzer.py`: PyMuPDF para extração + Gemini para análise de conteúdo
- `app.py`: Streamlit interface com visualização de cards
- `data/`: PDF atual e JSON com análise do dia
- `.streamlit/config.toml`: Configuração de tema light
- `.github/workflows/daily_run.yml`: Automação via GitHub Actions

### Padrões de Design Implementados
- **Seletores com Fallback**: 14+ XPath para username, 10+ para password, 11+ para botão
- **Chrome Binary Detection**: Detecta Chrome em 5 locais diferentes (multi-plataforma)
- **Limpeza Automática**: Remove PDFs antigos antes de baixar novo
- **Screenshot em Erro**: Salva em `/tmp/login_error.png` para debug
- **Logging Estruturado**: Prefixos [ENV], [LOGIN], [PDF], [DOWNLOAD], [GEMINI]

## Convenções de Código

### Stack Tecnológico
- **Python 3.12.1**: Linguagem principal
- **Selenium 4.40.0**: Automação web com Chrome 144.0.7559.132
- **Google Gemini 2.0 Flash**: Análise de conteúdo (via `google-generativeai` - deprecated)
- **Streamlit 1.53.1**: Interface web
- **PyMuPDF (fitz) 1.24.9**: Extração de texto de PDF
- **python-dotenv 1.0.0**: Gerenciamento de variáveis de ambiente

### Nomeação e Estrutura
- Prefixos de log: `[ENV]`, `[CHROME]`, `[LOGIN]`, `[PDF]`, `[DOWNLOAD]`, `[GEMINI]`
- Funções em snake_case com docstrings descritivas
- Arquivos de dados: `diario_sm_atual.pdf`, `clipagem_hoje.json`
- Variáveis de ambiente: `DIARIO_USER`, `DIARIO_PASS`, `GEMINI_API_KEY`

### Patterns de Implementação
- **Seletores Robustos**: Lista de fallbacks com try/except para elementos dinâmicos
- **WebDriverWait**: Timeout padrão de 20s para elementos, 120s para download
- **Chrome Options**: `--headless`, `--no-sandbox`, `--disable-dev-shm-usage`
- **Download Dir**: Configurado via `prefs` do Chrome para `data/`
- **Tratamento de Erros**: Screenshot + mensagem estruturada antes de raise

## Workflows de Desenvolvimento

### Execução dos Scripts
```bash
# Download do PDF
cd /workspaces/clipagem
python src/daily_scraper.py

# Análise com Gemini (requer GEMINI_API_KEY em .env)
python src/analyzer.py

# Interface web (porta 8501)
streamlit run app.py --server.port 8501
```

### Estrutura de Dados

**clipagem_hoje.json:**
```json
{
  "data_clipping": "04 de Fevereiro de 2026",
  "noticias": [
    {
      "pagina": 1,
      "titulo": "Título da notícia",
      "resumo_120_chars": "Resumo em até 120 caracteres",
      "relevancia": "alta|media|baixa"
    }
  ]
}
```

### Diagnóstico e Debug
- **Chrome**: Binário em `/usr/bin/google-chrome`
- **Screenshot de erro**: `/tmp/login_error.png`
- **Logs estruturados**: Prefixos identificam etapa do processo
- **PDF baixado**: `/workspaces/clipagem/data/diario_sm_atual.pdf`

### Problemas Conhecidos
1. **API Gemini**: Cota free tier pode esgotar (429 error)
2. **Filtro "Public. Legal"**: Não aplicado, baixa PDF errado
3. **Seletores dinâmicos**: IDs mudam (input-v-98, input-v-44, etc)

## Próximos Passos (Onde Paramos)

### 🎯 Tarefa Atual: Implementar Filtro "Public. Legal"

**Problema:** O scraper baixa PDF de publicações legais (VALVI) em vez das edições jornalísticas.

**Solução Necessária:**
1. Após login, navegar para `/newflip`
2. Localizar dropdown "Public. Legal" 
3. Selecionar opção "Exceto"
4. Aguardar atualização da lista
5. Baixar PDF da edição jornalística

**Elemento Identificado:**
```html
<input size="1" role="combobox" type="text" 
       aria-labelledby="input-v-98-label" 
       id="input-v-98" 
       aria-describedby="input-v-98-messages" 
       aria-expanded="false" 
       aria-controls="menu-v-96" 
       value="">
```

**Status:** Função `set_publication_filter()` criada mas combobox não localizado nos testes.

**Edição Alvo Confirmada:**
- JORNAL
- Edição Nº 7328
- Data Edição: 04/02/2026

### 🔍 Próximas Ações Sugeridas
1. Adicionar screenshot da página `/newflip` para debug visual
2. Tentar seletores alternativos para o dropdown (aria-label, texto "Public. Legal")
3. Verificar se filtro aparece após scroll ou aguardar carregamento
4. Implementar clique no dropdown + seleção da opção "Exceto"
5. Validar que PDF baixado é da edição jornalística (não VALVI)

---

## Integração com Fontes de Mídia

### Considerações Principais
- Suportar múltiplas fontes (notícias, redes sociais, blogs, etc)
- Respeitar rate limits e políticas de termos de serviço
- Implementar retry logic com backoff exponencial
- Cache de conteúdo quando aplicável

## Dependências Críticas

- [A documentar conforme tecnologias forem definidas]

## Referências para Padrões

- Revisar commits iniciais para decisões arquiteturais
- Documentar novas decisões de arquitetura em ADRs (Architecture Decision Records)

---

**Nota**: Este arquivo será expandido conforme o projeto evolui. Agentes devem atualizar esta documentação quando implementarem padrões ou convenções não documentadas aqui.
