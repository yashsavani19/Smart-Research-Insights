from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv()

DEFAULT_QUERY = (
    '('
    'marine OR ocean OR offshore OR maritime OR naval OR ship OR aquaculture'
    ') AND ('
    '"autonomous underwater vehicle" OR AUV OR ROV OR ASV OR USV OR autonomous OR "path planning" OR SLAM OR '
    '"computer vision" OR "defect detection" OR "predictive maintenance" OR "condition-based maintenance" OR CBM OR '
    '"digital twin" OR "data fusion" OR "edge computing" OR "multi-sensor fusion" OR "time-series anomaly detection" OR "change detection"'
    ' OR '
    'sonar OR "acoustic sensing" OR "ultrasonic" OR "multibeam echosounder" OR "sidescan sonar" OR '
    '"underwater acoustic communication" OR "optical modem" OR "blue-green laser" OR "acoustic modem"'
    ' OR '
    '"marine renewable energy" OR "wave energy" OR "wave energy converter" OR "tidal turbine" OR "offshore wind" OR "floating wind" OR '
    '"battery thermal management" OR "energy efficiency" OR "air lubrication" OR "life cycle assessment"'
    ' OR '
    '"corrosion resistant" OR antifouling OR biofouling OR "marine coatings" OR "cathodic protection" OR CFRP OR GFRP'
    ' OR '
    '"AIS analytics" OR "vessel trajectory" OR "trajectory prediction"'
    ')'
)

@dataclass
class Settings:
    database_url: str
    openalex_query: str
    country_filter: str = os.getenv("OPENALEX_COUNTRY_FILTER", "AU|NZ")

def get_settings() -> Settings:
    q = os.getenv("OPENALEX_QUERY_OVERRIDE") or DEFAULT_QUERY
    db = os.environ["DATABASE_URL"]  # fail fast if missing
    return Settings(database_url=db, openalex_query=q)
