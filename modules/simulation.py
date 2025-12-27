"""
Module principal de simulation des scénarios
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any
from datetime import datetime

from modules.consumption import ConsumptionAnalyzer
from modules.pv_system import PVSystem
from modules.battery_system import BatterySystem

class ScenarioSimulator:
    """Simulateur des différents scénarios"""
    
    def __init__(self, 
                 annual_consumption: float,
                 city: str,
                 irradiation: float,
                 load_profile_24h: List[float]):
        
        self.annual_consumption = annual_consumption
        self.city = city
        self.irradiation = irradiation
        self.load_profile_24h = load_profile_24h
        
        # Initialiser les analyseurs
        self.consumption_analyzer = ConsumptionAnalyzer(annual_consumption)
        self.pv_system = PVSystem(city, irradiation)
        
        # Analyser la consommation
        self.consumption_data = self.consumption_analyzer.calculate_load_profile(load_profile_24h)
        
    def simulate_scenario_0(self) -> Dict:
        """Scénario 0: Réseau seul"""
        return {
            "scenario_name": "Scénario 0 - Réseau seul",
            "description": "Consommation 100% réseau",
            "annual_consumption_kwh": self.annual_consumption,
            "annual_grid_import_kwh": self.annual_consumption,
            "annual_grid_export_kwh": 0,
            "pv_production_kwh": 0,
            "battery_charge_kwh": 0,
            "battery_discharge_kwh": 0,
            "self_consumption_percent": 0,
            "grid_reduction_percent": 0,
            "energy_cost_usd": self.annual_consumption * 0.15,  # 0.15 $/kWh
        }
    
    def simulate_scenario_1(self, pv_power_kw: float, pv_pr: float) -> Dict:
        """Scénario 1: PV seul"""
        # Production PV
        pv_data = self.pv_system.calculate_pv_production(pv_power_kw, pv_pr)
        pv_production = pv_data["annual_production_kwh"]
        
        # Consommation sur le réseau
        grid_import = max(0, self.annual_consumption - pv_production)
        
        # Injection au réseau (simplifiée)
        grid_export = max(0, pv_production - self.annual_consumption) * 0.3  # 30% d'injection
        
        # Taux d'autoconsommation estimé
        self_consumption = min(pv_production, self.annual_consumption)
        self_consumption_rate = (self_consumption / pv_production * 100) if pv_production > 0 else 0
        
        # Réduction appel réseau
        grid_reduction = ((self.annual_consumption - grid_import) / self.annual_consumption) * 100
        
        return {
            "scenario_name": "Scénario 1 - PV seul",
            "description": f"PV {pv_power_kw} kW + réseau",
            "annual_consumption_kwh": self.annual_consumption,
            "annual_grid_import_kwh": grid_import,
            "annual_grid_export_kwh": grid_export,
            "pv_production_kwh": pv_production,
            "pv_power_kw": pv_power_kw,
            "pv_pr_percent": pv_pr,
            "battery_charge_kwh": 0,
            "battery_discharge_kwh": 0,
            "self_consumption_percent": self_consumption_rate,
            "grid_reduction_percent": grid_reduction,
            "pv_coverage_percent": (pv_production / self.annual_consumption) * 100,
            "energy_cost_usd": grid_import * 0.15 - grid_export * 0.08,  # Achat 0.15, vente 0.08
        }
    
    def simulate_scenario_2(self, 
                           pv_power_kw: float, 
                           pv_pr: float,
                           battery_tech: str = "Plomb-acide") -> Dict:
        """Scénario 2: PV + Batterie plomb-acide"""
        # Production PV
        pv_data = self.pv_system.calculate_pv_production(pv_power_kw, pv_pr)
        pv_production = pv_data["annual_production_kwh"]
        
        # Dimensionnement batterie
        battery = BatterySystem(battery_tech)
        night_energy = self.consumption_data["night_energy_kwh"] * 365  # Annuel
        avg_power = self.consumption_data["avg_power_w"] / 1000  # kW
        
        # Taille batterie pour 8h d'autonomie
        battery_size = battery.calculate_battery_size(
            night_energy_kwh=night_energy/365,  # Journalier
            autonomy_hours=8,
            avg_power_kw=avg_power
        )
        
        # Simulation journalière simplifiée
        daily_sim = battery.simulate_daily_operation(
            load_profile=self.consumption_data["hourly_profile"],
            pv_profile=pv_data["hourly_profile"],
            battery_capacity_kwh=battery_size["selected_capacity_kwh"]
        )
        
        # Annualiser les résultats
        annual_grid_import = daily_sim["grid_import_kwh"] * 365
        annual_grid_export = daily_sim["grid_export_kwh"] * 365
        annual_battery_charge = daily_sim["battery_charge_kwh"] * 365
        annual_battery_discharge = daily_sim["battery_discharge_kwh"] * 365
        
        # Calcul indicateurs
        grid_reduction = ((self.annual_consumption - annual_grid_import) / self.annual_consumption) * 100
        total_coverage = ((pv_production + annual_battery_discharge) / self.annual_consumption) * 100
        
        return {
            "scenario_name": f"Scénario 2 - PV + {battery_tech}",
            "description": f"PV {pv_power_kw} kW + {battery_tech} + réseau",
            "annual_consumption_kwh": self.annual_consumption,
            "annual_grid_import_kwh": annual_grid_import,
            "annual_grid_export_kwh": annual_grid_export,
            "pv_production_kwh": pv_production,
            "pv_power_kw": pv_power_kw,
            "battery_technology": battery_tech,
            "battery_capacity_kwh": battery_size["selected_capacity_kwh"],
            "battery_usable_kwh": battery_size["usable_capacity_kwh"],
            "annual_battery_charge_kwh": annual_battery_charge,
            "annual_battery_discharge_kwh": annual_battery_discharge,
            "self_consumption_percent": daily_sim["self_consumption_percent"],
            "grid_reduction_percent": grid_reduction,
            "total_coverage_percent": total_coverage,
            "battery_autonomy_hours": battery_size["autonomy_hours"],
            "battery_night_coverage": battery_size["night_coverage_percent"],
            "energy_cost_usd": annual_grid_import * 0.15 - annual_grid_export * 0.08,
            "battery_cost_usd": battery_size["estimated_cost_usd"],
        }
    
    def simulate_scenario_3(self, pv_power_kw: float, pv_pr: float) -> Dict:
        """Scénario 3: PV + Batterie lithium-ion"""
        return self.simulate_scenario_2(pv_power_kw, pv_pr, "Lithium-ion")
    
    def simulate_scenario_4(self, 
                           target_coverage: float = 80,
                           pv_pr: float = 75) -> Dict:
        """Scénario 4: Configuration optimisée"""
        # Dimensionnement PV optimisé
        pv_sizing = self.pv_system.size_for_coverage(
            consumption_kwh=self.annual_consumption,
            target_coverage=target_coverage,
            pr=pv_pr
        )
        
        pv_power = pv_sizing["installed_power_kw"]
        pv_production = pv_sizing["actual_production_kwh"]
        
        # Dimensionnement batterie optimisé (lithium-ion)
        battery = BatterySystem("Lithium-ion")
        night_energy = self.consumption_data["night_energy_kwh"]
        avg_power = self.consumption_data["avg_power_w"] / 1000
        
        # Calculer l'autonomie nécessaire pour couvrir la nuit
        required_autonomy = night_energy / avg_power if avg_power > 0 else 0
        
        battery_size = battery.calculate_battery_size(
            night_energy_kwh=night_energy,
            autonomy_hours=required_autonomy,
            avg_power_kw=avg_power
        )
        
        # Simulation
        pv_data = self.pv_system.calculate_pv_production(pv_power, pv_pr)
        daily_sim = battery.simulate_daily_operation(
            load_profile=self.consumption_data["hourly_profile"],
            pv_profile=pv_data["hourly_profile"],
            battery_capacity_kwh=battery_size["selected_capacity_kwh"]
        )
        
        # Annualiser
        annual_grid_import = daily_sim["grid_import_kwh"] * 365
        annual_grid_export = daily_sim["grid_export_kwh"] * 365
        
        return {
            "scenario_name": "Scénario 4 - Configuration optimisée",
            "description": f"PV {pv_power:.1f} kW + Li-ion {battery_size['selected_capacity_kwh']:.1f} kWh optimisés",
            "annual_consumption_kwh": self.annual_consumption,
            "annual_grid_import_kwh": annual_grid_import,
            "annual_grid_export_kwh": annual_grid_export,
            "pv_production_kwh": pv_production,
            "pv_power_kw": pv_power,
            "pv_coverage_percent": pv_sizing["actual_coverage_percent"],
            "battery_technology": "Lithium-ion",
            "battery_capacity_kwh": battery_size["selected_capacity_kwh"],
            "battery_usable_kwh": battery_size["usable_capacity_kwh"],
            "self_consumption_percent": daily_sim["self_consumption_percent"],
            "grid_reduction_percent": ((self.annual_consumption - annual_grid_import) / self.annual_consumption) * 100,
            "total_coverage_percent": ((pv_production + battery_size["usable_capacity_kwh"] * 365) / self.annual_consumption) * 100,
            "optimization_criteria": f"Couverture {target_coverage}% + autonomie nuit",
        }
    
    def simulate_all_scenarios(self, 
                              pv_power_kw: float = 2.5,
                              pv_pr: float = 75) -> Dict[int, Dict]:
        """Simule tous les scénarios"""
        scenarios = {}
        
        scenarios[0] = self.simulate_scenario_0()
        scenarios[1] = self.simulate_scenario_1(pv_power_kw, pv_pr)
        scenarios[2] = self.simulate_scenario_2(pv_power_kw, pv_pr, "Plomb-acide")
        scenarios[3] = self.simulate_scenario_3(pv_power_kw, pv_pr)
        scenarios[4] = self.simulate_scenario_4(target_coverage=80, pv_pr=pv_pr)
        
        return scenarios
    
    def generate_comparison_table(self, scenarios: Dict[int, Dict]) -> pd.DataFrame:
        """Génère un tableau de comparaison des scénarios"""
        data = []
        for scenario_id, results in scenarios.items():
            data.append({
                "Scénario": results["scenario_name"],
                "Description": results["description"],
                "Consommation (kWh/an)": results["annual_consumption_kwh"],
                "Production PV (kWh/an)": results.get("pv_production_kwh", 0),
                "Importation réseau (kWh/an)": results["annual_grid_import_kwh"],
                "Exportation réseau (kWh/an)": results.get("annual_grid_export_kwh", 0),
                "Autoconsommation (%)": results.get("self_consumption_percent", 0),
                "Réduction réseau (%)": results.get("grid_reduction_percent", 0),
                "Couverture totale (%)": results.get("total_coverage_percent", 
                                                   results.get("pv_coverage_percent", 0)),
                "Coût énergie (USD/an)": results.get("energy_cost_usd", 0),
            })
        
        return pd.DataFrame(data)