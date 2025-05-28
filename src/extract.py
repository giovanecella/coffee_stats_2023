import logging
from pathlib import Path
from typing import Optional
import requests
from requests.adapters import HTTPAdapter  
from urllib3.util.retry import Retry
import pandas as pd
import os


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


FAO_CSV = Path("data") / "coffee_consumption_2023.csv"
FAO_API = "https://fenixservices.fao.org/faostat/api/v1/en/data/QCL"

def fetch_coffee_consumption(year: int = 2023) -> Optional[pd.DataFrame]:
    try:
        if FAO_CSV.exists():
            logger.info(f"Carregando dados de {FAO_CSV}")
            return pd.read_csv(FAO_CSV)
        
        session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=1.5,
            status_forcelist=[500, 502, 503, 504]
        )
        session.mount('https://', HTTPAdapter(max_retries=retries))
        
        params = {
            "year": str(year),
            "element": "5401",
            "item": "6501",
            "unit": "1000 tonnes"
        }
        resp = session.get(FAO_API, params=params)
        resp.raise_for_status()
        
        if 'data' not in (data := resp.json()):
            raise ValueError("Missing 'data' key in API response")
    
        df = pd.DataFrame(data['data'])[['area', 'value']]
        df = df.rename(columns={
            'area': 'country',
            'value': 'consumption_1000t'
        })
    
        FAO_CSV.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(FAO_CSV, index=False)
        logger.info(f"{len(df)} linhas salvas em {FAO_CSV}")
        return df
    
    except Exception as e:
        logger.error(f"Operação falhou: {str(e)}", exc_info=True)
        return None


EM_WATER_CSV = Path("data") / "coffee_emission_water.csv"
GHG_URL = "https://ourworldindata.org/grapher/ghg-per-kg-poore.csv?v=1&csvType=full&useColumnShortNames=true"
WATER_URL = "https://ourworldindata.org/grapher/water-withdrawals-per-kg-poore.csv?v=1&csvType=full&useColumnShortNames=true"
    
def fetch_emission_water() -> Optional[pd.DataFrame]:
    try:
        if EM_WATER_CSV.exists():
            logger.info(f"Carregando dados de {EM_WATER_CSV}")
            return pd.read_csv(EM_WATER_CSV)
        

        ghg_df = pd.read_csv(GHG_URL)
        coffee_ghg = ghg_df.query("Entity == 'Coffee'")[['Entity', 'GHG emissions per kilogram (Poore & Nemecek, 2018)']]
        coffee_ghg.columns = ['product', 'emission_kgCO2e_per_kg']
        
        water_df = pd.read_csv(WATER_URL)
        coffee_water = water_df.query("Entity == 'Coffee'")[['Entity', 'Freshwater withdrawals per kilogram (Poore & Nemecek, 2018)']]
        coffee_water.columns = ['product', 'water_l_per_kg']
        
        df = pd.merge(coffee_ghg, coffee_water, on='product')
        
        EM_WATER_CSV.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(EM_WATER_CSV, index=False)
        logger.info(f"Dados de emissão/água salvos em {EM_WATER_CSV}")
        return df
    
    except Exception as e:
        logger.error(f"Operação falhou: {str(e)}", exc_info=True)
        return None


POP_CSV = Path("data") / "population_2023.csv"
WB_API = "http://api.worldbank.org/v2/country/all/indicator/SP.POP.TOTL"

def fetch_population(year: int = 2023) -> Optional[pd.DataFrame]:
    try:
        if POP_CSV.exists():
            logger.info(f"Carregando dados de {POP_CSV}")
            return pd.read_csv(POP_CSV)
        
        params = {
            "date": year,
            "format": "json",
            "per_page": 500,
            "page": 1
        }
        
        all_data = []
        session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=1.5,
            status_forcelist=[500, 502, 503, 504]
        )
        session.mount('https://', HTTPAdapter(max_retries=retries))
        
        while True:
            logger.info(f"Buscando página {params['page']}")
            response = session.get(WB_API, params=params)  
            response.raise_for_status()
            
            data = response.json()
            if len(data) < 2:
                break
            
            page_data = data[1]
            if not page_data:
                break
                
            all_data.extend(page_data)
            params["page"] += 1
            
        df = pd.DataFrame([
            {
                "country": item["country"]["value"],
                "country_code": item["countryiso3code"],
                "year": item["date"],
                "population": item["value"]
            }
            for item in all_data
            if item.get("value") is not None
        ])
        
        df = df.drop_duplicates(subset=["country_code", "year"])
        df = df.sort_values(["country", "year"])
        
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
