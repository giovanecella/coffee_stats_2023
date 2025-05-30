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
    df,
    locations="iso_alpha",
    color=col,
    hover_name="country_norm",
    hover_data={
        "consumption_kg_per_capita": ":.2f",
        "total_emission_million_kgCO2e": ":.2f",
        "water_per_capita": ":,.1f",
        "iso_alpha": False
    },
    color_continuous_scale=metric_config["colors"],
    title=f"{metric} ({metri_config['unit']})",
    labels={col: f"{metric} ({metric_config['unit']})"},
    projection="natural earth"
)
fig.update_layout(
    margin={"r":0, "t":40, "l":0, "b":0},
    coloraxis_colorbar_title=f"{metric}<br>({metric_config['unit']})"
)
st.plotly_chart(fig, use_container_width=True)

st.divider()
country_list = sorted(df["country_norm"].dropna().unique())
selected_country = st.selectbox("Selecione um país:", [""] + country_list)

if selected_country:
    country_data = df[df["country_norm"] == selected_country].iloc[0]
    
    st.subheader(f"Dados para {selected_country}")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Consumo de café",
            f"{country_data['consumption_kg_per_capita']:.2f} kg/pessoa",
            "Consumo anual per capita"
        )
    
    with col2:
        st.metric(
        "Emissões totais do café",
        f"{country_data['total_emission_million_kgCO2e']:.2f} milhões de kg de CO₂e",
        "Emissões anuais a partir do café"
        )
    
    with col3:
        st.metric(
        f"{country_data['water_per_capita']:,.1f} L/pessoa",
        "Uso anual de água para produção de café"
        )
    
    st.subheader("♻️ Detalhamento das emissões")
    
    #dados obtidos a partir de https://ourworldindata.org/grapher/food-emissions-supply-chain
    land_use = country_data['total_emission_kgCO2e'] * 0.134
    farm = country_data['total_emission_kgCO2e'] * 0.377
    processing = country_data['total_emission_kgCO2e'] * 0.021
    transport = country_data['total_emission_kgCO2e'] * 0.005
    retail = country_data['total_emission_kgCO2e'] * 0.002
    packaging = country_data['total_emission_kgCO2e'] * 0.059
    losses = country_data['total_emission_kgCO2e'] * 0.402
    
    emissions_df = pd.DataFrame({
        "Origem": ["Uso da terra", "Plantio", "Processamento", "Transporte", "Venda", "Embalagem", "Perdas"],
        "Emissões (kg CO₂e)": [land_use, farm, processing, transport, retail, packaging, losses],
        "Cores": []
    })
    
    fig_pie = px.pie(
        emissions_df,
        names="Origem",
        values="Emissões (kg CO₂e)",
        color="Color",
        color_discrete_map="indentity",
        hole=0.4,
        title="Emissões por estágio da cadeia de suprimentos"
    )
    st.plotly_chart(fig_pie, use_container_width=True)
    
    st.subheader("🌍 Comparação global")
    
    avg_cons = df["consumption_kg_per_capita"].mean()
    avg_emission = df["total_emission_million_kgCO2e"].mean * 1_000_000
    avg_water = df["water_per_capita"].mean()
    
    cons_diff = (country_data['consumption_kg_per_capita'] - avg_cons) / avg_cons * 100
    emission_diff = (country_data['total_emission_kgCO2e'] - avg_emission) / avg_emission * 100
    water_diff = (country_data['water_per_capita'] - avg_water) - avg_water * 100
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Consumo médio global",
            f"{avg_cons:.2f} kg/pessoa",
            f"{cons_diff:+.1f}%",
            delta_color="inverse"
        )
    
    with col2:
        st.metric(
            "Emissão média global",
            f"{avg_emission/1_000_000:.2f} milhões de kg CO₂e",
            f"{emission_diff:+1f}%",
            delta_color="inverse"
        )
    
    with col3:
        st.metric(
            "Consumo médio de água",
            f"{avg_water:,.1f} L/pessoa",
            f"{water_diff+.1f}%",
            delta_color="inverse"
        )
    
st.divider()
st.caption("Fontes de dados: FAO, Banco Mundial, Our World in Data | Criado com Streamlit")
