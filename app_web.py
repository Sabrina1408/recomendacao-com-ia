import html
import json
import os
from pathlib import Path

import pandas as pd
import streamlit as st
from google import genai

APP_DIR = Path(__file__).resolve().parent
PDF_FILE = APP_DIR / "Seleção_Inteligente_de_Textos_de_DDS.pdf"
CRITERIA = ["Seguranca", "EPIs", "Clareza", "Objetividade", "Aplicabilidade"]
LABELS = {"Seguranca": "Segurança", "EPIs": "EPIs", "Clareza": "Clareza",
          "Objetividade": "Objetividade", "Aplicabilidade": "Aplicabilidade"}

AUTHORS = [
    ("Prof. Doutoranda Jaqueline Alves", "Universidade Federal Fluminense (UFF)",
     [("LinkedIn", "https://www.linkedin.com/in/jaqueline-alves-cmb/"),
      ("Lattes", "http://lattes.cnpq.br/9581708310870285")]),
    ("Sabrina Alves Brito", "UVA | Desenvolvedora, Rede Globo Televisão",
     [("LinkedIn", "https://www.linkedin.com/in/sabrina-a-brito/")]),
    ("Prof. Dr. Rodrigo Caiado", "Pontifícia Universidade Católica do Rio de Janeiro (PUC-Rio)",
     [("LinkedIn", "https://www.linkedin.com/in/rodrigo-caiado-a7187938/"),
      ("Lattes", "http://lattes.cnpq.br/3922452850648712")]),
    ("Prof. Dr. Gilson Lima", "Universidade Federal Fluminense (UFF)",
     [("LinkedIn", "https://www.linkedin.com/in/gilson-lima-25808323/"),
      ("Lattes", "http://lattes.cnpq.br/2248567464602970")]),
]

st.set_page_config(page_title="DDS SmartSelect", page_icon="🦺", layout="wide",
                   initial_sidebar_state="collapsed")

st.markdown("""
<style>
:root{--navy:#082b4c;--blue:#0b5f9e;--pale:#edf6fc;--green:#16845b;
--gold:#e6a817;--ink:#17212b;--muted:#5d6b78;--line:#dce5ec}
.stApp{background:#f7f9fb;color:var(--ink)}
.block-container{max-width:1180px;padding-top:1.4rem;padding-bottom:2rem}
header[data-testid="stHeader"]{background:transparent} #MainMenu,footer{visibility:hidden}
.hero{padding:2rem 2.2rem;border-radius:18px;background:linear-gradient(125deg,#062946,#0b5f9e);
box-shadow:0 12px 30px rgba(8,43,76,.16);margin-bottom:1.1rem}
.hero-tag{display:inline-block;padding:.28rem .7rem;border:1px solid rgba(255,255,255,.35);
border-radius:999px;color:#fff;font-size:.78rem;font-weight:700;letter-spacing:.04em;text-transform:uppercase}
.hero h1{color:#fff;font-size:2.35rem;margin:.65rem 0 .2rem}
.hero h2{color:#dceefa;font-size:1.15rem;font-weight:500;margin:0}
.hero p{color:#c9e1f1;margin:.8rem 0 0;max-width:800px}
.section-title{color:var(--navy);margin:1.3rem 0 .7rem}
.panel{background:#fff;border:1px solid var(--line);border-radius:14px;padding:1.15rem 1.25rem;
box-shadow:0 4px 16px rgba(8,43,76,.05)}
.method-flow{display:grid;grid-template-columns:repeat(5,1fr);gap:.6rem;margin:.7rem 0 1rem}
.method-step{min-height:96px;padding:.85rem .7rem;border-radius:12px;background:var(--pale);
border-top:4px solid var(--blue);text-align:center}
.step-number{color:var(--blue);font-weight:800;font-size:.76rem}
.step-title{color:var(--navy);font-weight:750;margin-top:.3rem}
.step-text{color:var(--muted);font-size:.82rem;margin-top:.22rem}
.winner-card{padding:1.35rem 1.5rem;background:linear-gradient(135deg,#effaf5,#fff);
border:1px solid #a8dcc7;border-left:7px solid var(--green);border-radius:14px;margin:.8rem 0 1rem}
.winner-kicker{color:var(--green);font-weight:800;text-transform:uppercase;font-size:.78rem}
.winner-title{color:#0e5139;font-size:1.45rem;font-weight:800;margin:.25rem 0 .65rem}
.dds-text{white-space:pre-line;line-height:1.65}.safety-note{background:#fff8e7;
border-left:5px solid var(--gold);border-radius:8px;padding:.85rem 1rem;color:#5b4817;margin:1rem 0}
.author-card{min-height:165px;background:#fff;border:1px solid var(--line);border-radius:12px;padding:1rem}
.author-name{color:var(--navy);font-weight:800}.author-affiliation{color:var(--muted);
font-size:.86rem;min-height:62px;margin:.3rem 0 .7rem}
.author-links a{color:var(--blue);font-weight:700;text-decoration:none;margin-right:.8rem}
.event-note{text-align:center;color:var(--muted);margin:1.2rem 0 .5rem;font-size:.9rem}
div.stButton>button,div.stDownloadButton>button{border-radius:9px;font-weight:700;min-height:44px}
div.stButton>button[kind="primary"]{background:var(--blue);border-color:var(--blue)}
[data-testid="stForm"]{background:#fff;border:1px solid var(--line);border-radius:14px;
padding:1.25rem;box-shadow:0 4px 16px rgba(8,43,76,.05)}
@media(max-width:800px){.hero{padding:1.45rem}.hero h1{font-size:1.8rem}
.method-flow{grid-template-columns:1fr}.method-step{min-height:auto;text-align:left}}
</style>""", unsafe_allow_html=True)


def parse_json_response(response_text: str, expected_start: str):
    cleaned = response_text.strip().replace("~~~json", "").replace("~~~", "").strip()
    cleaned = cleaned.replace(chr(96) * 3 + "json", "").replace(chr(96) * 3, "").strip()
    start = cleaned.find(expected_start)
    end = cleaned.rfind("}" if expected_start == "{" else "]")
    if start == -1 or end == -1 or end < start:
        raise ValueError("A resposta da IA não trouxe o JSON esperado.")
    return json.loads(cleaned[start:end + 1])


def generate_texts(client: genai.Client, profile: str, topic: str) -> dict:
    prompt = f"""
Você é especialista em comunicação de segurança do trabalho.
PERFIL DO PÚBLICO: {profile}
TEMA E CONTEXTO: {topic}

Crie 4 alternativas de Diálogo Diário de Segurança em português do Brasil,
adaptadas ao público. Cada uma deve ter de 8 a 10 linhas curtas, linguagem clara,
riscos e medidas preventivas aplicáveis. Mencione EPIs quando pertinentes e não
invente requisitos legais ou procedimentos da organização.

Retorne somente JSON válido:
{{"Texto 1":"...", "Texto 2":"...", "Texto 3":"...", "Texto 4":"..."}}
"""
    response = client.chats.create(model="gemini-3.1-flash-lite-preview").send_message(prompt)
    texts = parse_json_response(response.text, "{")
    if set(texts) != {f"Texto {n}" for n in range(1, 5)}:
        raise ValueError("A IA não retornou as quatro alternativas esperadas.")
    return texts


def evaluate_texts(client: genai.Client, texts: dict) -> pd.DataFrame:
    prompt = f"""
Avalie comparativamente estes DDS de 1 a 10 em: Seguranca (riscos e prevenção),
EPIs (adequação), Clareza, Objetividade e Aplicabilidade.
TEXTOS: {json.dumps(texts, ensure_ascii=False)}
Retorne somente JSON válido:
[
{{"Texto":"Texto 1","Seguranca":0,"EPIs":0,"Clareza":0,"Objetividade":0,"Aplicabilidade":0}},
{{"Texto":"Texto 2","Seguranca":0,"EPIs":0,"Clareza":0,"Objetividade":0,"Aplicabilidade":0}},
{{"Texto":"Texto 3","Seguranca":0,"EPIs":0,"Clareza":0,"Objetividade":0,"Aplicabilidade":0}},
{{"Texto":"Texto 4","Seguranca":0,"EPIs":0,"Clareza":0,"Objetividade":0,"Aplicabilidade":0}}
]
"""
    response = client.chats.create(model="gemini-2.5-flash").send_message(prompt)
    frame = pd.DataFrame(parse_json_response(response.text, "["))
    missing = set(["Texto", *CRITERIA]) - set(frame.columns)
    if missing:
        raise ValueError(f"A avaliação não trouxe: {', '.join(sorted(missing))}.")
    if len(frame) != 4 or set(frame["Texto"]) != {f"Texto {n}" for n in range(1, 5)}:
        raise ValueError("A avaliação não retornou as quatro alternativas.")
    frame[CRITERIA] = frame[CRITERIA].apply(pd.to_numeric, errors="raise")
    if not frame[CRITERIA].apply(lambda col: col.between(1, 10).all()).all():
        raise ValueError("As notas devem estar entre 1 e 10.")
    return frame[["Texto", *CRITERIA]]


def calculate_ranking(evaluations: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    original = evaluations.set_index("Texto")[CRITERIA].astype(float)
    normalized = original.div(original.sum(axis=0), axis=1)
    means = normalized.mean(axis=0)
    deviations = normalized.std(axis=0)
    coefficients = deviations.div(means).fillna(0)
    weight_table = pd.DataFrame({"Média": means, "Desvio-padrão": deviations,
                                 "Coeficiente de variação": coefficients})
    cv_sum = coefficients.sum()
    weight_table["Peso AHP-Gaussiano"] = (
        1 / len(CRITERIA) if cv_sum == 0 else coefficients / cv_sum
    )
    scores = (normalized * weight_table["Peso AHP-Gaussiano"]).sum(axis=1)
    ranking = pd.DataFrame({"Texto": scores.index, "Pontuação": scores})
    ranking = ranking.sort_values("Pontuação", ascending=False).reset_index(drop=True)
    ranking.insert(0, "Posição", range(1, len(ranking) + 1))
    return ranking, weight_table


def get_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY")
    try:
        if not api_key and "GEMINI_API_KEY" in st.secrets:
            api_key = st.secrets["GEMINI_API_KEY"]
    except FileNotFoundError:
        pass
    if not api_key:
        raise RuntimeError("Configure GEMINI_API_KEY nos Secrets do Streamlit.")
    return genai.Client(api_key=api_key)


def show_logos():
    logos = [("UFF_logo.jpg", "UFF"), ("veiga_logo.png", "UVA"), ("puc_logo.png", "PUC-Rio")]
    for column, (filename, label) in zip(st.columns(3), logos):
        with column:
            path = APP_DIR / filename
            if path.exists():
                st.image(str(path), use_container_width=True)
            else:
                st.markdown(f"<div style='text-align:center;color:#5d6b78'>{label}</div>",
                            unsafe_allow_html=True)


def render_author(name, affiliation, links):
    links_html = "".join(
        f'<a href="{html.escape(url)}" target="_blank" rel="noopener noreferrer">{html.escape(label)}</a>'
        for label, url in links
    )
    st.markdown(f"""<div class="author-card"><div class="author-name">{html.escape(name)}</div>
    <div class="author-affiliation">{html.escape(affiliation)}</div>
    <div class="author-links">{links_html}</div></div>""", unsafe_allow_html=True)


st.markdown("""<section class="hero">
<span class="hero-tag">Sistema de apoio à decisão em segurança industrial</span>
<h1>DDS SmartSelect</h1><h2>Seleção Inteligente de Diálogos Diários de Segurança</h2>
<p>IA Generativa e AHP-Gaussiano para gerar, avaliar e priorizar textos de DDS
adequados ao público e ao contexto operacional.</p></section>""", unsafe_allow_html=True)

logo_area, article_area = st.columns([2.15, 1], gap="large")
with logo_area:
    show_logos()
with article_area:
    st.markdown("#### Artigo científico")
    st.caption("Trabalho aprovado para apresentação no XLVI ENEGEP 2026.")
    if PDF_FILE.exists():
        with open(PDF_FILE, "rb") as pdf:
            st.download_button("📄 Acessar artigo completo", data=pdf.read(),
                               file_name=PDF_FILE.name, mime="application/pdf",
                               use_container_width=True)
    else:
        st.info(f'Inclua o arquivo "{PDF_FILE.name}" no diretório do app.')

st.markdown('<h3 class="section-title">Como funciona?</h3>', unsafe_allow_html=True)
st.markdown("""<div class="method-flow">
<div class="method-step"><div class="step-number">ETAPA 1</div><div class="step-title">Contexto</div><div class="step-text">Perfil do público e tema</div></div>
<div class="method-step"><div class="step-number">ETAPA 2</div><div class="step-title">Geração</div><div class="step-text">Quatro DDS criados por IA</div></div>
<div class="method-step"><div class="step-number">ETAPA 3</div><div class="step-title">Avaliação</div><div class="step-text">Notas em cinco critérios</div></div>
<div class="method-step"><div class="step-number">ETAPA 4</div><div class="step-title">AHP-Gaussiano</div><div class="step-text">Pesos pela variabilidade</div></div>
<div class="method-step"><div class="step-number">ETAPA 5</div><div class="step-title">Recomendação</div><div class="step-text">Ranking e melhor DDS</div></div>
</div>""", unsafe_allow_html=True)

for column, label in zip(st.columns(5), LABELS.values()):
    column.metric(label, "1–10")

st.markdown('<h3 class="section-title">Gerar nova recomendação</h3>', unsafe_allow_html=True)
with st.form("dds_form"):
    profile = st.text_input("Perfil do público",
        value="Eletricistas industriais com experiência em atividades de manutenção",
        help="Informe função, experiência ou características que ajudem a adequar a linguagem.")
    topic = st.text_area("Tema e contexto do DDS", value=(
        "Ocorreu um incidente envolvendo atividades em painéis elétricos energizados. "
        "Elaborar um DDS sobre os principais riscos em intervenções elétricas, com ênfase "
        "em medidas preventivas, uso adequado de EPIs, bloqueio de energia e "
        "conscientização operacional conforme as práticas da NR-10."),
        height=145, help="Descreva a situação, o risco ou a mensagem preventiva.")
    submitted = st.form_submit_button("✨ Gerar e selecionar o melhor DDS",
                                      type="primary", use_container_width=True)

if submitted:
    if not profile.strip() or not topic.strip():
        st.warning("Preencha o perfil do público e o tema.")
    else:
        try:
            with st.spinner("Gerando quatro alternativas e aplicando o AHP-Gaussiano..."):
                client = get_client()
                texts = generate_texts(client, profile.strip(), topic.strip())
                evaluations = evaluate_texts(client, texts)
                ranking, weights = calculate_ranking(evaluations)
            st.session_state["result"] = (texts, evaluations, ranking, weights)
        except Exception as error:
            st.error(f"Não foi possível concluir a recomendação: {error}")

if "result" in st.session_state:
    texts, evaluations, ranking, weights = st.session_state["result"]
    winner = ranking.iloc[0]["Texto"]
    winner_score = float(ranking.iloc[0]["Pontuação"])
    winner_text = html.escape(str(texts[winner])).replace("\\n", "<br>")
    st.markdown('<h3 class="section-title">DDS recomendado</h3>', unsafe_allow_html=True)
    st.markdown(f"""<div class="winner-card">
    <div class="winner-kicker">🏆 Alternativa priorizada pelo modelo multicritério</div>
    <div class="winner-title">{html.escape(winner)} · Pontuação {winner_score:.4f}</div>
    <div class="dds-text">{winner_text}</div></div>""", unsafe_allow_html=True)

    winner_row = evaluations.set_index("Texto").loc[winner]
    for column, criterion in zip(st.columns(5), CRITERIA):
        column.metric(LABELS[criterion], f"{winner_row[criterion]:.0f}/10")
    st.markdown("""<div class="safety-note"><strong>Atenção:</strong> o DDS gerado é
    material de apoio à comunicação preventiva. O profissional responsável deve verificar
    sua compatibilidade com os procedimentos, normas e requisitos da organização.</div>""",
    unsafe_allow_html=True)

    with st.expander("🔎 Ver análise completa e cálculo do método"):
        tab1, tab2, tab3, tab4 = st.tabs(
            ["Ranking", "Quatro alternativas", "Matriz de avaliação", "Pesos do método"])
        with tab1:
            shown = ranking.copy()
            shown["Pontuação"] = shown["Pontuação"].round(4)
            left, right = st.columns([1.2, 1])
            with left:
                st.bar_chart(ranking.set_index("Texto")["Pontuação"], color="#0b5f9e")
            with right:
                st.dataframe(shown, hide_index=True, use_container_width=True)
        with tab2:
            for name, text in texts.items():
                with st.expander(name, expanded=name == winner):
                    if name == winner:
                        st.success("Alternativa recomendada")
                    st.write(text)
        with tab3:
            st.dataframe(evaluations.rename(columns=LABELS), hide_index=True,
                         use_container_width=True)
            st.caption("As notas variam de 1 a 10 e são atribuídas comparativamente pela IA.")
        with tab4:
            shown_weights = weights.rename(index=LABELS).copy()
            shown_weights.index.name = "Critério"
            st.dataframe(shown_weights.style.format("{:.4f}"), use_container_width=True)
            st.markdown("""O **AHP-Gaussiano** obtém pesos a partir da variabilidade
            das avaliações. Quanto mais um critério diferencia as alternativas, maior tende
            a ser seu peso. A pontuação final é a soma ponderada dos valores normalizados.""")

st.markdown('<h3 class="section-title">Sobre o método</h3>', unsafe_allow_html=True)
st.markdown("""<div class="panel">O <strong>DDS SmartSelect</strong> integra IA
Generativa e AHP-Gaussiano. A IA cria quatro alternativas e avalia os textos segundo
segurança, EPIs, clareza, objetividade e aplicabilidade. Essas avaliações formam uma
matriz de decisão, processada para produzir pesos, ranking e recomendação. Assim, o
sistema não apenas gera um texto: ele compara alternativas de maneira estruturada.</div>""",
unsafe_allow_html=True)

st.markdown('<h3 class="section-title">Pesquisa desenvolvida por</h3>', unsafe_allow_html=True)
for column, author in zip(st.columns(4), AUTHORS):
    with column:
        render_author(*author)
st.markdown('<div class="event-note">Trabalho aprovado para apresentação no XLVI Encontro Nacional de Engenharia de Produção · ENEGEP 2026</div>',
            unsafe_allow_html=True)
