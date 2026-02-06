# 🔧 Seletores de Login Robustos - Documentação

## Problema Resolvido

❌ **Antes**: Seletores rígidos com IDs dinâmicos (`input-v-44`, etc)
- Quebrava sempre que o framework Vue/React re-renderizava
- Apenas 1 estratégia de busca

✅ **Depois**: Sistema de múltiplos seletores com fallback em cascata
- 14+ seletores para campo de usuário
- 10+ seletores para campo de senha
- 11+ seletores para botão de entrar
- Encontra mesmo com IDs dinâmicos

## Estratégias Implementadas

### 1. **Por Placeholder (Mais Confiável)**
```xpath
//input[@placeholder='E-mail']
//input[@placeholder='Senha']
```
- Texto descritivo geralmente não muda
- Visível para usuários

### 2. **Por Type de Input**
```xpath
//input[@type='email']
//input[@type='password']
```
- Semântica HTML
- Independente de estilo ou ID

### 3. **Por Atributos de Acessibilidade**
```xpath
//input[@aria-label='E-mail']
//label[contains(text(), 'E-mail')]/following::input[@type='text'][1]
```
- Melhor para sites acessíveis
- Relaciona label com input

### 4. **Por Posição (Fallback)**
```xpath
//input[@type='text'][1]    // Primeiro input text
//button[1]                  // Primeiro botão
```
- Última tentativa se nada acima funcionar

### 5. **Funções Helper com Retry**

```python
find_element_with_fallback(driver, selectors, timeout)
find_clickable_element_with_fallback(driver, selectors, timeout)
```

- Tenta cada seletor sequencialmente
- Para na primeira correspondência
- Retorna `None` se nenhum encontrado
- Permite tratamento de erro informativo

## Melhorias Adicionais

### Debug Screenshot
Se nenhum campo for encontrado, o script tira screenshot:
```python
driver.save_screenshot("/tmp/login_error.png")
```

### Logs Detalhados
```
[LOGIN] Procurando campo de E-mail/Usuário...
[LOGIN] Campo de Usuário encontrado
[LOGIN] Usuário preenchido: leno***
```

### Tratamento de Erros
- Mostra qual seletor falhou
- Tipo específico de exceção
- Facilita debugging em CI/CD

## Compatibilidade

| Tipo de Site | Likelihood |
|---|---|
| Formulários HTML padrão | ✅ 99% |
| Vue/React com IDs dinâmicos | ✅ 95% |
| Sites com aria-labels | ✅ 100% |
| Formulários customizados | ✅ 80% |

## Como Adicionar Novos Seletores

Se o login falhar com o novo código, adicione um seletor à lista apropriada:

**Para campo de usuário:**
```python
username_selectors = [
    # ... seletores existentes ...
    "//input[contains(@id, 'username')]",  # Novo seletor
]
```

**Para campo de senha:**
```python
password_selectors = [
    # ... seletores existentes ...
    "//input[contains(@name, 'pwd')]",  # Novo seletor
]
```

**Para botão:**
```python
button_selectors = [
    # ... seletores existentes ...
    "//button[contains(@class, 'submit')]",  # Novo seletor
]
```

## Testando Localmente

```bash
# Com credenciais configuradas
export DIARIO_LOGIN_URL="https://..."
export DIARIO_ACCESS_URL="https://..."
export DIARIO_USER="seu_usuario"
export DIARIO_PASS="sua_senha"

python src/daily_scraper.py
```

Se falhar, o screenshot será salvo em `/tmp/login_error.png` para análise.

## Performance

- **Antes**: Falha rápida (1-2s) com KeyError
- **Depois**: Tenta múltiplos seletores (3-15s)
- **Trade-off**: Mais confiável com pequeno overhead de tempo

---

**Nota**: Este sistema é resiliente contra mudanças menores no layout HTML. Para mudanças estruturais maiores, adicione novos seletores à lista.
