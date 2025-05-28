import logging
from pathlib import Path
from typing import Optional
import requests
from request.adapters import HTTTPAdapter
from urllib3.util.retry import Retry
import pandas as pd

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
        session.mount('https://', HTTTPAdapter(max_retries=retries))
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

if __name__ == "__main__":
    if (df := fetch_coffee_consumption()) is not None:
        logger.info(f"Dados carregados com sucesso:\n{df.head()}")
