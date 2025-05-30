import os
import logging
from pathlib import Path
from typing import Optional
import requests
from requests.adapters import HTTPAdapter  
from urllib3.util.retry import Retry
import pandas as pd
from io import StringIO
from faostat import get_data_df



logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


DATA_DIR = Path("data")
FAO_CSV = DATA_DIR / "coffee_consumption_2023.csv"
EM_WATER_CSV = DATA_DIR / "coffee_emission_water.csv"
GHG_URL = "https://nyc3.digitaloceanspaces.com/owid-public/data/energy/ghg-per-kg-poore.csv"
WATER_URL = "https://nyc3.digitaloceanspaces.com/owid-public/data/water/water-withdrawals-per-kg-poore.csv"
POP_CSV = DATA_DIR / "population_2023.csv"
WB_API = "http://api.worldbank.org/v2/country/all/indicator/SP.POP.TOTL"

def create_session() -> requests.Session:
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=1.5,
        status_forcelist=[500,502,503,504,521]
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

def fetch_coffee_consumption(year: int = 2022) -> Optional[pd.DataFrame]:
    if FAO_CSV.exists():
        logger.info(f"Carregando dados de {FAO_CSV}")
        return pd.read_csv(FAO_CSV)
    fao_df = get_data_df(
        code="SCL",
        pars={
            "year": str(year),
            "element": "2141",
            "item": "657"}
    )
    df_fao = fao_df[["Area", "Value"]].rename(columns={"Value": "consumption_t"})
    FAO_CSV.parent.mkdir(parents=True, exist_ok=True)
    df_fao.to_csv(FAO_CSV, index=False)
    logger.info(f"{len(df_fao)} linhas salvas em {FAO_CSV} da biblioteca faostat")
    return df_fao

   
def fetch_emission_water() -> Optional[pd.DataFrame]:
    
    if EM_WATER_CSV.exists():
        logger.info(f"Carregando dados de {EM_WATER_CSV}")
        return pd.read_csv(EM_WATER_CSV)
    
    session = create_session()
    headers = {"User-Agent": "python-requests"}

    try:
        r1 = session.get(GHG_URL, headers=headers, timeout=10)
        r1.raise_for_status()
        ghg_df = pd.read_csv(StringIO(r1.text))
        coffee_ghg = (
            ghg_df.query("Entity == 'Coffee'")
            .loc[:, ['Entity', 'GHG emissions per kilogram (Poore & Nemecek, 2018)']]
            .rename(columns={
                "Entity": "product",
                "GHG emissions per kilogram (Poore & Nemecek, 2018)": "emission_kgCO2e_per_kg"
            })
        )
        
        r2 = session.get(WATER_URL, headers=headers, timeout=10)
        r2.raise_for_status()
        water_df = pd.read_csv(StringIO(r2.text))
        coffee_water = (
            water_df.query("Entity == 'Coffee'")
            .loc[:,["Entity", "Freshwater withdrawals per kilogram (Poore & Nemecek, 2018)"]]
            .rename(columns={
                "Entity": "product",
                "Freshwater withdrawals per kilogram (Poore & Nemecek, 2018)": "water_l_perg_kg"
            })
        )
        
        df = pd.merge(coffee_ghg, coffee_water, on='product')
        EM_WATER_CSV.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(EM_WATER_CSV, index=False)
        logger.info(f"Dados de emissão/água salvos em {EM_WATER_CSV}, vindos de Our World in Data")
        return df
    
    except Exception as e:
        logger.error(f"Operação OWID falhou: {str(e)}", exc_info=True)
        return None


def fetch_population(year: int = 2023) -> Optional[pd.DataFrame]:
    if POP_CSV.exists():
        logger.info(f"Carregando dados de {POP_CSV}")
        return pd.read_csv(POP_CSV)
    session = create_session()
    params = {
        "date": year,
        "format": "json",
        "per_page": 500,
        "page": 1
    }
    all_data = []
    try:
        while True:
            resp = session.get(WB_API, params=params, timeout=10)  
            resp.raise_for_status()
            data = resp.json()
            if len(data) < 2 or not data[1]:
                break
            all_data.extend(data[1])
            params["page"] += 1
        
        df = pd.DataFrame([
            {
                "country": item["country"]["value"],
                "country_code": item["countryiso3code"],
                "population": item["value"]
            }
            for item in all_data
            if item.get("value") is not None
        ])
        
        POP_CSV.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(POP_CSV, index=False)
        logger.info(f"Dados populacionais salvos em {POP_CSV}")
        return df
    
    except Exception as e:
        logger.error(f"Operação falhou: {str(e)}", exc_info=True)
        return None


if __name__ == "__main__":
    try:
        logger.info("Iniciando extração de dados...")
        
        # Coffee consumption
        coffee_df = fetch_coffee_consumption()
        if coffee_df is not None:
            logger.info(f"Dados de consumo de café:\n{coffee_df.head()}")
        
        # Emission/water data
        emission_df = fetch_emission_water()
        if emission_df is not None:
            logger.info(f"Dados de emissão/água:\n{emission_df.head()}")
        
        # Population data
        population_df = fetch_population()
        if population_df is not None:
            logger.info(f"Dados populacionais:\n{population_df.head()}")
            
        logger.info("Extração concluída com sucesso!")
        
    except Exception as e:
        logger.error(f"Falha na execução do script: {str(e)}", exc_info=True)
