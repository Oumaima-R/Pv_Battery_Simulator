"""
Configuration de l'application PV+Battery Simulator
"""

# Paramètres par défaut du projet
DEFAULT_PARAMS = {
    "annual_consumption": 4479.3,  # kWh/an
    "pv_power": 2.5,  # kWc
    "pv_pr": 75,  # Performance Ratio %
    "battery_capacity_li": 5.5,  # kWh
    "battery_capacity_pb": 10.0,  # kWh
    "dod_li": 85,  # Depth of Discharge %
    "dod_pb": 50,  # Depth of Discharge %
    "efficiency_li": 95,  # %
    "efficiency_pb": 85,  # %
    "irradiation_rabat": 1900,  # kWh/m²
}

# Profil de charge horaire par défaut (24h)
DEFAULT_LOAD_PROFILE = [
    0.205, 0.205, 0.205, 0.205, 0.205, 0.205,  # 00-06h
    0.925, 0.925,  # 06-08h
    0.308, 0.308, 0.308, 0.308,  # 08-12h
    0.925, 0.925,  # 12-14h
    0.308, 0.308, 0.308, 0.308,  # 14-18h
    1.078, 1.078, 1.078, 1.078,  # 18-22h
    0.310, 0.310  # 22-00h
]

# Données d'irradiation pour différentes villes (kWh/m²)
CITIES_IRRADIATION = {
    "Rabat": 1900,
    "Casablanca": 1850,
    "Marrakech": 2100,
    "Fès": 1950,
    "Tanger": 1800,
    "Agadir": 2200,
    "Oujda": 2000,
    "Meknès": 1920,
}

# Paramètres technologiques
BATTERY_TECHNOLOGIES = {
    "Lithium-ion": {
        "dod_range": (80, 95),
        "efficiency_range": (90, 98),
        "lifetime_years": 10,
        "cycles": 4000,
        "cost_per_kwh": 500,  # $/kWh
    },
    "Plomb-acide": {
        "dod_range": (40, 60),
        "efficiency_range": (80, 90),
        "lifetime_years": 5,
        "cycles": 800,
        "cost_per_kwh": 200,  # $/kWh
    }
}

# Scénarios à simuler
SCENARIOS = {
    0: {"name": "Scénario 0", "description": "Réseau seul (référence)", "pv": False, "battery": None},
    1: {"name": "Scénario 1", "description": "PV seul + réseau", "pv": True, "battery": None},
    2: {"name": "Scénario 2", "description": "PV + Batterie Plomb-acide", "pv": True, "battery": "Plomb-acide"},
    3: {"name": "Scénario 3", "description": "PV + Batterie Lithium-ion", "pv": True, "battery": "Lithium-ion"},
    4: {"name": "Scénario 4", "description": "Configuration optimisée", "pv": True, "battery": "Lithium-ion", "optimized": True},
}