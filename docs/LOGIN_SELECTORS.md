# Seletores de Login - Referencia Playwright

O login em `src/daily_scraper.py` usa lista de seletores XPath com prioridade para elementos visiveis.

## Usuario

- `//label[contains(., 'Entre com seu E-mail ou CPF/CNPJ')]/ancestor::div[contains(@class, 'v-field')][1]//input[contains(@class, 'v-field__input') and not(@type='hidden')]`
- `//input[contains(@class, 'v-field__input') and @type='text' and @maxlength='100']`
- `//input[@type='text' and @maxlength='100']`
- `//input[contains(@placeholder,'E-mail') or contains(@placeholder,'CPF') or contains(@placeholder,'CNPJ')]`

## Senha

- `//input[@type='password']`
- `//input[contains(@placeholder, 'Senha')]`
- `//label[contains(., 'Senha')]/ancestor::div[contains(@class, 'v-field')][1]//input`

## Botao Entrar

- `//button[normalize-space()='Entrar']`
- `//span[normalize-space()='Entrar']/ancestor::button`
- `//button[@type='submit']`

## Boas praticas

- Sempre usar locator visivel.
- Evitar seletor por ID dinamico.
- Salvar screenshot + HTML em erro para ajuste orientado por evidencia.
