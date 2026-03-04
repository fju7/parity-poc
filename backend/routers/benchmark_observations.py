"""
Benchmark Observations: Crowdsourced Commercial Rate Database

POST /api/benchmark-observations  — save anonymized billing observations

Stores anonymized data points from completed bill analyses. No user_id,
no patient info, no provider names, no exact dates, no full ZIP codes.
"""

import os
from collections import Counter
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from supabase import create_client

router = APIRouter(prefix="/api", tags=["benchmark-observations"])

# ---------------------------------------------------------------------------
# Supabase client (lazy singleton)
# ---------------------------------------------------------------------------

_supabase = None


def _get_supabase():
    global _supabase
    if _supabase is None:
        url = os.environ.get("SUPABASE_URL", "https://kfxxpscdwoemtzylhhhb.supabase.co")
        key = os.environ.get("SUPABASE_SERVICE_KEY", "")
        if not key:
            raise RuntimeError("SUPABASE_SERVICE_KEY not set")
        _supabase = create_client(url, key)
    return _supabase


# ---------------------------------------------------------------------------
# Insurer Normalization
# ---------------------------------------------------------------------------

INSURER_ALIASES = {
    "cigna": ["cigna", "cigna healthcare", "cigna health", "evernorth"],
    "aetna": ["aetna", "aetna health", "cvs health", "cvs/aetna"],
    "uhc": ["united", "unitedhealthcare", "united healthcare", "uhc", "optum"],
    "bcbs": [
        "blue cross", "blue shield", "bcbs", "anthem", "carefirst",
        "highmark", "premera", "regence", "horizon", "independence",
        "excellus", "wellmark", "florida blue", "blue cross blue shield",
    ],
    "humana": ["humana"],
    "kaiser": ["kaiser", "kaiser permanente"],
    "tricare": ["tricare"],
    "medicare_advantage": ["medicare advantage", "ma plan"],
    "medicaid_managed": ["medicaid", "managed medicaid"],
}


def normalize_insurer(raw_text: str) -> tuple[str, str]:
    """Returns (normalized_key, raw_text)."""
    lower = raw_text.lower().strip()
    for key, aliases in INSURER_ALIASES.items():
        for alias in aliases:
            if alias in lower:
                return key, raw_text
    return "other", raw_text


# ---------------------------------------------------------------------------
# Provider Specialty Inference
# ---------------------------------------------------------------------------

CPT_SPECIALTY_MAP = {
    # Primary Care / E&M (office visits)
    "99201": "primary_care", "99202": "primary_care", "99203": "primary_care",
    "99204": "primary_care", "99205": "primary_care",
    "99211": "primary_care", "99212": "primary_care", "99213": "primary_care",
    "99214": "primary_care", "99215": "primary_care",
    # Primary Care / E&M (hospital visits)
    "99221": "primary_care", "99222": "primary_care", "99223": "primary_care",
    "99231": "primary_care", "99232": "primary_care", "99233": "primary_care",
    # Primary Care / E&M (consultations)
    "99241": "primary_care", "99242": "primary_care", "99243": "primary_care",
    "99244": "primary_care", "99245": "primary_care",
    # Emergency Medicine
    "99281": "emergency_medicine", "99282": "emergency_medicine",
    "99283": "emergency_medicine", "99284": "emergency_medicine",
    "99285": "emergency_medicine",
    # Preventive / Wellness
    "99381": "primary_care", "99382": "primary_care", "99383": "primary_care",
    "99384": "primary_care", "99385": "primary_care", "99386": "primary_care",
    "99391": "primary_care", "99392": "primary_care", "99393": "primary_care",
    "99394": "primary_care", "99395": "primary_care", "99396": "primary_care",
    # Dermatology
    "11102": "dermatology", "11103": "dermatology", "11104": "dermatology",
    "11105": "dermatology", "11106": "dermatology",
    "11300": "dermatology", "11301": "dermatology", "11305": "dermatology",
    "11306": "dermatology", "11310": "dermatology", "11311": "dermatology",
    "17000": "dermatology", "17003": "dermatology", "17004": "dermatology",
    "17110": "dermatology", "17111": "dermatology",
    # Cardiology
    "93000": "cardiology", "93005": "cardiology", "93010": "cardiology",
    "93015": "cardiology", "93016": "cardiology", "93017": "cardiology",
    "93018": "cardiology",
    "93306": "cardiology", "93307": "cardiology", "93308": "cardiology",
    "93312": "cardiology", "93314": "cardiology", "93315": "cardiology",
    "93320": "cardiology", "93321": "cardiology", "93325": "cardiology",
    "93350": "cardiology", "93351": "cardiology",
    "93458": "cardiology", "93459": "cardiology", "93460": "cardiology",
    # Orthopedics
    "20610": "orthopedics", "20611": "orthopedics",
    "27130": "orthopedics", "27236": "orthopedics", "27244": "orthopedics",
    "27245": "orthopedics", "27447": "orthopedics",
    "29826": "orthopedics", "29827": "orthopedics", "29881": "orthopedics",
    "29882": "orthopedics",
    "23472": "orthopedics", "27446": "orthopedics",
    # Gastroenterology
    "43235": "gastroenterology", "43239": "gastroenterology",
    "43249": "gastroenterology",
    "45378": "gastroenterology", "45380": "gastroenterology",
    "45381": "gastroenterology", "45384": "gastroenterology",
    "45385": "gastroenterology",
    # Ophthalmology
    "66821": "ophthalmology", "66984": "ophthalmology", "66982": "ophthalmology",
    "67028": "ophthalmology", "92012": "ophthalmology", "92014": "ophthalmology",
    "92134": "ophthalmology", "92250": "ophthalmology",
    # Urology
    "52000": "urology", "52332": "urology", "52353": "urology",
    "55700": "urology", "55866": "urology",
    # OB/GYN
    "58558": "obstetrics_gynecology", "58571": "obstetrics_gynecology",
    "58661": "obstetrics_gynecology", "59400": "obstetrics_gynecology",
    "59510": "obstetrics_gynecology", "59610": "obstetrics_gynecology",
    "76801": "obstetrics_gynecology", "76805": "obstetrics_gynecology",
    "76815": "obstetrics_gynecology", "76817": "obstetrics_gynecology",
    # General Surgery
    "47562": "general_surgery", "47563": "general_surgery",
    "49505": "general_surgery", "49507": "general_surgery",
    "49650": "general_surgery",
    "43280": "general_surgery", "43281": "general_surgery",
    # ENT / Otolaryngology
    "42820": "otolaryngology", "42821": "otolaryngology",
    "42826": "otolaryngology", "30520": "otolaryngology",
    "31231": "otolaryngology", "31237": "otolaryngology",
    # Pulmonology
    "31622": "pulmonology", "31623": "pulmonology", "31624": "pulmonology",
    "94010": "pulmonology", "94060": "pulmonology", "94375": "pulmonology",
    "94726": "pulmonology", "94727": "pulmonology", "94729": "pulmonology",
    # Neurology
    "95004": "allergy", "95024": "allergy",
    "95816": "neurology", "95819": "neurology", "95861": "neurology",
    "95907": "neurology", "95908": "neurology",
    # Psychiatry
    "90791": "psychiatry", "90792": "psychiatry",
    "90832": "psychiatry", "90834": "psychiatry", "90837": "psychiatry",
    "90847": "psychiatry",
    # Physical Therapy / Rehab
    "97110": "physical_therapy", "97112": "physical_therapy",
    "97116": "physical_therapy", "97140": "physical_therapy",
    "97161": "physical_therapy", "97162": "physical_therapy",
    "97163": "physical_therapy", "97530": "physical_therapy",
    # Anesthesiology
    "00100": "anesthesiology", "00400": "anesthesiology",
    "00670": "anesthesiology", "00810": "anesthesiology",
    "01996": "anesthesiology",
    # Radiology / Imaging
    "70553": "radiology", "71046": "radiology", "71250": "radiology",
    "71260": "radiology", "72148": "radiology", "72156": "radiology",
    "73221": "radiology", "73721": "radiology", "74177": "radiology",
    "74178": "radiology", "76700": "radiology", "76830": "radiology",
    "77065": "radiology", "77066": "radiology", "77067": "radiology",
    # Radiation Oncology
    "77385": "radiation_oncology", "77386": "radiation_oncology",
    "77412": "radiation_oncology",
    # Pathology
    "88305": "pathology", "88304": "pathology", "88302": "pathology",
    "88307": "pathology", "88309": "pathology",
    "88312": "pathology", "88313": "pathology",
    "88342": "pathology", "88360": "pathology",
    # Laboratory
    "80048": "laboratory", "80050": "laboratory", "80053": "laboratory",
    "80061": "laboratory", "80076": "laboratory",
    "82565": "laboratory", "82947": "laboratory", "83036": "laboratory",
    "84443": "laboratory", "85025": "laboratory", "85027": "laboratory",
    "36415": "laboratory", "36416": "laboratory",
    "87491": "laboratory", "87591": "laboratory", "87801": "laboratory",
}


def infer_specialty(cpt_codes: list[str]) -> str:
    """Infer provider specialty from the most common specialty across CPT codes."""
    specialties = [CPT_SPECIALTY_MAP.get(code, "unknown") for code in cpt_codes]
    specialties = [s for s in specialties if s != "unknown"]
    if not specialties:
        return "unknown"
    return Counter(specialties).most_common(1)[0][0]


# ---------------------------------------------------------------------------
# Region Derivation
# ---------------------------------------------------------------------------

ZIP3_TO_REGION = {
    # New York metro
    "100": "manhattan_ny", "101": "manhattan_ny", "102": "manhattan_ny",
    "103": "staten_island_ny", "104": "bronx_ny",
    "105": "westchester_ny", "106": "westchester_ny",
    "107": "yonkers_ny", "108": "new_rochelle_ny",
    "110": "queens_ny", "111": "long_island_ny", "112": "brooklyn_ny",
    "113": "flushing_ny", "114": "jamaica_ny", "115": "long_island_ny",
    "116": "long_island_ny", "117": "long_island_ny",
    "070": "northern_nj", "071": "northern_nj", "072": "northern_nj",
    "073": "northern_nj", "074": "northern_nj", "076": "northern_nj",
    "077": "northern_nj", "078": "northern_nj", "079": "northern_nj",
    # Los Angeles metro
    "900": "los_angeles_ca", "901": "los_angeles_ca", "902": "los_angeles_ca",
    "903": "inglewood_ca", "904": "santa_monica_ca",
    "905": "torrance_ca", "906": "long_beach_ca", "907": "long_beach_ca",
    "908": "long_beach_ca", "910": "pasadena_ca", "911": "pasadena_ca",
    "912": "glendale_ca", "913": "van_nuys_ca", "914": "van_nuys_ca",
    "915": "burbank_ca", "916": "san_fernando_valley_ca",
    "917": "industry_ca", "918": "alhambra_ca",
    "925": "riverside_ca", "926": "santa_ana_ca", "927": "santa_ana_ca",
    "928": "anaheim_ca",
    # Chicago metro
    "600": "chicago_suburbs_il", "601": "chicago_suburbs_il",
    "602": "chicago_suburbs_il", "603": "chicago_suburbs_il",
    "604": "chicago_suburbs_il", "605": "chicago_suburbs_il",
    "606": "chicago_il", "607": "chicago_suburbs_il",
    "608": "chicago_suburbs_il",
    # Dallas-Fort Worth metro
    "750": "dallas_tx", "751": "dallas_tx", "752": "dallas_tx",
    "753": "dallas_tx", "760": "fort_worth_tx", "761": "fort_worth_tx",
    "762": "fort_worth_tx",
    # Houston metro
    "770": "houston_tx", "771": "houston_tx", "772": "houston_tx",
    "773": "houston_tx", "774": "houston_tx", "775": "houston_tx",
    # Washington DC metro
    "200": "washington_dc", "201": "washington_dc", "202": "washington_dc",
    "203": "washington_dc", "204": "washington_dc", "205": "washington_dc",
    "206": "washington_dc", "207": "southern_md", "208": "southern_md",
    "209": "silver_spring_md", "210": "baltimore_md", "211": "baltimore_md",
    "212": "baltimore_md", "214": "annapolis_md",
    "220": "northern_va", "221": "northern_va", "222": "arlington_va",
    "223": "alexandria_va",
    # Florida metros
    "320": "jacksonville_fl", "321": "daytona_beach_fl", "322": "jacksonville_fl",
    "323": "tallahassee_fl", "324": "panama_city_fl",
    "325": "pensacola_fl", "326": "jacksonville_fl",
    "327": "orlando_fl", "328": "orlando_fl",
    "329": "melbourne_fl",
    "330": "miami_fl", "331": "miami_fl", "332": "miami_fl",
    "333": "fort_lauderdale_fl", "334": "west_palm_fl",
    "335": "tampa_fl", "336": "st_petersburg_fl", "337": "st_petersburg_fl",
    "338": "lakeland_fl", "339": "fort_myers_fl",
    "341": "naples_fl", "342": "sarasota_fl", "344": "gainesville_fl",
    "346": "tampa_fl",
    # Philadelphia metro
    "190": "philadelphia_pa", "191": "philadelphia_pa", "192": "philadelphia_pa",
    "193": "southeastern_pa", "194": "southeastern_pa",
    "080": "southern_nj", "081": "southern_nj", "083": "southern_nj",
    "085": "trenton_nj",
    # Boston metro
    "020": "boston_ma", "021": "boston_ma", "022": "boston_ma",
    "023": "brockton_ma", "024": "boston_suburbs_ma",
    # San Francisco Bay Area
    "940": "san_francisco_ca", "941": "san_francisco_ca",
    "943": "palo_alto_ca", "944": "san_mateo_ca",
    "945": "oakland_ca", "946": "oakland_ca", "947": "berkeley_ca",
    "948": "richmond_ca", "949": "san_rafael_ca",
    "950": "san_jose_ca", "951": "san_jose_ca",
    # Phoenix metro
    "850": "phoenix_az", "851": "phoenix_az", "852": "phoenix_az",
    "853": "phoenix_az", "855": "globe_az",
    "856": "tucson_az", "857": "tucson_az",
    # Atlanta metro
    "300": "atlanta_ga", "301": "atlanta_ga", "302": "atlanta_ga",
    "303": "atlanta_ga", "304": "swainsboro_ga", "305": "athens_ga",
    "306": "atlanta_suburbs_ga",
    # Detroit metro
    "480": "detroit_mi", "481": "detroit_mi", "482": "detroit_mi",
    "483": "royal_oak_mi", "484": "flint_mi",
    # Seattle metro
    "980": "seattle_wa", "981": "seattle_wa",
    "982": "everett_wa", "983": "tacoma_wa", "984": "tacoma_wa",
    # Minneapolis-St. Paul metro
    "550": "minneapolis_mn", "551": "minneapolis_mn",
    "553": "minneapolis_mn", "554": "minneapolis_mn",
    "555": "minneapolis_mn",
    # San Diego metro
    "919": "san_diego_ca", "920": "san_diego_ca", "921": "san_diego_ca",
    # Denver metro
    "800": "denver_co", "801": "denver_co", "802": "denver_co",
    "803": "denver_co", "804": "denver_co", "805": "longmont_co",
    # St. Louis metro
    "630": "st_louis_mo", "631": "st_louis_mo", "620": "east_st_louis_il",
    # Baltimore metro
    "210": "baltimore_md", "211": "baltimore_md", "212": "baltimore_md",
    # Las Vegas metro
    "889": "las_vegas_nv", "890": "las_vegas_nv", "891": "las_vegas_nv",
    # Portland metro
    "970": "portland_or", "971": "portland_or", "972": "portland_or",
    "973": "salem_or",
    # San Antonio metro
    "780": "san_antonio_tx", "781": "san_antonio_tx", "782": "san_antonio_tx",
    # Austin metro
    "786": "austin_tx", "787": "austin_tx",
    # Nashville metro
    "370": "nashville_tn", "371": "nashville_tn", "372": "nashville_tn",
    # Charlotte metro
    "280": "charlotte_nc", "281": "charlotte_nc", "282": "charlotte_nc",
    # Indianapolis metro
    "460": "indianapolis_in", "461": "indianapolis_in", "462": "indianapolis_in",
    # Columbus metro
    "430": "columbus_oh", "431": "columbus_oh", "432": "columbus_oh",
    # Cleveland metro
    "440": "cleveland_oh", "441": "cleveland_oh", "442": "cleveland_oh",
    "443": "akron_oh", "444": "youngstown_oh",
    # Cincinnati metro
    "450": "cincinnati_oh", "451": "cincinnati_oh", "452": "cincinnati_oh",
    # Kansas City metro
    "640": "kansas_city_mo", "641": "kansas_city_mo",
    "660": "kansas_city_ks", "661": "kansas_city_ks",
    # Milwaukee metro
    "530": "milwaukee_wi", "531": "milwaukee_wi", "532": "milwaukee_wi",
    # Oklahoma City metro
    "730": "oklahoma_city_ok", "731": "oklahoma_city_ok",
    # Raleigh-Durham metro
    "275": "raleigh_nc", "276": "raleigh_nc", "277": "durham_nc",
    # Salt Lake City metro
    "840": "salt_lake_city_ut", "841": "salt_lake_city_ut",
    # Hartford metro
    "060": "hartford_ct", "061": "hartford_ct",
    # Pittsburgh metro
    "150": "pittsburgh_pa", "151": "pittsburgh_pa", "152": "pittsburgh_pa",
    # Memphis metro
    "380": "memphis_tn", "381": "memphis_tn",
    # Richmond metro
    "230": "richmond_va", "231": "richmond_va", "232": "richmond_va",
    # New Orleans metro
    "700": "new_orleans_la", "701": "new_orleans_la",
    # Louisville metro
    "400": "louisville_ky", "401": "louisville_ky", "402": "louisville_ky",
    # Birmingham metro
    "350": "birmingham_al", "351": "birmingham_al", "352": "birmingham_al",
    # Buffalo metro
    "140": "buffalo_ny", "141": "buffalo_ny", "142": "buffalo_ny",
    # Rochester metro
    "144": "rochester_ny", "145": "rochester_ny", "146": "rochester_ny",
    # Providence metro
    "028": "providence_ri", "029": "providence_ri",
    # Honolulu metro
    "967": "honolulu_hi", "968": "honolulu_hi",
}

ZIP3_TO_STATE = {
    # New York
    "100": "NY", "101": "NY", "102": "NY", "103": "NY", "104": "NY",
    "105": "NY", "106": "NY", "107": "NY", "108": "NY",
    "110": "NY", "111": "NY", "112": "NY", "113": "NY", "114": "NY",
    "115": "NY", "116": "NY", "117": "NY",
    "140": "NY", "141": "NY", "142": "NY",
    "144": "NY", "145": "NY", "146": "NY",
    # New Jersey
    "070": "NJ", "071": "NJ", "072": "NJ", "073": "NJ", "074": "NJ",
    "076": "NJ", "077": "NJ", "078": "NJ", "079": "NJ",
    "080": "NJ", "081": "NJ", "083": "NJ", "085": "NJ",
    # California
    "900": "CA", "901": "CA", "902": "CA", "903": "CA", "904": "CA",
    "905": "CA", "906": "CA", "907": "CA", "908": "CA",
    "910": "CA", "911": "CA", "912": "CA", "913": "CA", "914": "CA",
    "915": "CA", "916": "CA", "917": "CA", "918": "CA",
    "919": "CA", "920": "CA", "921": "CA",
    "925": "CA", "926": "CA", "927": "CA", "928": "CA",
    "940": "CA", "941": "CA", "943": "CA", "944": "CA",
    "945": "CA", "946": "CA", "947": "CA", "948": "CA", "949": "CA",
    "950": "CA", "951": "CA",
    # Illinois
    "600": "IL", "601": "IL", "602": "IL", "603": "IL",
    "604": "IL", "605": "IL", "606": "IL", "607": "IL", "608": "IL",
    "620": "IL",
    # Texas
    "750": "TX", "751": "TX", "752": "TX", "753": "TX",
    "760": "TX", "761": "TX", "762": "TX",
    "770": "TX", "771": "TX", "772": "TX", "773": "TX",
    "774": "TX", "775": "TX",
    "780": "TX", "781": "TX", "782": "TX",
    "786": "TX", "787": "TX",
    # DC / Maryland / Virginia
    "200": "DC", "201": "DC", "202": "DC", "203": "DC",
    "204": "DC", "205": "DC", "206": "DC",
    "207": "MD", "208": "MD", "209": "MD",
    "210": "MD", "211": "MD", "212": "MD", "214": "MD",
    "220": "VA", "221": "VA", "222": "VA", "223": "VA",
    "230": "VA", "231": "VA", "232": "VA",
    # Florida
    "320": "FL", "321": "FL", "322": "FL", "323": "FL", "324": "FL",
    "325": "FL", "326": "FL", "327": "FL", "328": "FL", "329": "FL",
    "330": "FL", "331": "FL", "332": "FL", "333": "FL", "334": "FL",
    "335": "FL", "336": "FL", "337": "FL", "338": "FL", "339": "FL",
    "341": "FL", "342": "FL", "344": "FL", "346": "FL",
    # Pennsylvania
    "150": "PA", "151": "PA", "152": "PA",
    "190": "PA", "191": "PA", "192": "PA", "193": "PA", "194": "PA",
    # Massachusetts
    "020": "MA", "021": "MA", "022": "MA", "023": "MA", "024": "MA",
    # Arizona
    "850": "AZ", "851": "AZ", "852": "AZ", "853": "AZ",
    "855": "AZ", "856": "AZ", "857": "AZ",
    # Georgia
    "300": "GA", "301": "GA", "302": "GA", "303": "GA",
    "304": "GA", "305": "GA", "306": "GA",
    # Michigan
    "480": "MI", "481": "MI", "482": "MI", "483": "MI", "484": "MI",
    # Washington
    "980": "WA", "981": "WA", "982": "WA", "983": "WA", "984": "WA",
    # Minnesota
    "550": "MN", "551": "MN", "553": "MN", "554": "MN", "555": "MN",
    # Colorado
    "800": "CO", "801": "CO", "802": "CO", "803": "CO",
    "804": "CO", "805": "CO",
    # Missouri
    "630": "MO", "631": "MO", "640": "MO", "641": "MO",
    # Nevada
    "889": "NV", "890": "NV", "891": "NV",
    # Oregon
    "970": "OR", "971": "OR", "972": "OR", "973": "OR",
    # Tennessee
    "370": "TN", "371": "TN", "372": "TN",
    "380": "TN", "381": "TN",
    # North Carolina
    "275": "NC", "276": "NC", "277": "NC",
    "280": "NC", "281": "NC", "282": "NC",
    # Indiana
    "460": "IN", "461": "IN", "462": "IN",
    # Ohio
    "430": "OH", "431": "OH", "432": "OH",
    "440": "OH", "441": "OH", "442": "OH", "443": "OH", "444": "OH",
    "450": "OH", "451": "OH", "452": "OH",
    # Kansas
    "660": "KS", "661": "KS",
    # Wisconsin
    "530": "WI", "531": "WI", "532": "WI",
    # Oklahoma
    "730": "OK", "731": "OK",
    # Utah
    "840": "UT", "841": "UT",
    # Connecticut
    "060": "CT", "061": "CT",
    # Louisiana
    "700": "LA", "701": "LA",
    # Kentucky
    "400": "KY", "401": "KY", "402": "KY",
    # Alabama
    "350": "AL", "351": "AL", "352": "AL",
    # Rhode Island
    "028": "RI", "029": "RI",
    # Hawaii
    "967": "HI", "968": "HI",
}


def derive_region(zip_code: str) -> tuple[str, str, str]:
    """Returns (region_name, state_code, zip3)."""
    zip3 = zip_code[:3]
    region = ZIP3_TO_REGION.get(zip3, f"region_{zip3}")
    state = ZIP3_TO_STATE.get(zip3, "unknown")
    return region, state, zip3


# ---------------------------------------------------------------------------
# Outlier Detection
# ---------------------------------------------------------------------------

CPT_AMOUNT_RANGES = {
    "99213": (50, 500),
    "99214": (75, 700),
    "99215": (100, 900),
    "99203": (75, 600),
    "99204": (100, 800),
    "99205": (125, 1000),
    "11102": (80, 800),
    "11103": (50, 600),
    "17000": (50, 500),
    "93000": (30, 400),
    "93306": (100, 1500),
    "93307": (80, 1200),
    "27447": (1500, 50000),
    "27130": (1500, 50000),
    "29881": (500, 15000),
    "70553": (200, 5000),
    "73721": (150, 3000),
    "74177": (200, 4000),
    "80053": (10, 300),
    "85025": (5, 150),
    "36415": (3, 50),
}

DEFAULT_RANGE = (1, 100000)


def check_outlier(cpt_code: str, amount: float) -> bool:
    """Returns True if the amount is likely an outlier."""
    low, high = CPT_AMOUNT_RANGES.get(cpt_code, DEFAULT_RANGE)
    return amount < low or amount > high


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------

class ObservationLineItem(BaseModel):
    cpt_code: Optional[str] = None
    amount: Optional[float] = None
    amount_type: str = "billed_amount"
    cpt_confidence: Optional[str] = "medium"
    facility_type: Optional[str] = "unknown"


class SaveObservationsRequest(BaseModel):
    line_items: List[ObservationLineItem]
    insurer: Optional[str] = None
    zip_code: str
    network_status: Optional[str] = "unknown"
    input_method: str
    service_date: Optional[str] = None
    provider_specialty: Optional[str] = None


class SaveObservationsResponse(BaseModel):
    saved: int
    message: str


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post("/benchmark-observations", response_model=SaveObservationsResponse)
async def save_benchmark_observations(req: SaveObservationsRequest):
    """Anonymize and store benchmark observations from a completed bill analysis."""
    # Normalize insurer
    if req.insurer:
        insurer_normalized, insurer_raw = normalize_insurer(req.insurer)
    else:
        insurer_normalized, insurer_raw = "unknown", None

    # Derive region from ZIP
    region, state_code, zip3 = derive_region(req.zip_code)

    # Only store month/year
    service_month = req.service_date[:7] if req.service_date and len(req.service_date) >= 7 else None

    # Infer specialty if not provided
    provider_specialty = req.provider_specialty
    if not provider_specialty:
        cpt_codes = [item.cpt_code for item in req.line_items if item.cpt_code]
        provider_specialty = infer_specialty(cpt_codes)

    observations = []
    for item in req.line_items:
        if not item.cpt_code or item.amount is None:
            continue

        amount = float(item.amount)
        is_outlier = check_outlier(item.cpt_code, amount)

        # Determine confidence
        confidence = item.cpt_confidence or "medium"
        if confidence == "inferred":
            confidence = "low"
        if is_outlier:
            confidence = "low"

        observations.append({
            "cpt_code": item.cpt_code,
            "amount": amount,
            "amount_type": item.amount_type,
            "insurer": insurer_normalized,
            "insurer_raw": insurer_raw,
            "region": region,
            "state_code": state_code,
            "zip3": zip3,
            "provider_specialty": provider_specialty,
            "network_status": req.network_status or "unknown",
            "facility_type": item.facility_type or "unknown",
            "service_month": service_month,
            "confidence": confidence,
            "input_method": req.input_method,
            "is_outlier": is_outlier,
        })

    if observations:
        try:
            sb = _get_supabase()
            sb.table("benchmark_observations").insert(observations).execute()
        except Exception as exc:
            # Fire-and-forget pattern — log but don't fail the user's request
            print(f"WARNING: Failed to save benchmark observations: {exc}")
            return SaveObservationsResponse(saved=0, message="Observations could not be saved.")

    return SaveObservationsResponse(
        saved=len(observations),
        message=f"{len(observations)} anonymized observation(s) added to benchmark database.",
    )
