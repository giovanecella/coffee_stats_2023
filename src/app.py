import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path


DATA_PATH = Path("data") / "coffee_footprint_2023.csv"

COFFEE_COLORS = ["#f6e0c2", "#e6c19a", "#d9a56f", "#c78a4a", "#b16f2e", "#9a561d", "#7d3f10"]
EMISSION_COLORS = ["#fff7f3", "#fde0dd", "#fcc5c0", "#fa9fb5", "#f768a1", "#dd3497", "#ae017e"]

@st.cache
def load_data():
    try:
        df = pd.read_csv(DATA_PATH)
        df["total_emission_million_kgCO2e"] = df["total_emission_kgCO2e"] / 1_000_000
        
        return df
    
    except Exception as e:
        st.error(f"Erro carregando dados: {str(e)}")
        return pd.DataFrame()
        
st.set_page_config(layout="wide", page_title="Pegada Ecológica do Café")
df = load_data()

st.title("🌍 Sustentabilidade Global do Café")

metric = st.radio(
    "Escolha uma medida:",
    options=("Consumo de café per capita", "Emissões totais por café", "Consumo de água per capita por café"),
    horizontal=True
)

metric_map = {
    "Consumo de café per capita": {
    "column": "consumption_kg_per_capita",
    "unit": "kg/pessoa",
    "colors": COFFEE_COLORS,
    "format": "{:,.2f}"
    },
    "Emissões totais por café": {
        "column": "total_emission_million_kgCO2e",
        "unit": "milhões de kg kg CO₂e",
        "colors": EMISSION_COLORS,
        "format": "{:,.2f}"
    },
    "Consumo de água per capita por café": {
        "column": "water_per_capita",
        "unit": "L/pessoa",
        "colors": px.colors.squential.Blues,
        "format": "{:,.1f}"
    }
}

metric_config = metric_map[metric]
col = metric_config["column"]

fig = px.choropleth(
)
