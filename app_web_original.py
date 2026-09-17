import json
import os
import re

import pandas as pd
import streamlit as st
from google import genai


CRITERIA = ["Seguranca", "EPIs", "Clareza", "Objetividade", "Aplicabilidade"]


def parse_json_response(response_text: str, expected_start: str):
    cleaned = response_text.strip().replace("```json", "").replace("```", "").strip()
    start = cleaned.find(expected_start)
    end = cleaned.rfind("}" if expected_start == "{" else "]")
    if start == -1 or end == -1 or end < start:
        raise ValueError("A resposta da IA nao trouxe o JSON esperado.")
    return json.loads(cleaned[start : end + 1])


def generate_texts(client: genai.Client, profile: str, topic: str) -> dict:
    prompt = f"""
Crie 4 textos curtos de DDS sobre o tema: {topic}.

Cada texto deve ter de 8 a 10 linhas.
Retorne apenas JSON neste formato:
{{
  "Texto 1": "...",
  "Texto 2": "...",
  "Texto 3": "...",
  "Texto 4": "..."
}}
"""
    chat = client.chats.create(model="gemini-3.1-flash-lite-preview")
    response = chat.send_message(prompt)
    return parse_json_response(response.text, "{")

# gemini-2.5-flash

def evaluate_texts(client: genai.Client, texts: dict) -> pd.DataFrame:
    prompt = f"""
Avalie os textos de DDS abaixo, atribuindo notas de 1 a 10 para cada criterio.

Criterios:
- Seguranca
- EPIs
- Clareza
- Objetividade
- Aplicabilidade

Textos:
{texts}

Retorne apenas JSON neste formato:
[
    {{"Texto": "Texto 1", "Seguranca": 0, "EPIs": 0, "Clareza": 0, "Objetividade": 0, "Aplicabilidade": 0}},
    {{"Texto": "Texto 2", "Seguranca": 0, "EPIs": 0, "Clareza": 0, "Objetividade": 0, "Aplicabilidade": 0}},
    {{"Texto": "Texto 3", "Seguranca": 0, "EPIs": 0, "Clareza": 0, "Objetividade": 0, "Aplicabilidade": 0}},
    {{"Texto": "Texto 4", "Seguranca": 0, "EPIs": 0, "Clareza": 0, "Objetividade": 0, "Aplicabilidade": 0}}
]
"""
    chat = client.chats.create(model="gemini-2.5-flash")
    response = chat.send_message(prompt)
    data = parse_json_response(response.text, "[")
    frame = pd.DataFrame(data)
    missing = set(["Texto", *CRITERIA]) - set(frame.columns)
    if missing:
        raise ValueError(f"A avaliacao nao trouxe as colunas: {', '.join(sorted(missing))}.")
    frame[CRITERIA] = frame[CRITERIA].apply(pd.to_numeric, errors="raise")
    return frame


def calculate_ranking(evaluations: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    original = evaluations.set_index("Texto")[CRITERIA].astype(float)
    normalized = original.div(original.sum(axis=0), axis=1)
    mean = normalized.mean(axis=0)
    standard_deviation = normalized.std(axis=0)
    coefficient_of_variation = standard_deviation / mean
    matriz_cv = pd.DataFrame({
        "Media": mean,
        "Desvio_Padrao": standard_deviation,
    })
    matriz_cv["Coeficiente_de_Variacao"] = coefficient_of_variation
    sum_cv = matriz_cv["Coeficiente_de_Variacao"].sum()
    matriz_cv["Peso_AHP_Gaussiano"] = (
        matriz_cv["Coeficiente_de_Variacao"] / sum_cv
    )
    weights = matriz_cv["Peso_AHP_Gaussiano"]
    weighted = normalized * weights
    final_score = weighted.sum(axis=1)
    ranking = pd.DataFrame({
        "Texto": final_score.index,
        "Pontuacao": final_score,
    })
    ranking = ranking.sort_values(by="Pontuacao", ascending=False)
    ranking["Ranking"] = range(1, len(ranking) + 1)
    return ranking, matriz_cv


def get_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key and "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
    if not api_key:
        raise RuntimeError("Defina a variavel de ambiente GEMINI_API_KEY antes de iniciar o site.")
    return genai.Client(api_key=api_key)


st.set_page_config(page_title="Recomendacao de DDS", page_icon="🦺", layout="wide")
st.title("Recomendacao de DDS com IA")
st.caption("Gere, avalie e classifique textos de dialogo diario de seguranca.")

with st.form("dds_form"):
    profile = st.text_input(
        "Perfil do publico",
        value="Eletricista industrial e trabalho 12 anos em empresa",
    )
    topic = st.text_area(
        "Tema do DDS",
        value=(
            "Ontem ocorreu um incidente envolvendo atividades em paineis eletricos energizados. "
            "Gerar um DDS voltado aos principais riscos em intervencoes eletricas, enfatizando "
            "medidas preventivas, uso adequado de EPIs, bloqueio de energia e conscientizacao "
            "operacional conforme praticas da NR-10"
        ),
        height=130,
    )
    submitted = st.form_submit_button("Gerar recomendacao", type="primary")

if submitted:
    if not profile.strip() or not topic.strip():
        st.warning("Preencha o perfil e o tema antes de gerar a recomendacao.")
    else:
        try:
            with st.spinner("Gerando e avaliando os textos..."):
                client = get_client()
                texts = generate_texts(client, profile, topic)
                evaluations = evaluate_texts(client, texts)
                ranking, weights = calculate_ranking(evaluations)
            st.session_state["result"] = (texts, evaluations, ranking, weights)
        except Exception as error:
            st.error(f"Nao foi possivel concluir a recomendacao: {error}")

if "result" in st.session_state:
    texts, evaluations, ranking, weights = st.session_state["result"]
    winner = ranking.iloc[0]["Texto"]
    st.success(f"Texto recomendado: {winner} (pontuacao {ranking.iloc[0]['Pontuacao']:.4f})")

    overview, texts_tab, evaluation_tab = st.tabs(["Ranking", "Textos", "Avaliacao"])
    with overview:
        left, right = st.columns([1.4, 1])
        with left:
            st.bar_chart(ranking.set_index("Texto")["Pontuacao"])
            st.dataframe(ranking, hide_index=True, use_container_width=True)
        with right:
            st.subheader("Calculo dos criterios")
            st.dataframe(weights, use_container_width=True)
    with texts_tab:
        for name, text in texts.items():
            with st.expander(name, expanded=name == winner):
                st.write(text)
    with evaluation_tab:
        st.dataframe(evaluations, hide_index=True, use_container_width=True)
