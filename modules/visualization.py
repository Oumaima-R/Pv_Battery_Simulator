"""
Module de visualisation des résultats
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import Dict, List, Any

class Visualization:
    """Classe pour créer des visualisations"""
    
    @staticmethod
    def create_load_shape_chart(hourly_profile: List[float], 
                               title: str = "Profil de Charge Journalier") -> go.Figure:
        """Crée un graphique du profil de charge"""
        hours = list(range(24))
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=hours,
            y=hourly_profile,
            mode='lines+markers',
            name='Puissance (kW)',
            line=dict(color='blue', width=3),
            fill='tozeroy',
            fillcolor='rgba(0, 100, 255, 0.2)'
        ))
        
        fig.update_layout(
            title=dict(text=title, x=0.5, xanchor='center'),
            xaxis_title="Heure de la journée",
            yaxis_title="Puissance (kW)",
            template="plotly_white",
            hovermode="x unified",
            showlegend=True
        )
        
        # Ajouter des zones jour/nuit
        fig.add_vrect(x0=6, x1=22, 
                     fillcolor="rgba(255, 255, 0, 0.1)", 
                     line_width=0,
                     annotation_text="Jour", 
                     annotation_position="top left")
        
        fig.add_vrect(x0=22, x1=24, 
                     fillcolor="rgba(0, 0, 0, 0.1)", 
                     line_width=0,
                     annotation_text="Nuit", 
                     annotation_position="top left")
        
        fig.add_vrect(x0=0, x1=6, 
                     fillcolor="rgba(0, 0, 0, 0.1)", 
                     line_width=0)
        
        return fig
    
    @staticmethod
    def create_energy_flow_chart(scenario_results: Dict) -> go.Figure:
        """Crée un diagramme de Sankey des flux énergétiques"""
        
        # Définir les nœuds
        nodes = ["PV", "Réseau", "Batterie", "Maison", "Export", "Pertes"]
        
        # Définir les liens (source, target, value)
        links = {
            "source": [],
            "target": [],
            "value": [],
            "color": []
        }
        
        # Flux du PV
        pv_production = scenario_results.get("pv_production_kwh", 0)
        if pv_production > 0:
            # PV -> Maison (autoconsommation)
            self_cons = pv_production * scenario_results.get("self_consumption_percent", 50) / 100
            links["source"].append(0)  # PV
            links["target"].append(3)  # Maison
            links["value"].append(self_cons)
            links["color"].append("rgba(255, 165, 0, 0.6)")
            
            # PV -> Batterie (charge)
            battery_charge = scenario_results.get("annual_battery_charge_kwh", 0)
            if battery_charge > 0:
                links["source"].append(0)  # PV
                links["target"].append(2)  # Batterie
                links["value"].append(battery_charge)
                links["color"].append("rgba(255, 165, 0, 0.4)")
            
            # PV -> Export
            grid_export = scenario_results.get("annual_grid_export_kwh", 0)
            if grid_export > 0:
                links["source"].append(0)  # PV
                links["target"].append(4)  # Export
                links["value"].append(grid_export)
                links["color"].append("rgba(255, 165, 0, 0.3)")
        
        # Flux batterie
        battery_discharge = scenario_results.get("annual_battery_discharge_kwh", 0)
        if battery_discharge > 0:
            links["source"].append(2)  # Batterie
            links["target"].append(3)  # Maison
            links["value"].append(battery_discharge)
            links["color"].append("rgba(0, 150, 0, 0.6)")
        
        # Flux réseau
        grid_import = scenario_results.get("annual_grid_import_kwh", 0)
        if grid_import > 0:
            links["source"].append(1)  # Réseau
            links["target"].append(3)  # Maison
            links["value"].append(grid_import)
            links["color"].append("rgba(100, 100, 100, 0.6)")
        
        # Créer la figure Sankey
        fig = go.Figure(data=[go.Sankey(
            node=dict(
                pad=15,
                thickness=20,
                line=dict(color="black", width=0.5),
                label=nodes,
                color=["orange", "gray", "green", "blue", "red", "black"]
            ),
            link=dict(
                source=links["source"],
                target=links["target"],
                value=links["value"],
                color=links["color"]
            )
        )])
        
        fig.update_layout(
            title_text=f"Flux Énergétiques - {scenario_results.get('scenario_name', 'Scénario')}",
            font_size=12,
            height=500
        )
        
        return fig
    
    @staticmethod
    def create_scenario_comparison_chart(scenarios_df: pd.DataFrame) -> go.Figure:
        """Crée un graphique de comparaison des scénarios"""
        
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=("Importation Réseau", "Autoconsommation", 
                          "Réduction Réseau", "Couverture Énergétique"),
            vertical_spacing=0.15,
            horizontal_spacing=0.15
        )
        
        # Graphique 1: Importation réseau
        fig.add_trace(
            go.Bar(
                x=scenarios_df["Scénario"],
                y=scenarios_df["Importation réseau (kWh/an)"],
                name="Importation",
                marker_color="red"
            ),
            row=1, col=1
        )
        
        # Graphique 2: Autoconsommation
        fig.add_trace(
            go.Bar(
                x=scenarios_df["Scénario"],
                y=scenarios_df["Autoconsommation (%)"],
                name="Autoconsommation",
                marker_color="blue"
            ),
            row=1, col=2
        )
        
        # Graphique 3: Réduction réseau
        fig.add_trace(
            go.Bar(
                x=scenarios_df["Scénario"],
                y=scenarios_df["Réduction réseau (%)"],
                name="Réduction",
                marker_color="green"
            ),
            row=2, col=1
        )
        
        # Graphique 4: Couverture énergétique
        fig.add_trace(
            go.Bar(
                x=scenarios_df["Scénario"],
                y=scenarios_df["Couverture totale (%)"],
                name="Couverture",
                marker_color="orange"
            ),
            row=2, col=2
        )
        
        fig.update_layout(
            title_text="Comparaison des Scénarios",
            showlegend=False,
            height=700,
            template="plotly_white"
        )
        
        # Mise à jour des axes
        fig.update_yaxes(title_text="kWh/an", row=1, col=1)
        fig.update_yaxes(title_text="%", row=1, col=2)
        fig.update_yaxes(title_text="%", row=2, col=1)
        fig.update_yaxes(title_text="%", row=2, col=2)
        
        # Rotation des labels x
        fig.update_xaxes(tickangle=45)
        
        return fig
    
    @staticmethod
    def create_battery_operation_chart(daily_simulation: Dict) -> go.Figure:
        """Crée un graphique de l'opération journalière de la batterie"""
        
        hours = list(range(24))
        
        fig = make_subplots(
            rows=3, cols=1,
            subplot_titles=("État de Charge (SOC)", "Charge/Décharge", "Flux Réseau"),
            shared_xaxes=True,
            vertical_spacing=0.1
        )
        
        # Graphique SOC
        fig.add_trace(
            go.Scatter(
                x=hours,
                y=daily_simulation.get("hourly_soc", [0]*24),
                mode='lines',
                name='SOC',
                line=dict(color='green', width=3),
                fill='tozeroy'
            ),
            row=1, col=1
        )
        
        # Graphique Charge/Décharge
        fig.add_trace(
            go.Bar(
                x=hours,
                y=daily_simulation.get("hourly_charge", [0]*24),
                name='Charge',
                marker_color='blue'
            ),
            row=2, col=1
        )
        
        fig.add_trace(
            go.Bar(
                x=hours,
                y=[-x for x in daily_simulation.get("hourly_discharge", [0]*24)],
                name='Décharge',
                marker_color='red'
            ),
            row=2, col=1
        )
        
        # Graphique Flux Réseau
        fig.add_trace(
            go.Bar(
                x=hours,
                y=daily_simulation.get("hourly_import", [0]*24),
                name='Import',
                marker_color='orange'
            ),
            row=3, col=1
        )
        
        fig.add_trace(
            go.Bar(
                x=hours,
                y=[-x for x in daily_simulation.get("hourly_export", [0]*24)],
                name='Export',
                marker_color='purple'
            ),
            row=3, col=1
        )
        
        fig.update_layout(
            title_text="Opération Journalière de la Batterie",
            height=700,
            showlegend=True,
            template="plotly_white"
        )
        
        # Mise à jour des axes
        fig.update_yaxes(title_text="SOC (kWh)", row=1, col=1)
        fig.update_yaxes(title_text="Puissance (kW)", row=2, col=1)
        fig.update_yaxes(title_text="Puissance (kW)", row=3, col=1)
        fig.update_xaxes(title_text="Heure", row=3, col=1)
        
        return fig
    
    @staticmethod
    def create_pv_production_chart(monthly_production: Dict) -> go.Figure:
        """Crée un graphique de production PV mensuelle"""
        
        months = list(monthly_production.keys())
        values = list(monthly_production.values())
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=months,
            y=values,
            name='Production PV',
            marker_color='orange',
            text=[f"{v:.0f} kWh" for v in values],
            textposition='auto'
        ))
        
        fig.update_layout(
            title_text="Production PV Mensuelle",
            xaxis_title="Mois",
            yaxis_title="Production (kWh)",
            template="plotly_white",
            showlegend=False
        )
        
        return fig