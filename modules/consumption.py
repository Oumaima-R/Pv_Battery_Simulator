"""
Module d'analyse de la consommation électrique
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple

class ConsumptionAnalyzer:
    """Analyse de la consommation résidentielle"""
    
    def __init__(self, annual_consumption_kwh: float):
        self.annual_consumption = annual_consumption_kwh
        self.daily_consumption = annual_consumption_kwh / 365
        self.avg_power_w = (self.daily_consumption / 24) * 1000
        
    def calculate_load_profile(self, profile_24h: List[float]) -> Dict:
        """
        Calcule le profil de charge complet à partir d'un profil 24h
        
        Args:
            profile_24h: Liste de 24 valeurs de puissance en kW
            
        Returns:
            Dict avec les résultats
        """
        # Vérifier la longueur
        if len(profile_24h) != 24:
            raise ValueError("Le profil doit contenir 24 valeurs (une par heure)")
        
        # Créer le profil annuel (8760 heures)
        yearly_profile = np.tile(profile_24h, 365)
        
        # Calculer l'énergie quotidienne du profil
        daily_energy_profile = sum(profile_24h)  # kWh/j (puisque pas = 1h)
        
        # Facteur d'ajustement pour correspondre à la consommation annuelle
        scaling_factor = self.daily_consumption / daily_energy_profile
        
        # Ajuster le profil
        adjusted_profile = [p * scaling_factor for p in profile_24h]
        adjusted_yearly = np.tile(adjusted_profile, 365)
        
        # Séparer jour/nuit (jour: 6h-22h, nuit: 22h-6h)
        day_hours = list(range(6, 22))
        night_hours = [h for h in range(24) if h not in day_hours]
        
        # Calculer les énergies jour/nuit
        day_energy = sum([adjusted_profile[h] for h in day_hours])
        night_energy = sum([adjusted_profile[h] for h in night_hours])
        
        day_percentage = (day_energy / self.daily_consumption) * 100
        night_percentage = (night_energy / self.daily_consumption) * 100
        
        # Trouver les pics
        peak_power = max(adjusted_profile)
        peak_hour = adjusted_profile.index(peak_power)
        
        return {
            "hourly_profile": adjusted_profile,
            "yearly_profile": adjusted_yearly.tolist(),
            "daily_energy_kwh": self.daily_consumption,
            "day_energy_kwh": day_energy,
            "night_energy_kwh": night_energy,
            "day_percentage": day_percentage,
            "night_percentage": night_percentage,
            "peak_power_kw": peak_power,
            "peak_hour": peak_hour,
            "avg_power_w": self.avg_power_w,
        }
    
    def analyze_room_consumption(self, room_data: Dict[str, float]) -> pd.DataFrame:
        """
        Analyse la consommation par pièce
        
        Args:
            room_data: Dict {nom_piece: consommation_kwh}
            
        Returns:
            DataFrame avec l'analyse
        """
        df = pd.DataFrame.from_dict(room_data, orient='index', columns=['Consommation (kWh)'])
        df['Pourcentage'] = (df['Consommation (kWh)'] / self.annual_consumption) * 100
        df = df.sort_values('Consommation (kWh)', ascending=False)
        
        return df
    
    def calculate_time_distribution(self) -> Dict[str, float]:
        """
        Calcule la répartition temporelle de la consommation
        Basé sur les données du rapport
        """
        return {
            "Eau chaude et chauffage": {"jour": 980.0, "nuit": 1320.0, "total": 2300.0},
            "Cuisson": {"jour": 639.0, "nuit": 66.0, "total": 705.0},
            "Multimédia/bureautique": {"jour": 506.9, "nuit": 355.1, "total": 862.0},
            "Froid et lavage": {"jour": 385.0, "nuit": 325.0, "total": 710.0},
            "Éclairage": {"jour": 112.0, "nuit": 168.0, "total": 280.0},
            "Divers": {"jour": 277.0, "nuit": -80.7, "total": 196.3},
        }