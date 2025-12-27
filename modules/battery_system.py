"""
Module de dimensionnement du système de batterie
"""

from typing import Dict, List
import numpy as np

class BatterySystem:
    """Système de stockage par batterie"""
    
    def __init__(self, technology: str):
        self.technology = technology
        self.set_parameters()
        
    def set_parameters(self):
        """Définit les paramètres selon la technologie"""
        if self.technology == "Lithium-ion":
            self.dod = 0.85  # Depth of Discharge
            self.efficiency = 0.95  # Rendement aller-retour
            self.lifetime_years = 10
            self.cycles = 4000
            self.cost_per_kwh = 500  # $/kWh
        elif self.technology == "Plomb-acide":
            self.dod = 0.50
            self.efficiency = 0.85
            self.lifetime_years = 5
            self.cycles = 800
            self.cost_per_kwh = 200
        else:
            raise ValueError(f"Technologie non supportée: {self.technology}")
    
    def calculate_battery_size(self, 
                             night_energy_kwh: float,
                             autonomy_hours: float = None,
                             avg_power_kw: float = None) -> Dict:
        """
        Calcule la taille de la batterie
        
        Args:
            night_energy_kwh: Besoin énergétique nocturne
            autonomy_hours: Autonomie souhaitée (heures)
            avg_power_kw: Puissance moyenne
            
        Returns:
            Dict avec dimensionnement
        """
        if autonomy_hours is not None and avg_power_kw is not None:
            # Calcul basé sur l'autonomie
            energy_to_store = avg_power_kw * autonomy_hours
        else:
            # Calcul basé sur le besoin nocturne
            energy_to_store = night_energy_kwh
        
        # Capacité nominale nécessaire
        nominal_capacity = energy_to_store / (self.dod * self.efficiency)
        
        # Capacité utilisable
        usable_capacity = nominal_capacity * self.dod * self.efficiency
        
        # Arrondir à une capacité commerciale
        commercial_capacities = {
            "Lithium-ion": [2.0, 3.0, 4.0, 5.0, 5.5, 6.0, 7.0, 8.0, 9.0, 10.0],
            "Plomb-acide": [5.0, 6.0, 8.0, 10.0, 12.0, 15.0, 20.0]
        }
        
        selected_capacity = min(commercial_capacities[self.technology], 
                               key=lambda x: abs(x - nominal_capacity))
        
        # Capacité utilisable réelle
        actual_usable = selected_capacity * self.dod * self.efficiency
        
        # Autonomie réelle
        if avg_power_kw:
            actual_autonomy = actual_usable / avg_power_kw if avg_power_kw > 0 else 0
        else:
            actual_autonomy = None
        
        # Couverture du besoin nocturne
        night_coverage = (actual_usable / night_energy_kwh) * 100 if night_energy_kwh > 0 else 0
        
        # Coût estimé
        estimated_cost = selected_capacity * self.cost_per_kwh
        
        return {
            "technology": self.technology,
            "required_capacity_kwh": nominal_capacity,
            "selected_capacity_kwh": selected_capacity,
            "usable_capacity_kwh": actual_usable,
            "dod": self.dod * 100,
            "efficiency": self.efficiency * 100,
            "autonomy_hours": actual_autonomy,
            "night_coverage_percent": night_coverage,
            "estimated_cost_usd": estimated_cost,
            "lifetime_years": self.lifetime_years,
            "cycles": self.cycles,
        }
    
    def simulate_daily_operation(self, 
                               load_profile: List[float],
                               pv_profile: List[float],
                               battery_capacity_kwh: float) -> Dict:
        """
        Simule l'opération journalière de la batterie
        
        Args:
            load_profile: Profil de charge horaire (24h)
            pv_profile: Profil de production PV horaire (24h)
            battery_capacity_kwh: Capacité de la batterie
            
        Returns:
            Dict avec résultats de simulation
        """
        soc = battery_capacity_kwh * self.dod * 0.5  # SOC initial à 50% de l'utilisable
        usable_capacity = battery_capacity_kwh * self.dod
        
        grid_import = []
        grid_export = []
        battery_soc = []
        battery_charge = []
        battery_discharge = []
        self_consumption = []
        
        for hour in range(24):
            load = load_profile[hour]
            pv = pv_profile[hour]
            
            # Énergie nette
            net_energy = pv - load
            
            if net_energy > 0:
                # Excédent PV
                # Essayer de charger la batterie
                charge_possible = min(net_energy, 
                                    (usable_capacity - soc) / self.efficiency)
                if charge_possible > 0:
                    soc += charge_possible * self.efficiency
                    battery_charge.append(charge_possible)
                    battery_discharge.append(0)
                    remaining_excess = net_energy - charge_possible
                else:
                    remaining_excess = net_energy
                    battery_charge.append(0)
                    battery_discharge.append(0)
                
                # Injecter l'excédent au réseau
                grid_export.append(remaining_excess)
                grid_import.append(0)
                
            else:
                # Déficit énergétique
                deficit = -net_energy
                
                # Essayer de décharger la batterie
                discharge_possible = min(deficit, soc * self.efficiency)
                if discharge_possible > 0:
                    soc -= discharge_possible / self.efficiency
                    battery_discharge.append(discharge_possible)
                    battery_charge.append(0)
                    remaining_deficit = deficit - discharge_possible
                else:
                    remaining_deficit = deficit
                    battery_discharge.append(0)
                    battery_charge.append(0)
                
                # Importer du réseau
                grid_import.append(remaining_deficit)
                grid_export.append(0)
            
            battery_soc.append(soc)
            
            # Calcul autoconsommation
            if pv > 0:
                self_cons = min(pv, load + (battery_charge[-1] if battery_charge[-1] > 0 else 0))
                self_consumption.append(self_cons / pv * 100)
            else:
                self_consumption.append(0)
        
        total_self_consumption = sum(self_consumption) / 24 if any(self_consumption) else 0
        
        return {
            "grid_import_kwh": sum(grid_import),
            "grid_export_kwh": sum(grid_export),
            "battery_charge_kwh": sum(battery_charge),
            "battery_discharge_kwh": sum(battery_discharge),
            "self_consumption_percent": total_self_consumption,
            "hourly_soc": battery_soc,
            "hourly_import": grid_import,
            "hourly_export": grid_export,
        }