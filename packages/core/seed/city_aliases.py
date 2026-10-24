# Normalization lookup for Indian and global employment locations
CITY_ALIASES: dict[str, str] = {
    # Bangalore
    "bangalore": "Bengaluru",
    "bengaluru": "Bengaluru",
    "blr": "Bengaluru",
    "bengaluru, karnataka": "Bengaluru",
    "bangalore urban": "Bengaluru",
    "electronic city": "Bengaluru",
    "whitefield": "Bengaluru",
    # Mumbai
    "mumbai": "Mumbai",
    "bombay": "Mumbai",
    "navi mumbai": "Mumbai",
    "thane": "Mumbai",
    "mumbai city": "Mumbai",
    "mumbai suburban": "Mumbai",
    # Delhi NCR
    "delhi": "Delhi NCR",
    "new delhi": "Delhi NCR",
    "gurgaon": "Gurugram",
    "gurugram": "Gurugram",
    "noida": "Noida",
    "greater noida": "Noida",
    "faridabad": "Delhi NCR",
    "ghaziabad": "Delhi NCR",
    # Hyderabad
    "hyderabad": "Hyderabad",
    "secunderabad": "Hyderabad",
    "cyberabad": "Hyderabad",
    "gachibowli": "Hyderabad",
    "hitec city": "Hyderabad",
    # Pune
    "pune": "Pune",
    "poona": "Pune",
    "hinjewadi": "Pune",
    # Chennai
    "chennai": "Chennai",
    "madras": "Chennai",
    # Kolkata
    "kolkata": "Kolkata",
    "calcutta": "Kolkata",
    "salt lake": "Kolkata",
    "new town": "Kolkata",
    # Ahmedabad
    "ahmedabad": "Ahmedabad",
    "gandhinagar": "Gandhinagar",
    # Other tech hubs
    "kochi": "Kochi",
    "cochin": "Kochi",
    "trivandrum": "Thiruvananthapuram",
    "thiruvananthapuram": "Thiruvananthapuram",
    "coimbatore": "Coimbatore",
    "indore": "Indore",
    "jaipur": "Jaipur",
    "chandigarh": "Chandigarh",
    "mohali": "Mohali",
    "bhubaneswar": "Bhubaneswar",
    "nagpur": "Nagpur",
    "vadodara": "Vadodara",
    "baroda": "Vadodara",
    "surat": "Surat",
    # Remote variations
    "remote": "Remote",
    "anywhere in india": "Remote",
    "work from home": "Remote",
    "wfh": "Remote",
}


def normalize_city(raw_city: str) -> str:
    """Normalize a city string into its standard canonical format."""
    clean = raw_city.strip().lower()
    return CITY_ALIASES.get(clean, raw_city.strip().title())
