# 📰 Clipagem Digital - Diário de Santa Maria

Sistema automatizado de clipping diário do **Diário de Santa Maria**, com análise inteligente de conteúdo e interface web moderna.

[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=flat&logo=streamlit&logoColor=white)](https://clipagem-secom.streamlit.app/)
[![Python](https://img.shields.io/badge/Python-3.11-blue?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![Selenium](https://img.shields.io/badge/Selenium-4.40.0-green?style=flat&logo=selenium&logoColor=white)](https://www.selenium.dev/)
[![Groq](https://img.shields.io/badge/Groq-Mixtral_8x7B-orange?style=flat&logo=ai&logoColor=white)](https://groq.com/)

🔗 **App em Produção**: https://clipagem-secom.streamlit.app/

---

## 📋 Sobre o Projeto

**Clipagem Digital** automatiza o processo de monitoramento diário do jornal **Diário de Santa Maria**, extraindo notícias relevantes para a **Prefeitura Municipal de Santa Maria (PMSM)** através de:

- 🤖 **Download Automatizado**: Selenium baixa PDF diariamente (06:15 BRT)
- 🧠 **Análise com IA**: Groq Mixtral 8x7B identifica notícias relevantes
- 📊 **Dashboard Web**: Interface Streamlit com cards, resumos e licitações
- ⏰ **Execução Programada**: GitHub Actions executa automaticamente todos os dias

---

## 🚀 Funcionalidades

### ✅ Automação Completa
- Login automático no portal do Diário SM
- Filtro inteligente: ignora publicações legais (VALVI), seleciona apenas edições jornalísticas
- Seleção automática da **edição mais recente**
- Download e renomeação padronizada do PDF

### 🧠 Análise Inteligente
- Extração de texto do PDF via PyMuPDF
- Análise com Groq Mixtral 8x7B
- Identificação de notícias relevantes:
  - Prefeitura de Santa Maria
  - Câmara de Vereadores
  - Segurança Pública regional
  - Infraestrutura (UFSM, rodovias)
  - Caso Boate Kiss
  - Licitações e contratos

### 📊 Interface Web
- Dashboard responsivo em Streamlit
- Cards com resumo executivo por IA
- Tabela de licitações destacada
- Botão de download do PDF original
- Botão manual para nova verificação
- Atualização automática diária

### ⏰ Keep Alive
- Selenium acessa a app a cada 6 horas
- Evita hibernação do Streamlit Cloud
- Screenshot de cada acesso para logs

---

## 🏗️ Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                    GitHub Actions (Cron)                     │
│                      Executa 06:15 BRT                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              src/daily_scraper.py (Selenium)                 │
│  • Login no portal Diário SM                                 │
│  • Filtro "Public. Legal" = "Exceto"                        │
│  • Seleção de edição JORNAL (não VALVI)                    │
│  • Download de diario_sm_atual.pdf                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│             src/analyzer.py (Groq Mixtral 8x7B)              │
│  • Extração de texto do PDF (PyMuPDF)                       │
│  • Análise com Groq API                                     │
│  • Geração de clipagem_hoje.json                            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              src/app.py (Streamlit Cloud)                    │
│  • Dashboard com cards e resumo                              │
│  • Tabela de licitações                                      │
│  • Download do PDF original                                  │
│  • Atualização em tempo real                                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 📁 Estrutura do Projeto

```
clipagem/
├── src/
│   ├── daily_scraper.py      # Selenium: login + download PDF
│   ├── analyzer.py            # Groq: análise de conteúdo
│   └── app.py                 # Streamlit: interface web
├── data/
│   ├── diario_sm_atual.pdf   # PDF baixado daily_scraper
│   └── clipagem_hoje.json    # JSON gerado pelo analyzer
├── .github/
│   └── workflows/
│       ├── daily_run.yml      # Execução diária 06:15 BRT
│       └── keep_alive.yml     # Keep alive a cada 6h
├── keep_alive.py              # Script Selenium para manter app ativa
├── requirements.txt           # Dependências Python
└── README.md                  # Este arquivo
```

---

## 🛠️ Tecnologias

| Componente | Tecnologia | Versão |
|------------|------------|--------|
| **Linguagem** | Python | 3.11+ |
| **Web Scraping** | Selenium | 4.40.0 |
| **Browser** | Google Chrome | Headless |
| **Análise IA** | Groq | Mixtral 8x7B |
| **PDF Processing** | PyMuPDF (fitz) | 1.24.9 |
| **Interface Web** | Streamlit | 1.53.1 |
| **Automação** | GitHub Actions | - |
| **Deploy** | Streamlit Cloud | - |

---

## ⚙️ Configuração

### Variáveis de Ambiente

Configure os seguintes secrets no GitHub Actions (secret `SECRETES`):

```env
DIARIO_LOGIN_URL=https://diariosm.com.br/assinante/login?redirect=/newflip
DIARIO_ACCESS_URL=https://diariosm.com.br/assinante/newflip
DIARIO_USER=seu_email@exemplo.com
DIARIO_PASS=sua_senha
GROQ_API_KEY=sua_chave_api_groq
```

### Secrets do Streamlit Cloud

Configure no Streamlit Cloud (opcional, apenas para botão de dispatch manual):

```toml
GH_TOKEN = "seu_github_personal_access_token"
```

---

## 📅 Execução Automática

### Daily Run (Clipagem)
- **Horário**: 06:15 BRT (09:00 UTC)
- **Frequência**: Segunda a Sábado
- **Workflow**: `.github/workflows/daily_run.yml`
- **Trigger Manual**: Via Streamlit ou GitHub Actions

### Keep Alive
- **Horário**: A cada 6 horas (00:00, 06:00, 12:00, 18:00 UTC)
- **Método**: Selenium Chrome headless
- **Workflow**: `.github/workflows/keep_alive.yml`

---

## 🧪 Execução Local

### Pré-requisitos
```bash
# Python 3.11+
python --version

# Google Chrome instalado
google-chrome --version
```

### Instalação
```bash
# Clone o repositório
git clone https://github.com/lenondpaula/clipagem.git
cd clipagem

# Crie ambiente virtual
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Instale dependências
pip install -r requirements.txt

# Configure .env
cp .env.example .env
# Edite .env com suas credenciais
```

### Execução
```bash
# 1. Download do PDF
python src/daily_scraper.py

# 2. Análise com Groq
python src/analyzer.py

# 3. Interface Streamlit
streamlit run src/app.py
```

---

## 📊 Saída de Dados

### PDF: `data/diario_sm_atual.pdf`
Arquivo PDF da edição mais recente do jornal.

### JSON: `data/clipagem_hoje.json`
```json
{
  "data_clipping": "18 de Fevereiro de 2026",
  "resumo_gemini": "Resumo executivo gerado por IA...",
  "noticias": [
    {
      "pagina": 3,
      "titulo": "Prefeitura anuncia obras na Avenida Medianeira",
      "resumo_120_chars": "Secretaria de Obras inicia revitalização...",
      "relevancia": "alta"
    }
  ]
}
```

---

## 🔧 Debug e Logs

### Logs Estruturados
Todos os scripts usam prefixos para facilitar diagnóstico:
- `[ENV]` - Carregamento de variáveis
- `[CHROME]` - Setup do ChromeDriver
- `[LOGIN]` - Processo de autenticação
- `[FILTRO]` - Aplicação de filtros
- `[PDF]` - Download do PDF
- `[GROQ]` - Análise com IA

### Artifacts de Debug
Em caso de erro, o workflow salva:
- `/tmp/login_error.png` - Screenshot da página
- `/tmp/login_error.html` - HTML source da página
- `/tmp/filtro_debug.png` - Screenshot do filtro

Acesse em: **GitHub Actions > Run > Artifacts**

---

## 🤝 Contribuindo

Contribuições são bem-vindas! Para mudanças maiores:

1. Fork o projeto
2. Crie uma branch (`git checkout -b feature/MinhaFeature`)
3. Commit suas mudanças (`git commit -m 'Adiciona MinhaFeature'`)
4. Push para a branch (`git push origin feature/MinhaFeature`)
5. Abra um Pull Request

---

## 📝 Licença

Este projeto é de uso interno da **Prefeitura Municipal de Santa Maria**.

---

## 👥 Contato

**SECOM - Secretaria de Comunicação**
- 📧 Email: secom@santamaria.rs.gov.br
- 🌐 Site: https://www.santamaria.rs.gov.br

---

## 🎯 Status do Projeto

✅ **Em Produção** - Sistema funcionando diariamente desde fevereiro de 2026

### Últimas Atualizações (20/02/2026)
- ✅ **Migração para Groq API** - Substituição do Gemini por Mixtral 8x7B
- ✅ **Correção crítica keep-alive** - Bug THIRD_PARTY_NOTICES resolvido
- ✅ **Filtragem VALVI/JORNAL aprimorada** - Detecção robusta de publicações
- ✅ **Workflows otimizados** - Timeouts e verificações adicionais
- ✅ **Validação pós-download** - Remove automaticamente arquivos inválidos
- ✅ **User-agent real** - Simulação de navegador legítimo no keep-alive
