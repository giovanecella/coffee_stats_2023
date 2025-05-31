import pandas as pd
import pycountry
import logging
from pathlib import Path
#alterar para fazer juncao dos datasets a partir do iso code. se nao houver, dropar
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

COUNTRY_CACHE= {}

def normalize_country(name: str) -> str:
    if name in COUNTRY_CACHE:
        return COUNTRY_CACHE[name]
    
    try:
        normalized = pycountry.countries.lookup(name).name
        COUNTRY_CACHE[name] = normalized
        return normalized
    except LookupError:
        logger.warning(f"País não encontrado: {name}. Usando nome original.")
        COUNTRY_CACHE[name] = name
        return name

def transform_all() -> pd.DataFrame:
    DATA_DIR = Path("data")
    CONSUMPTION_PATH = DATA_DIR / "coffee_consumption_2023.csv"
    EMISSIONS_PATH = DATA_DIR / "coffee_emission_water.csv"
    POPULATION_PATH = DATA_DIR / "population_2023.csv"
    OUTPUT_PATH = DATA_DIR / "coffee_footprint_2023.csv"
    
    try:
        cons = pd.read_csv(CONSUMPTION_PATH)
        emis = pd.read_csv(EMISSIONS_PATH)
        pop = pd.read_csv(POPULATION_PATH)
        logger.info("Dados carregados com sucesso")
    except FileNotFoundError as e:
        logger.error(f"Arquivo de dados não encontrado {str(e)}")
        raise
    
    required_columns = [
        (cons, ["Area", "consumption_t"]),
        (emis, ["product", "emission_kgCO2e_per_kg", "water_l_per_kg"]),
        (pop, ["country", "country_code", "population"])
    ]
    
    for df_obj, cols in required_columns:
        missing = [c for c in cols if c not in df_obj.columns]
        if missing:
            logger.error(f"Faltam colunas no dataset: {', '.join(missing)}")
            raise ValueError("Estrutura de dados inválida")
    
    logger.info("Normalizando nomes de países")
    cons["country_norm"] = cons["Area"].apply(normalize_country)
    pop["country_norm"] = pop["country"].apply(normalize_country)
    
    emis["country_norm"] = "Global"
    
    cons["consumption_kg"] = cons["consumption_t"] * 1000
    
    logger.info("Unindo dadasets")
    df = (
        cons[["country_norm", "consumption_kg"]]
        .merge(
            pop[["country_norm", "country_code", "population"]],
            on="country_norm",
            how="left"
        )
        .merge(
            emis[["emission_kgCO2e_per_kg", "water_l_per_kg"]],
            how="cross"
        )
    )
    
    logger.info("Calculando métricas de pegada ecológica")
    df["consumption_kg_per_capita"] = df["consumption_kg"] / df["population"]
    df["total_emission_kgCO2e"] = df["consumption_kg"] * df["emission_kgCO2e_per_kg"]
    df["emission_kgCO2e_per_capita"] = df["consumption_kg_per_capita"] * df["emission_kgCO2e_per_kg"]
    df["total_water_l"] = df["consumption_kg"] * df["water_l_per_kg"]
    df["water_per_capita"] = df["consumption_kg_per_capita"] * df["water_l_per_kg"]
    
    country_map = cons.set_index("country_norm")["Area"].to_dict()
    df["original_country"] = df["country_norm"].map(country_map)
    
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)
    logger.info(f"Dados transformados salvos em {OUTPUT_PATH}")
    
    return df
    
if __name__=="__main__":
    try:
        df = transform_all()
        logger.info(f"Tranformação completa. Formato do dataset final: {df.shape}")
        print("Sample dos dados transformados:")
        print(df[["original_country", "consumption_kg_per_capita"]].head())
    except Exception as e:
        logger.error(f"Transformação falhou: {str(e)}")
