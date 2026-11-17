# Minha Letra AI ✍️

Aplicativo Streamlit para usar uma amostra manuscrita como referência visual e transcrever fotos de páginas de caderno com a OpenAI Responses API.

## O que inclui

- Ficha para copiar à mão com A–Z, a–z, números de 0 a 9, acentos, pontuação, símbolos matemáticos e frases de referência.
- Upload de uma foto da ficha preenchida para servir como amostra de caligrafia.
- Upload de uma foto de página do caderno.
- Transcrição fiel ou com correção ortográfica evidente.
- Editor do resultado, exportação TXT e exemplos de correções temporários na sessão.
- Redimensionamento e validação de imagens antes do envio.

## Como executar localmente

1. Instale Python 3.10 ou superior.
2. Instale as dependências: `pip install -r requirements.txt`
3. Configure `OPENAI_API_KEY` como variável de ambiente, sem colocá-la no código ou no GitHub.
4. Inicie: `streamlit run app.py`

## Publicar no Streamlit Community Cloud

1. Entre no Streamlit Community Cloud e conecte sua conta GitHub.
2. Crie um app apontando para este repositório, branch `main` e arquivo `app.py`.
3. Abra as configurações do app (**Settings → Secrets**) e adicione:

```toml
OPENAI_API_KEY = "sua-chave-da-api"
OPENAI_MODEL = "gpt-4.1"
```

4. Salve. Nunca adicione a chave a este repositório ou ao código-fonte.

O modelo padrão configurado é `gpt-4.1`. Se sua conta API não tiver acesso a ele, ajuste `OPENAI_MODEL` para um modelo com entrada de imagem habilitada na sua conta.

## Limites importantes

- O app **não faz fine-tuning nem treinamento permanente**. A imagem de referência é enviada junto com cada página para orientar o reconhecimento visual.
- A amostra e as correções ficam apenas na memória da sessão Streamlit; podem desaparecer quando a sessão termina ou reinicia.
- A IA pode errar, especialmente com fotos desfocadas, baixa iluminação, páginas tortas ou escrita muito comprimida. Revise sempre o resultado.
- As imagens da amostra e da página são enviadas à OpenAI API durante a transcrição. Não envie documentos ou anotações com dados sensíveis.
- O uso da API pode gerar cobrança separada da assinatura ChatGPT. Configure a chave com ajuda de um responsável e acompanhe os limites de uso.

## Arquivos

- `app.py` — interface e processamento.
- `requirements.txt` — dependências Python.
- `.gitignore` — evita enviar segredos e arquivos temporários.
