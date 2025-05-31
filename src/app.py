import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import googletrans
from googletrans import Translator

translator = Translator()

DATA_PATH = Path("data") / "coffee_footprint_2023.csv"

COFFEE_COLORS = ["#f6e0c2", "#e6c19a", "#d9a56f", "#c78a4a", "#b16f2e", "#9a561d", "#7d3f10"]
EMISSION_COLORS = ["#fff7f3", "#fde0dd", "#fcc5c0", "#fa9fb5", "#f768a1", "#dd3497", "#ae017e"]

EMISSION_SOURCE_COLORS = {
    "land_use": "#4caf50",
    "farm": "#8bc34a",
    "processing": "#ffc107",
    "transport": "#ff9800",
    "retail": "#9c27b0",
    "packaging": "#3f51b5",
    "losses": "#f44336"
}


@st.cache_data
def load_data():
    try:
        df = pd.read_csv(DATA_PATH)
        df["total_emission_million_kgCO2e"] = df["total_emission_kgCO2e"] / 1_000_000
        return df
    
    except Exception as e:
        st.error(f"Erro carregando dados: {str(e)}")
        return pd.DataFrame()

@st.cache_data
def translate_country_names(country_names: pd.Series) -> pd.Series:
    if country_names is None or country_names.empty:
        return pd.Series(dtype=str)
    
    translations = {}
    for name in country_names.unique():
        try:
            translated = translator.translate(name, src='en', dest='pt').text
            translations[name] = translated
        except Exception as e:
            #st.warning(f"Tradução falhou para {name}: {str(e)}")
            translations[name] = name
    return country_names.map(translations)
        
st.set_page_config(layout="wide", page_title="Pegada Ecológica do Café")
df = load_data()

if not df.empty:
    df["country_pt"] = translate_country_names(df["country_norm"])

st.title("🌍 Sustentabilidade Global do Café")

metric = st.radio(
    "Escolha uma métrica:",
    options=("Consumo de café per capita", "Emissões totais por café", "Consumo de água per capita (do café)"),
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
    "Consumo de água per capita (do café)": {
        "column": "water_per_capita",
        "unit": "L/pessoa",
        "colors": px.colors.sequential.Blues,
        "format": "{:,.1f}"
    }
}

metric_config = metric_map[metric]
col = metric_config["column"]

if not df.empty:
    fig = px.choropleth(
        df,
        locations="country_code",
        color=col,
        hover_name="country_pt",
        hover_data={
            "consumption_kg_per_capita": ":.2f",
            "total_emission_million_kgCO2e": ":.2f",
            "water_per_capita": ":,.1f",
            "country_code": False,
            "country_pt": False
        },
        color_continuous_scale=metric_config["colors"],
        title=f"{metric} ({metric_config['unit']})",
        labels={col: f"{metric} ({metric_config['unit']})"},
        projection="natural earth"
    )
    fig.update_layout(
        margin={"r":0, "t":40, "l":0, "b":0},
        coloraxis_colorbar_title=f"{metric}<br>({metric_config['unit']})"
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()
if not df.empty:
    country_list = sorted(df["country_pt"].dropna().unique())
    selected_country = st.selectbox("Selecione um país para detalhes:", [""] + country_list)
else:
    selected_country = None

if selected_country:
    original_name = df.loc[df["country_pt"] == selected_country, "country_norm"].iloc[0]
    country_data = df[df["country_norm"] == original_name].iloc[0]
    
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
        "Pegada hídrica",
        f"{country_data['water_per_capita']:,.1f} L/pessoa",
        "Uso anual de água para produção de café"
        )
    
    st.subheader("♻️ Composição das emissões")
    
    #dados obtidos a partir de https://ourworldindata.org/grapher/food-emissions-supply-chain
    emission_sources = [
        {"source": "land_use", "name": "Uso da terra", "share": 0.134},
        {"source": "farm", "name": "Cultivo", "share": 0.377},
        {"source": "processing", "name": "Processamento", "share": 0.021},
        {"source": "transport", "name": "Transporte", "share": 0.005},
        {"source": "retail", "name": "Varejo", "share": 0.002},
        {"source": "packaging", "name": "Embalagem", "share": 0.059},
        {"source": "losses", "name": "Perdas", "share": 0.402}
    ]
    
    emissions_df = pd.DataFrame(emission_sources)
    emissions_df["Emissões (kg CO₂e)"] = emissions_df["share"] * country_data['total_emission_kgCO2e']
    emissions_df["color"] = emissions_df["source"].map(EMISSION_SOURCE_COLORS)
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig_pie = px.pie(
            emissions_df,
            names="name",
            values="share",
            color="source",
            color_discrete_map=EMISSION_SOURCE_COLORS,
            hover_data= None,
            hover_name= None,
            hole=0.4,
            title="Emissões por estágio da cadeia de produção"
        )   
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        fig_bar = px.bar(
            emissions_df.sort_values("share", ascending=False),
            x="name",
            y="Emissões (kg CO₂e)",
            color="source",
            color_discrete_map=EMISSION_SOURCE_COLORS,
            hover_data= None,
            hover_name= None,
            title="Emissões absolutas por estágio",
            labels={"name": "Estágio de produção"}
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    
    st.subheader("🌍 Comparação com médias globais")
    
    avg_cons = df["consumption_kg_per_capita"].mean()
    avg_emission = df["total_emission_kgCO2e"].mean()
    avg_water = df["water_per_capita"].mean()
    
    cons_diff = (country_data['consumption_kg_per_capita'] - avg_cons) / avg_cons * 100
    emission_diff = (country_data['total_emission_kgCO2e'] - avg_emission) / avg_emission * 100
    water_diff = (country_data['water_per_capita'] - avg_water) - avg_water * 100
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Média global de consumo",
            f"{avg_cons:.2f} kg/pessoa",
            f"{cons_diff:+.1f}%",
            delta_color="inverse"
        )
    
    with col2:
        st.metric(
            "Média global de emissões",
            f"{avg_emission/1_000_000:.2f} milhões de kg CO₂e",
            f"{emission_diff:+1f}%",
            delta_color="inverse"
        )
    
    with col3:
        st.metric(
            "Média global de consumo de água",
            f"{avg_water:,.1f} L/pessoa",
            f"{water_diff:+.1f}%",
            delta_color="inverse"
        )
    
st.divider()
st.caption("Fontes de dados: FAO, Banco Mundial, Our World in Data | Criado com Streamlit")
