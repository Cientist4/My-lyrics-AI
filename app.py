from __future__ import annotations
import base64
import io
import os
import streamlit as st
from PIL import Image, ImageOps, UnidentifiedImageError
from openai import OpenAI, APIConnectionError, APIStatusError, AuthenticationError, BadRequestError, RateLimitError

APP_NAME = "Minha Letra AI"
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-6.1-terra")
MAX_IMAGE_BYTES = 12 * 1024 * 1024
MAX_IMAGE_SIDE = 2800

SAMPLE_SHEET = """MINHA FICHA DE CALIGRAFIA — MINHA LETRA AI

1) LETRAS MAIÚSCULAS
ABCDEFGHIJKLMNOPQRSTUVWXYZ

2) LETRAS MINÚSCULAS
abcdefghijklmnopqrstuvwxyz

3) NÚMEROS
0123456789

4) ACENTOS E LETRAS DO PORTUGUÊS
Á À Â Ã É Ê Í Ó Ô Õ Ú Ü Ç
á à â ã é ê í ó ô õ ú ü ç

5) PONTUAÇÃO E SÍMBOLOS
. , ; : ! ? ... ' " “ ” ‘ ’
( ) [ ] { } < > / \\ | _ - —
+ - × ÷ = ≠ < > ≤ ≥ ± √ π % ‰
@ # $ R$ € £ ¥ & * ^ ~ ° º ª §

6) FRASES PARA MOSTRAR COMO VOCÊ ESCREVE
Amanhã, às 8h30, vou estudar Português e Matemática.
O pequeno gato bebeu água perto da janela.
Quero que a inteligência artificial reconheça minha letra.
B, D, P e R são diferentes; m, n, u e r também.
Meu caderno tem números: 12, 25, 48, 100 e 2026.

DICA: copie tudo à mão, com sua letra normal. Não tente enfeitar nem mudar seu jeito de escrever.
"""

st.set_page_config(page_title=APP_NAME, page_icon="✍️", layout="centered")


def get_secret(name: str, fallback: str = "") -> str:
    value = os.getenv(name, fallback)
    try:
        secret_value = st.secrets.get(name, "")
        if secret_value:
            value = str(secret_value)
    except Exception:
        pass
    return str(value).strip()


def prepare_image(raw_bytes: bytes) -> bytes:
    if not raw_bytes:
        raise ValueError("O arquivo está vazio.")
    if len(raw_bytes) > MAX_IMAGE_BYTES:
        raise ValueError("A imagem passou de 12 MB. Envie uma foto menor.")
    try:
        image = Image.open(io.BytesIO(raw_bytes))
        image = ImageOps.exif_transpose(image).convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValueError("Não consegui abrir essa imagem. Envie JPG, PNG ou WEBP.") from exc
    image.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE), Image.Resampling.LANCZOS)
    output = io.BytesIO()
    image.save(output, format="JPEG", quality=90, optimize=True)
    return output.getvalue()


def to_data_url(image_bytes: bytes) -> str:
    encoded = base64.b64encode(image_bytes).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def build_prompt(mode: str, notes: str, corrections: list[dict[str, str]]) -> str:
    if mode == "Fiel ao caderno":
        instruction = "Transcreva fielmente. Preserve palavras, acentos, maiúsculas, pontuação, quebras de linha e erros do original. Não corrija."
    else:
        instruction = "Transcreva e corrija apenas erros evidentes de ortografia e pontuação, sem mudar o sentido. Marque dúvidas."

    correction_text = ""
    if corrections:
        correction_text = "\nExemplos de correções desta sessão:\n" + "\n".join(
            f'- A leitura correta de "{x["wrong"]}" é "{x["right"]}".' for x in corrections[-12:]
        )

    return f"""Você é especialista em ler caligrafia manuscrita em português.

Você receberá DUAS imagens:
1. A PRIMEIRA é uma amostra da caligrafia da pessoa. Use-a como referência para formato das letras, números, ligações, inclinação e espaçamento.
2. A SEGUNDA é a página do caderno que deve ser transcrita.

TAREFA: {instruction}

REGRAS:
- Compare os formatos das letras da página com a amostra da mesma pessoa; não suponha que a letra seja padronizada.
- Use o contexto, mas não invente trechos que não estejam visíveis.
- Para trechos realmente impossíveis de ler, escreva [ilegível].
- Preserve a ordem, títulos, listas, parágrafos, números, símbolos e fórmulas.
- Diferencie letras parecidas usando amostra e contexto: a/o, c/e, i/l, m/n, u/v, r/s, B/D, P/R, 1/7 e 0/6.
- Não descreva a imagem. Entregue somente a transcrição.
{correction_text}
Observações do usuário: {notes.strip() or "Nenhuma."}
"""


def transcribe(reference: bytes, page: bytes, mode: str, notes: str,
               corrections: list[dict[str, str]]) -> str:
    api_key = get_secret("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Configure OPENAI_API_KEY em Streamlit Settings → Secrets. Nunca coloque a chave no GitHub.")
    model = get_secret("OPENAI_MODEL", DEFAULT_MODEL) or DEFAULT_MODEL
    client = OpenAI(api_key=api_key)
    response = client.responses.create(
        model=model,
        input=[{"role": "user", "content": [
            {"type": "input_text", "text": build_prompt(mode, notes, corrections)},
            {"type": "input_image", "image_url": to_data_url(reference), "detail": "high"},
            {"type": "input_image", "image_url": to_data_url(page), "detail": "high"},
        ]}],
        max_output_tokens=6000,
    )
    result = (response.output_text or "").strip()
    if not result:
        raise RuntimeError("A IA não retornou texto. Tente outra foto, com mais iluminação e foco.")
    return result


for key, default in {
    "handwriting_reference": None,
    "reference_name": "",
    "corrections": [],
    "editable_transcript": "",
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

st.title("✍️ Minha Letra AI")
st.caption("Use uma amostra da sua caligrafia como referência para transcrever páginas do caderno.")

with st.sidebar:
    st.subheader("Seu perfil de letra")
    if st.session_state.handwriting_reference:
        st.success("Amostra carregada nesta sessão")
        st.caption(st.session_state.reference_name)
    else:
        st.info("Você ainda não salvou uma amostra.")
    st.caption(f"Correções nesta sessão: {len(st.session_state.corrections)}")
    if st.button("Limpar amostra e correções", use_container_width=True):
        st.session_state.handwriting_reference = None
        st.session_state.reference_name = ""
        st.session_state.corrections = []
        st.session_state.editable_transcript = ""
        st.rerun()
    st.divider()
    st.caption("Amostras e correções ficam na memória da sessão. Não há treinamento permanente nesta versão.")

tab_sample, tab_transcribe, tab_about = st.tabs([
    "1. Ensinar minha letra", "2. Transcrever caderno", "3. Como funciona"
])

with tab_sample:
    st.header("Crie sua amostra de caligrafia")
    st.write("Copie a ficha abaixo à mão, usando sua letra normal. Depois fotografe a folha inteira.")
    st.download_button("Baixar ficha para copiar (TXT)", data=SAMPLE_SHEET,
                       file_name="ficha_caligrafia_minha_letra_ai.txt",
                       mime="text/plain", use_container_width=True)
    with st.expander("Ver alfabeto, números e símbolos", expanded=True):
        st.code(SAMPLE_SHEET, language="text")
    st.info("Use folha clara e caneta escura. Deixe espaço entre as linhas e não corte a folha na foto.")
    sample_upload = st.file_uploader("Envie a foto da ficha preenchida",
        type=["jpg", "jpeg", "png", "webp"], key="sample_upload",
        help="JPG, PNG ou WEBP. Máximo de 12 MB.")
    if st.button("Salvar minha amostra de letra", type="primary", use_container_width=True):
        if sample_upload is None:
            st.warning("Primeiro escolha a foto da ficha preenchida.")
        else:
            try:
                st.session_state.handwriting_reference = prepare_image(sample_upload.getvalue())
                st.session_state.reference_name = sample_upload.name
                st.success("Amostra salva! Abra a aba Transcrever caderno.")
            except ValueError as exc:
                st.error(str(exc))
    if st.session_state.handwriting_reference:
        st.caption("Amostra salva nesta sessão:")
        st.image(st.session_state.handwriting_reference,
                 caption=st.session_state.reference_name, use_container_width=True)

with tab_transcribe:
    st.header("Transcreva uma página")
    if not st.session_state.handwriting_reference:
        st.warning("Primeiro salve uma foto da sua ficha na aba Ensinar minha letra.")
    else:
        st.success("Amostra pronta para servir de referência.")
    page_upload = st.file_uploader("Envie a foto da página do caderno",
        type=["jpg", "jpeg", "png", "webp"], key="page_upload",
        help="Fotografe de cima, com boa luz, foco e a página inteira. Máximo de 12 MB.")
    mode = st.radio("Como você quer a transcrição?",
                    ["Fiel ao caderno", "Corrigir ortografia evidente"])
    notes = st.text_input("Observação opcional",
                          placeholder="Ex.: o assunto é Ciências; há nomes próprios.")
    if st.button("Transcrever página", type="primary", use_container_width=True,
                 disabled=not bool(st.session_state.handwriting_reference)):
        if page_upload is None:
            st.warning("Escolha a foto da página que deseja transcrever.")
        else:
            try:
                page = prepare_image(page_upload.getvalue())
                with st.spinner("Analisando a amostra e lendo a página..."):
                    st.session_state.editable_transcript = transcribe(
                        st.session_state.handwriting_reference, page, mode, notes,
                        st.session_state.corrections)
                st.success("Transcrição concluída. Revise o resultado.")
            except ValueError as exc:
                st.error(str(exc))
            except AuthenticationError:
                st.error("A API recusou a chave. Verifique a configuração com o responsável.")
            except RateLimitError:
                st.error("O limite ou saldo da API foi atingido. Confira o uso e a cobrança com o responsável.")
            except APIConnectionError:
                st.error("Não consegui conectar à API. Confira sua internet e tente novamente.")
            except BadRequestError as exc:
                st.error(f"A API não aceitou a solicitação: {exc}")
            except APIStatusError as exc:
                st.error(f"A API retornou erro HTTP {exc.status_code}. Confira o modelo configurado.")
            except RuntimeError as exc:
                st.error(str(exc))
            except Exception as exc:
                st.error("Ocorreu um erro inesperado. Tente outra foto.")
                st.caption(f"Detalhe técnico: {type(exc).__name__}")

    st.subheader("Resultado editável")
    edited = st.text_area("Revise e corrija o texto:", key="editable_transcript",
                          height=300, placeholder="A transcrição aparecerá aqui...")
    if edited.strip():
        st.download_button("Baixar transcrição em TXT", data=edited,
            file_name="transcricao_minha_letra.txt", mime="text/plain",
            use_container_width=True)
        with st.expander("Ensinar uma correção para esta sessão"):
            wrong = st.text_input("Como a IA leu", key="correction_wrong")
            right = st.text_input("Como deveria ler", key="correction_right")
            if st.button("Guardar exemplo de correção"):
                if wrong.strip() and right.strip():
                    st.session_state.corrections.append(
                        {"wrong": wrong.strip(), "right": right.strip()})
                    st.success("Exemplo adicionado para as próximas transcrições desta sessão.")
                    st.rerun()
                else:
                    st.warning("Preencha os dois campos.")

with tab_about:
    st.header("Como esta versão funciona")
    st.markdown("""
    1. Copie a ficha completa à mão e envie uma foto como amostra.
    2. Ao transcrever, o app envia a amostra e a página juntas ao modelo de visão da OpenAI.
    3. O modelo compara o formato das letras e tenta reconhecer o texto.
    4. Você pode corrigir o resultado e guardar exemplos durante a sessão.
    """)
    st.warning("Esta versão não treina nem altera permanentemente um modelo. A amostra e as correções são referências temporárias da sessão. Ao fechar ou perder a sessão, envie a amostra novamente. Nenhuma IA garante leitura perfeita.")
    st.markdown("**Privacidade:** o código não grava suas fotos em banco de dados, mas as imagens são enviadas à API da OpenAI durante a transcrição. Não envie páginas com senhas ou informações privadas.")
    st.markdown("**Custos:** a API pode ser cobrada separadamente do ChatGPT. Configure a chave com ajuda de um responsável. Nunca compartilhe a chave nem a coloque no GitHub.")
    st.caption(f"Modelo padrão: {DEFAULT_MODEL}. Pode ser alterado por OPENAI_MODEL no Streamlit Secrets.")
