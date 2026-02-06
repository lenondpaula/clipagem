# 🚀 Guia de Setup - Clipagem Digital

## Instalação Rápida

### 1. Clonar Repositório
```bash
git clone https://github.com/lenondpaula/clipagem.git
cd clipagem
```

### 2. Criar Ambiente Virtual
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# ou
venv\Scripts\activate     # Windows
```

### 3. Instalar Dependências
```bash
pip install -r requirements.txt
```

### 4. Configurar Variáveis de Ambiente

Copie o arquivo de exemplo e preencha com suas credenciais:
```bash
cp .env.example .env
```

Edite o arquivo `.env` e preencha:
```env
DIARIO_LOGIN_URL=https://seu_url_de_login
DIARIO_ACCESS_URL=https://seu_url_de_acesso
DIARIO_USER=seu_usuario
DIARIO_PASS=sua_senha
GEMINI_API_KEY=sua_chave_api_google
```

### 5. Testar Scraper
```bash
python src/daily_scraper.py
```

### 6. Testar Análise
```bash
python src/analyzer.py
```

### 7. Executar Interface
```bash
streamlit run app.py
```

---

## 📁 Estrutura de Diretórios

```
clipagem/
├── .env                    # Credenciais (não versionado)
├── .env.example           # Exemplo de .env
├── .gitignore             # Ignorar arquivos sensíveis
├── requirements.txt       # Dependências Python
├── README.md
├── app.py                 # Interface Streamlit
├── src/
│   ├── daily_scraper.py   # Download do PDF
│   └── analyzer.py        # Análise com Gemini
├── data/                  # Arquivos gerados (não versionado)
│   ├── diario_sm_atual.pdf
│   └── clipagem_hoje.json
├── docs/
│   └── LOGIN_SELECTORS.md # Documentação de seletores
└── .github/
    ├── copilot-instructions.md
    └── workflows/
        └── daily_run.yml  # Automação GitHub Actions
```

---

## 🔐 Variáveis de Ambiente

### Diário Oficial
| Variável | Descrição |
|----------|-----------|
| `DIARIO_LOGIN_URL` | URL da página de login |
| `DIARIO_ACCESS_URL` | URL onde o PDF está acessível |
| `DIARIO_USER` | Usuário/Email de login |
| `DIARIO_PASS` | Senha de login |

### Google Gemini
| Variável | Descrição |
|----------|-----------|
| `GEMINI_API_KEY` | Chave API do Google Gemini |

### Obtendo as Credenciais

#### 1. **DIARIO_LOGIN_URL** e **DIARIO_ACCESS_URL**
- Visite o site do Diário Oficial
- Copie a URL da página de login
- Copie a URL onde o PDF fica disponível para download

#### 2. **DIARIO_USER** e **DIARIO_PASS**
- Use suas credenciais de acesso ao sistema

#### 3. **GEMINI_API_KEY**
- Visite: https://aistudio.google.com/app/apikey
- Crie uma nova chave de API
- Copie e guarde em local seguro

---

## ⚙️ Configuração do GitHub Actions (Automação)

Se quiser usar o workflow automático no GitHub Actions, configure os secrets:

1. Vá para: **Settings → Secrets and variables → Actions**
2. Adicione os seguintes secrets:
   - `DIARIO_LOGIN_URL`
   - `DIARIO_ACCESS_URL`
   - `DIARIO_USER`
   - `DIARIO_PASS`
   - `GEMINI_API_KEY`

O workflow executará automaticamente todos os dias às 06:15 (Brasília).

---

## 🧪 Testando Localmente

### Testar apenas download (daily_scraper.py)
```bash
export DIARIO_LOGIN_URL="sua_url"
export DIARIO_ACCESS_URL="sua_url"
export DIARIO_USER="seu_usuario"
export DIARIO_PASS="sua_senha"

python src/daily_scraper.py
```

### Testar análise (analyzer.py)
```bash
export GEMINI_API_KEY="sua_chave"

python src/analyzer.py
```

### Testar interface (app.py)
```bash
streamlit run app.py
```

---

## 🐛 Troubleshooting

### Chrome não encontrado
```
[CHROME] ERRO ao configurar ChromeDriver
```
**Solução**: Instale Google Chrome:
```bash
# Linux
sudo apt-get install google-chrome-stable

# macOS
brew install google-chrome

# Windows
# Baixe de https://www.google.com/chrome/
```

### Módulo não encontrado
```
ModuleNotFoundError: No module named 'dotenv'
```
**Solução**: Instale as dependências:
```bash
pip install -r requirements.txt
```

### Credenciais não funcionam
**Verificar**:
1. Arquivo `.env` existe na raiz do projeto?
2. Variáveis estão preenchidas corretamente?
3. Senha não contém caracteres especiais que precisam escape?

### Login falha
O script tira screenshot automático em `/tmp/login_error.png`
- Verifique se o seletor de placeholder mudou
- Adicione novo seletor em `src/daily_scraper.py` conforme docs

---

## 📊 Fluxo de Execução

```
1. daily_scraper.py
   ├── Limpeza de PDFs antigos
   ├── Download do Diário
   └── Salva em data/diario_sm_atual.pdf

2. analyzer.py
   ├── Extrai texto do PDF
   ├── Envia para Google Gemini
   └── Salva em data/clipagem_hoje.json

3. app.py
   ├── Carrega JSON
   ├── Exibe interface
   └── Permite compartilhar no WhatsApp
```

---

## 📞 Suporte

- **Issues**: https://github.com/lenondpaula/clipagem/issues
- **Documentação**: Veja `docs/`
- **Desenvolvedor**: Lenon de Paula

---

**Última atualização**: Fevereiro 2026
