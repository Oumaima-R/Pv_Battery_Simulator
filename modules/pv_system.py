"""
Module de dimensionnement du système PV
"""

import numpy as np
from typing import Dict, Tuple

class PVSystem:
    """Système photovoltaïque"""
    
    def __init__(self, city: str, irradiation: float):
        self.city = city
        self.irradiation = irradiation  # kWh/m²
        
    def calculate_pv_production(self, pv_power_kw: float, pr: float) -> Dict:
        """
        Calcule la production PV
        
        Args:
            pv_power_kw: Puissance crête en kW
            pr: Performance Ratio (0-100%)
            
        Returns:
            Dict avec les résultats
        """
        # Production annuelle
        annual_production = pv_power_kw * self.irradiation * (pr / 100)
        
        # Production mensuelle (simplifiée)
        monthly_factors = {
            "Jan": 0.08, "Feb": 0.09, "Mar": 0.10,
            "Apr": 0.11, "May": 0.12, "Jun": 0.12,
            "Jul": 0.12, "Aug": 0.11, "Sep": 0.10,
            "Oct": 0.09, "Nov": 0.08, "Dec": 0.07
        }
        
        monthly_production = {
            month: annual_production * factor 
            for month, factor in monthly_factors.items()
        }
        
        # Profil horaire de production (gaussien centré sur midi)
        hours = list(range(24))
        # Courbe gaussienne pour la production journalière
        production_hourly = []
        for h in hours:
            # Production maximale à 13h
            production = np.exp(-((h - 13) ** 2) / (2 * 4))  # Variance 4
            production_hourly.append(production)
        
        # Normaliser pour que la somme = production journalière
        daily_production = annual_production / 365
        sum_prod = sum(production_hourly)
        production_hourly = [p * daily_production / sum_prod for p in production_hourly]
        
        return {
            "annual_production_kwh": annual_production,
            "monthly_production": monthly_production,
            "hourly_profile": production_hourly,
            "capacity_factor": (annual_production / (pv_power_kw * 8760)) * 100,
        }
    
    def size_for_coverage(self, consumption_kwh: float, target_coverage: float, pr: float) -> Dict:
        """
        Dimensionne le PV pour un taux de couverture donné
        
        Args:
            consumption_kwh: Consommation annuelle
            target_coverage: Taux de couverture cible (0-100%)
            pr: Performance Ratio
            
        Returns:
            Dict avec dimensionnement
        """
        # Énergie PV nécessaire
        required_pv_energy = consumption_kwh * (target_coverage / 100)
        
        # Puissance crête nécessaire
        required_power = required_pv_energy / (self.irradiation * (pr / 100))
        
        # Arrondir à la puissance commerciale supérieure
        commercial_powers = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
        installed_power = min(commercial_powers, key=lambda x: abs(x - required_power))
        
        # Production réelle avec la puissance installée
        actual_production = installed_power * self.irradiation * (pr / 100)
        actual_coverage = (actual_production / consumption_kwh) * 100
        
        # Surface nécessaire (rendement 20%)
        module_area = installed_power / (1 * 0.20)  # kW / (kW/m² * rendement)
        
        return {
            "required_power_kw": required_power,
            "installed_power_kw": installed_power,
            "required_energy_kwh": required_pv_energy,
            "actual_production_kwh": actual_production,
            "actual_coverage_percent": actual_coverage,
            "module_area_m2": module_area,
            "performance_ratio": pr,
        }