import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import math
from datetime import datetime
import io

# ========== CONFIGURATION ==========
st.set_page_config(
    page_title="Dimensionnement PV + Batterie",
    page_icon="🔋",
    layout="wide"
)

st.title("🔋 DIMENSIONNEMENT COMPLET - SYSTÈME PV + BATTERIE")
st.markdown("**Étude de dimensionnement avec analyse détaillée des scénarios**")

# ========== FONCTIONS DE CALCUL ==========
def calculate_pv_production(pv_power_kw, irradiation_kwh_m2, pr_percent, system_losses_percent=14):
    """Calcule la production PV annuelle"""
    production = pv_power_kw * irradiation_kwh_m2 * (pr_percent/100) * (1 - system_losses_percent/100)
    return round(production, 1)

def calculate_battery_sizing(night_energy_kwh, battery_tech, autonomy_hours=None):
    """Calcule la dimension de la batterie"""
    if battery_tech == "Aucune":
        return {"capacity_kwh": 0, "usable_kwh": 0, "dod": 0, "efficiency": 0}
    
    # Paramètres selon technologie
    if battery_tech == "Lithium-ion":
        dod = 0.85  # Depth of Discharge
        efficiency = 0.95  # Round-trip efficiency
        cost_per_kwh = 500  # €/kWh
    elif battery_tech == "Plomb-acide":
        dod = 0.50
        efficiency = 0.85
        cost_per_kwh = 200
    else:
        dod = 0.60
        efficiency = 0.90
        cost_per_kwh = 300
    
    if autonomy_hours:
        # Calcul basé sur l'autonomie
        capacity = (night_energy_kwh * autonomy_hours / 24) / (dod * efficiency)
    else:
        # Calcul basé sur le besoin nocturne
        capacity = night_energy_kwh / (dod * efficiency)
    
    usable = capacity * dod * efficiency
    
    # Arrondir à des valeurs commerciales
    commercial_capacities = [2.0, 3.0, 4.0, 5.0, 5.5, 6.0, 8.0, 10.0, 12.0]
    selected = min(commercial_capacities, key=lambda x: abs(x - capacity))
    
    return {
        "capacity_kwh": selected,
        "usable_kwh": selected * dod * efficiency,
        "dod": dod * 100,
        "efficiency": efficiency * 100,
        "cost": selected * cost_per_kwh,
        "tech": battery_tech
    }

def simulate_scenario(annual_consumption, pv_production, battery_config, scenario_id):
    """Simule un scénario énergétique"""
    pv = pv_production
    battery_capacity = battery_config["capacity_kwh"]
    battery_usable = battery_config["usable_kwh"]
    battery_tech = battery_config["tech"]
    
    # Initialisation selon scénario
    if scenario_id == "S0":  # Réseau seul
        grid_import = annual_consumption
        grid_export = 0
        battery_charge = 0
        battery_discharge = 0
        pv_used = 0
        energy_lost = pv  # Tout le PV est perdu (non utilisé)
        
    elif scenario_id == "S1":  # PV seul
        # Autoconsommation de 65%
        pv_used = pv * 0.65
        grid_import = max(0, annual_consumption - pv_used)
        grid_export = max(0, pv - pv_used) * 0.3  # 30% d'injection
        energy_lost = (pv - pv_used) * 0.7  # 70% de pertes
        battery_charge = 0
        battery_discharge = 0
        
    elif scenario_id in ["S2", "S3", "S4"]:  # Avec batterie
        # Autoconsommation augmentée avec batterie
        if scenario_id == "S2":  # PV + Plomb
            self_consumption_rate = 0.75
            battery_efficiency = 0.85
        elif scenario_id == "S3":  # PV + Li-ion
            self_consumption_rate = 0.85
            battery_efficiency = 0.95
        else:  # S4: Optimisé
            self_consumption_rate = 0.90
            battery_efficiency = 0.97
        
        # Énergie disponible pour la batterie
        excess_pv = pv * (1 - self_consumption_rate)
        battery_charge = min(excess_pv, battery_usable / battery_efficiency)
        battery_discharge = battery_charge * battery_efficiency
        
        # Bilan énergétique
        pv_direct_use = pv * self_consumption_rate
        total_available = pv_direct_use + battery_discharge
        grid_import = max(0, annual_consumption - total_available)
        grid_export = max(0, excess_pv - battery_charge) * 0.2  # 20% injection restante
        energy_lost = (excess_pv - battery_charge) * 0.8 + (battery_charge * (1 - battery_efficiency))
        pv_used = pv_direct_use + battery_charge
    
    # Calcul des indicateurs
    self_consumption_rate = (pv_used / pv * 100) if pv > 0 else 0
    total_coverage = ((pv_used + battery_discharge) / annual_consumption * 100) if annual_consumption > 0 else 0
    grid_reduction = ((annual_consumption - grid_import) / annual_consumption * 100) if annual_consumption > 0 else 0
    
    return {
        "scenario_id": scenario_id,
        "scenario_name": f"Scénario {scenario_id[-1]}",
        "description": get_scenario_description(scenario_id),
        "pv_energy_kwh": pv,
        "pv_used_kwh": pv_used,
        "battery_charge_kwh": battery_charge,
        "battery_discharge_kwh": battery_discharge,
        "grid_import_kwh": grid_import,
        "grid_export_kwh": grid_export,
        "energy_lost_kwh": energy_lost,
        "self_consumption_percent": round(self_consumption_rate, 1),
        "total_coverage_percent": round(total_coverage, 1),
        "grid_reduction_percent": round(grid_reduction, 1),
        "battery_tech": battery_tech,
        "battery_capacity_kwh": battery_capacity,
        "annual_cost_eur": round(grid_import * 0.15 - grid_export * 0.08, 1)  # 0.15€/kWh achat, 0.08€ vente
    }

def get_scenario_description(scenario_id):
    """Retourne la description du scénario"""
    descriptions = {
        "S0": "Réseau seul (référence)",
        "S1": "PV seul sans batterie",
        "S2": "PV + Batterie Plomb-acide",
        "S3": "PV + Batterie Lithium-ion",
        "S4": "Configuration optimisée"
    }
    return descriptions.get(scenario_id, "")

# ========== SIDEBAR - PARAMÈTRES DE DIMENSIONNEMENT ==========
with st.sidebar:
    st.header("⚙️ PARAMÈTRES DE DIMENSIONNEMENT")
    
    # Section 1: Consommation
    st.subheader("🏠 CONSOMMATION ÉLECTRIQUE")
    
    annual_consumption = st.number_input(
        "Consommation annuelle (kWh/an)",
        min_value=1000.0,
        max_value=20000.0,
        value=4479.3,
        step=100.0,
        help="Consommation électrique totale de l'habitation"
    )
    
    night_percentage = st.slider(
        "Part consommation nocturne (%)",
        min_value=10,
        max_value=50,
        value=35,
        step=1,
        help="Pourcentage de la consommation qui se produit la nuit"
    )
    
    night_energy = annual_consumption * (night_percentage / 100)
    daily_consumption = annual_consumption / 365
    avg_power = (daily_consumption / 24) * 1000
    
    st.info(f"""
    **Récapitulatif consommation:**
    - Journalière: {daily_consumption:.1f} kWh/j
    - Nocturne: {night_energy/365:.1f} kWh/j
    - Puissance moyenne: {avg_power:.0f} W
    """)
    
    # Section 2: Localisation
    st.subheader("📍 LOCALISATION")
    
    city = st.selectbox(
        "Ville",
        ["Rabat", "Casablanca", "Marrakech", "Fès", "Tanger", "Agadir"],
        index=0
    )
    
    # Irradiation selon ville (kWh/m²)
    irradiation_data = {
        "Rabat": 1900,
        "Casablanca": 1850,
        "Marrakech": 2100,
        "Fès": 1950,
        "Tanger": 1800,
        "Agadir": 2200
    }
    
    irradiation = irradiation_data[city]
    st.metric("Irradiation annuelle", f"{irradiation} kWh/m²")
    
    # Section 3: Système PV
    st.subheader("☀️ SYSTÈME PHOTOVOLTAÏQUE")
    
    pv_target_coverage = st.slider(
        "Objectif couverture PV (%)",
        min_value=30,
        max_value=100,
        value=60,
        step=5,
        help="Pourcentage de la consommation à couvrir par le PV"
    )
    
    pv_pr = st.slider(
        "Performance Ratio (PR) (%)",
        min_value=65,
        max_value=85,
        value=75,
        step=1,
        help="Performance du système PV"
    )
    
    module_efficiency = st.slider(
        "Rendement module (%)",
        min_value=15,
        max_value=25,
        value=20,
        step=1,
        help="Rendement des panneaux PV"
    )
    
    # Calcul puissance PV nécessaire
    required_pv_energy = annual_consumption * (pv_target_coverage / 100)
    required_pv_power = required_pv_energy / (irradiation * (pv_pr/100))
    
    # Puissances commerciales disponibles
    commercial_powers = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 6.0, 8.0, 10.0]
    selected_pv_power = min(commercial_powers, key=lambda x: abs(x - required_pv_power))
    
    # Calcul production réelle
    pv_production = calculate_pv_production(selected_pv_power, irradiation, pv_pr)
    actual_coverage = (pv_production / annual_consumption) * 100
    
    st.metric("Puissance PV nécessaire", f"{required_pv_power:.1f} kWc")
    st.metric("Puissance installée", f"{selected_pv_power} kWc")
    st.metric("Production estimée", f"{pv_production:,.0f} kWh/an")
    st.metric("Couverture réelle", f"{actual_coverage:.1f}%")
    
    # Section 4: Batterie
    st.subheader("🔋 SYSTÈME DE STOCKAGE")
    
    battery_tech = st.selectbox(
        "Technologie batterie",
        ["Aucune", "Lithium-ion", "Plomb-acide"],
        index=1 if "pv_battery_simulator" in st.session_state else 0
    )
    
    autonomy_hours = None
    if battery_tech != "Aucune":
        autonomy_option = st.radio(
            "Critère de dimensionnement",
            ["Couverture besoin nocturne", "Autonomie spécifique"],
            index=0
        )
        
        if autonomy_option == "Autonomie spécifique":
            autonomy_hours = st.slider(
                "Autonomie souhaitée (heures)",
                min_value=4,
                max_value=24,
                value=8,
                step=1
            )
    
    # Calcul dimensionnement batterie
    battery_config = calculate_battery_sizing(night_energy/365, battery_tech, autonomy_hours)
    
    if battery_tech != "Aucune":
        st.metric("Capacité batterie", f"{battery_config['capacity_kwh']} kWh")
        st.metric("Énergie utilisable", f"{battery_config['usable_kwh']:.1f} kWh")
        st.metric("Coût estimé", f"{battery_config['cost']:,.0f} €")
    
    # Bouton simulation
    st.markdown("---")
    if st.button("🚀 LANCER LA SIMULATION", type="primary", use_container_width=True):
        st.session_state.simulated = True

# ========== FONCTIONS DE VISUALISATION ==========
def create_energy_balance_chart(scenarios_data):
    """Crée un graphique du bilan énergétique"""
    scenarios = ["S0", "S1", "S2", "S3", "S4"]
    
    # Préparer les données
    categories = ["PV Utilisé", "Batterie", "Réseau"]
    colors = ["orange", "green", "gray"]
    
    fig = go.Figure()
    
    for i, cat in enumerate(categories):
        values = []
        for s in scenarios:
            data = scenarios_data[s]
            if cat == "PV Utilisé":
                values.append(data["pv_used_kwh"])
            elif cat == "Batterie":
                values.append(data["battery_discharge_kwh"])
            else:  # Réseau
                values.append(data["grid_import_kwh"])
        
        fig.add_trace(go.Bar(
            name=cat,
            x=scenarios,
            y=values,
            marker_color=colors[i],
            text=[f"{v:,.0f}" for v in values],
            textposition='auto'
        ))
    
    fig.update_layout(
        title="📊 Bilan Énergétique par Scénario (kWh/an)",
        barmode='stack',
        xaxis_title="Scénario",
        yaxis_title="Énergie (kWh/an)",
        template="plotly_white",
        height=400,
        showlegend=True
    )
    
    return fig

def create_performance_indicators_chart(scenarios_data):
    """Crée un graphique des indicateurs de performance"""
    scenarios = ["S0", "S1", "S2", "S3", "S4"]
    
    indicators = {
        "Autoconsommation": [scenarios_data[s]["self_consumption_percent"] for s in scenarios],
        "Couverture totale": [scenarios_data[s]["total_coverage_percent"] for s in scenarios],
        "Réduction réseau": [scenarios_data[s]["grid_reduction_percent"] for s in scenarios]
    }
    
    fig = go.Figure()
    
    colors = ["blue", "green", "red"]
    
    for i, (name, values) in enumerate(indicators.items()):
        fig.add_trace(go.Scatter(
            x=scenarios,
            y=values,
            name=name,
            mode='lines+markers',
            line=dict(color=colors[i], width=3),
            marker=dict(size=10)
        ))
    
    fig.update_layout(
        title="📈 Indicateurs de Performance par Scénario (%)",
        xaxis_title="Scénario",
        yaxis_title="Pourcentage (%)",
        template="plotly_white",
        height=400,
        hovermode='x unified'
    )
    
    return fig

def create_technology_comparison_chart(scenarios_data):
    """Crée un graphique de comparaison des technologies"""
    scenarios = ["S1", "S2", "S3", "S4"]
    
    tech_names = []
    costs = []
    efficiencies = []
    coverages = []
    
    for s in scenarios:
        data = scenarios_data[s]
        tech_names.append(data["battery_tech"] if data["battery_tech"] else "PV seul")
        costs.append(data["annual_cost_eur"])
        efficiencies.append(data["self_consumption_percent"])
        coverages.append(data["total_coverage_percent"])
    
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=("Coût annuel (€)", "Autoconsommation (%)", 
                       "Couverture totale (%)", "Batterie (kWh)"),
        vertical_spacing=0.15
    )
    
    # Coût annuel
    fig.add_trace(
        go.Bar(x=tech_names, y=costs, name="Coût", marker_color="red"),
        row=1, col=1
    )
    
    # Autoconsommation
    fig.add_trace(
        go.Bar(x=tech_names, y=efficiencies, name="Autoconsommation", marker_color="blue"),
        row=1, col=2
    )
    
    # Couverture totale
    fig.add_trace(
        go.Bar(x=tech_names, y=coverages, name="Couverture", marker_color="green"),
        row=2, col=1
    )
    
    # Capacité batterie
    battery_caps = [0, scenarios_data["S2"]["battery_capacity_kwh"], 
                    scenarios_data["S3"]["battery_capacity_kwh"],
                    scenarios_data["S4"]["battery_capacity_kwh"]]
    fig.add_trace(
        go.Bar(x=tech_names, y=battery_caps, name="Capacité", marker_color="orange"),
        row=2, col=2
    )
    
    fig.update_layout(
        title="🔧 Comparaison des Technologies",
        showlegend=False,
        height=500,
        template="plotly_white"
    )
    
    return fig

def create_radar_comparison_chart(scenarios_data):
    """Crée un graphique radar multicritère"""
    criteria = ["Réduction", "Autoconsom.", "Couverture", "Économie", "Durabilité"]
    
    # Normalisation des données
    normalized = {}
    
    for s in ["S1", "S2", "S3", "S4"]:
        data = scenarios_data[s]
        values = [
            data["grid_reduction_percent"] / 100,
            data["self_consumption_percent"] / 100,
            data["total_coverage_percent"] / 100,
            (1 - data["annual_cost_eur"] / scenarios_data["S0"]["annual_cost_eur"]),
            0.7 if s == "S2" else 0.9 if s == "S3" else 1.0  # Durabilité relative
        ]
        normalized[s] = values
    
    fig = go.Figure()
    
    colors = ["orange", "yellow", "lightgreen", "green"]
    
    for i, s in enumerate(["S1", "S2", "S3", "S4"]):
        fig.add_trace(go.Scatterpolar(
            r=normalized[s] + [normalized[s][0]],
            theta=criteria + [criteria[0]],
            name=f"Scénario {s[-1]}",
            line=dict(color=colors[i], width=3),
            fill='toself',
            opacity=0.3
        ))
    
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        title="🎯 Analyse Multicritère des Scénarios",
        showlegend=True,
        height=450,
        template="plotly_white"
    )
    
    return fig

# ========== ONGLETS PRINCIPAUX ==========
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📐 DIMENSIONNEMENT",
    "📊 RÉSULTATS SCÉNARIOS",
    "📈 PERFORMANCES",
    "🔧 COMPARAISONS",
    "📥 EXPORT"
])

with tab1:
    st.header("📐 DIMENSIONNEMENT DU SYSTÈME")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("☀️ SYSTÈME PV")
        
        # Surface nécessaire
        module_area = selected_pv_power / (1 * (module_efficiency/100))  # kW / (kW/m² * rendement)
        
        st.metric("Puissance installée", f"{selected_pv_power} kWc")
        st.metric("Nombre de modules (330W)", f"{int((selected_pv_power * 1000) / 330)}")
        st.metric("Surface nécessaire", f"{module_area:.1f} m²")
        st.metric("Production spécifique", f"{pv_production/selected_pv_power:.0f} kWh/kWc")
        
        # Graphique production mensuelle
        monthly_factors = [0.08, 0.09, 0.10, 0.11, 0.12, 0.12, 
                          0.12, 0.11, 0.10, 0.09, 0.08, 0.07]
        monthly_production = [pv_production * f for f in monthly_factors]
        months = ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin", 
                 "Juil", "Août", "Sep", "Oct", "Nov", "Déc"]
        
        fig_pv = go.Figure(data=[
            go.Bar(x=months, y=monthly_production, marker_color='orange')
        ])
        fig_pv.update_layout(
            title="Production PV Mensuelle Estimée",
            xaxis_title="Mois",
            yaxis_title="Production (kWh)",
            template="plotly_white",
            height=300
        )
        st.plotly_chart(fig_pv, use_container_width=True)
    
    with col2:
        st.subheader("🔋 SYSTÈME DE STOCKAGE")
        
        if battery_tech != "Aucune":
            autonomy = battery_config["usable_kwh"] / (avg_power/1000) if avg_power > 0 else 0
            night_coverage = (battery_config["usable_kwh"] / (night_energy/365)) * 100
            
            st.metric("Technologie", battery_tech)
            st.metric("Capacité nominale", f"{battery_config['capacity_kwh']} kWh")
            st.metric("Énergie utilisable", f"{battery_config['usable_kwh']:.1f} kWh")
            st.metric("Autonomie estimée", f"{autonomy:.1f} heures")
            st.metric("Couverture nuit", f"{night_coverage:.1f}%")
            st.metric("Rendement", f"{battery_config['efficiency']}%")
            st.metric("DoD", f"{battery_config['dod']}%")
            
            # Comparaison technologies
            tech_comparison = pd.DataFrame({
                "Paramètre": ["DoD", "Rendement", "Durée de vie", "Cycles", "Coût"],
                "Plomb-acide": ["50%", "85%", "3-5 ans", "500-800", "200 €/kWh"],
                "Lithium-ion": ["85%", "95%", "10-15 ans", "3000-6000", "500 €/kWh"]
            })
            st.dataframe(tech_comparison, use_container_width=True, hide_index=True)
        else:
            st.info("Aucune batterie sélectionnée")
        
        st.subheader("📈 BILAN CONSOMMATION")
        consumption_data = pd.DataFrame({
            "Période": ["Jour", "Nuit", "Total"],
            "Énergie (kWh/j)": [
                daily_consumption * (1 - night_percentage/100),
                daily_consumption * (night_percentage/100),
                daily_consumption
            ],
            "Pourcentage": [
                f"{100 - night_percentage}%",
                f"{night_percentage}%",
                "100%"
            ]
        })
        st.dataframe(consumption_data, use_container_width=True, hide_index=True)

with tab2:
    if 'simulated' not in st.session_state:
        st.info("👈 Configurez les paramètres et lancez la simulation")
    else:
        st.header("📊 RÉSULTATS DES SCÉNARIOS")
        
        # Simuler tous les scénarios
        scenarios_to_simulate = ["S0", "S1", "S2", "S3", "S4"]
        scenarios_results = {}
        
        for scenario_id in scenarios_to_simulate:
            if scenario_id == "S0":
                battery_config_s0 = {"capacity_kwh": 0, "usable_kwh": 0, "tech": "Aucune"}
            elif scenario_id == "S1":
                battery_config_s1 = {"capacity_kwh": 0, "usable_kwh": 0, "tech": "Aucune"}
            elif scenario_id == "S2":
                battery_config_s2 = calculate_battery_sizing(night_energy/365, "Plomb-acide", 8)
            elif scenario_id == "S3":
                battery_config_s3 = calculate_battery_sizing(night_energy/365, "Lithium-ion", 8)
            else:  # S4
                battery_config_s4 = calculate_battery_sizing(night_energy/365, "Lithium-ion", 10)
            
            battery_config = locals().get(f"battery_config_{scenario_id.lower()}", 
                                         battery_config if scenario_id in ["S2", "S3", "S4"] else 
                                         {"capacity_kwh": 0, "usable_kwh": 0, "tech": "Aucune"})
            
            scenarios_results[scenario_id] = simulate_scenario(
                annual_consumption, pv_production, battery_config, scenario_id
            )
        
        # Tableau des résultats
        results_table = []
        for s in scenarios_to_simulate:
            data = scenarios_results[s]
            results_table.append({
                "Scénario": data["scenario_id"],
                "Description": data["description"],
                "PV produit (kWh)": f"{data['pv_energy_kwh']:,.0f}",
                "PV utilisé (kWh)": f"{data['pv_used_kwh']:,.0f}",
                "Batt. chargée (kWh)": f"{data['battery_charge_kwh']:,.0f}",
                "Batt. déchargée (kWh)": f"{data['battery_discharge_kwh']:,.0f}",
                "Réseau import (kWh)": f"{data['grid_import_kwh']:,.0f}",
                "Réseau export (kWh)": f"{data['grid_export_kwh']:,.0f}",
                "Pertes (kWh)": f"{data['energy_lost_kwh']:,.0f}",
                "Autoconso. (%)": f"{data['self_consumption_percent']}",
                "Couverture (%)": f"{data['total_coverage_percent']}",
                "Réduction (%)": f"{data['grid_reduction_percent']}",
                "Coût (€)": f"{data['annual_cost_eur']}"
            })
        
        df_results = pd.DataFrame(results_table)
        st.dataframe(df_results, use_container_width=True)
        
        # Graphique bilan énergétique
        st.subheader("📊 Bilan Énergétique")
        st.plotly_chart(create_energy_balance_chart(scenarios_results), use_container_width=True)

with tab3:
    if 'simulated' in st.session_state:
        st.header("📈 ANALYSE DES PERFORMANCES")
        
        # Graphique indicateurs
        st.plotly_chart(create_performance_indicators_chart(scenarios_results), 
                       use_container_width=True)
        
        # Analyse détaillée par scénario
        st.subheader("📋 Analyse Détailée")
        
        selected_scenario = st.selectbox(
            "Sélectionner un scénario",
            list(scenarios_results.keys()),
            format_func=lambda x: f"{x}: {scenarios_results[x]['scenario_name']}"
        )
        
        if selected_scenario:
            data = scenarios_results[selected_scenario]
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Énergie PV produite", f"{data['pv_energy_kwh']:,.0f} kWh")
                st.metric("Énergie PV utilisée", f"{data['pv_used_kwh']:,.0f} kWh")
                st.metric("Taux d'utilisation PV", f"{data['pv_used_kwh']/data['pv_energy_kwh']*100:.1f}%" 
                         if data['pv_energy_kwh'] > 0 else "0%")
            
            with col2:
                st.metric("Stockage batterie", f"{data['battery_charge_kwh']:,.0f} → {data['battery_discharge_kwh']:,.0f} kWh")
                st.metric("Rendement batterie", f"{data['battery_discharge_kwh']/data['battery_charge_kwh']*100:.1f}%" 
                         if data['battery_charge_kwh'] > 0 else "-")
                st.metric("Import réseau", f"{data['grid_import_kwh']:,.0f} kWh")
            
            with col3:
                st.metric("Export réseau", f"{data['grid_export_kwh']:,.0f} kWh")
                st.metric("Pertes système", f"{data['energy_lost_kwh']:,.0f} kWh")
                st.metric("Coût annuel", f"{data['annual_cost_eur']} €")
            
            # Diagramme circulaire pour le scénario sélectionné
            if data['pv_energy_kwh'] > 0:
                labels = ['Autoconsommation directe', 'Charge batterie', 'Export réseau', 'Pertes']
                direct_use = data['pv_used_kwh'] - data['battery_charge_kwh']
                values = [
                    max(0, direct_use),
                    data['battery_charge_kwh'],
                    data['grid_export_kwh'],
                    data['energy_lost_kwh']
                ]
                
                fig_pie = go.Figure(data=[go.Pie(
                    labels=labels,
                    values=values,
                    hole=0.4,
                    marker_colors=['green', 'blue', 'orange', 'red']
                )])
                fig_pie.update_layout(title=f"Répartition Production PV - {data['scenario_name']}")
                st.plotly_chart(fig_pie, use_container_width=True)

with tab4:
    if 'simulated' in st.session_state:
        st.header("🔧 COMPARAISONS DÉTAILLÉES")
        
        # Comparaison technologies
        st.subheader("🔋 Comparaison des Technologies de Stockage")
        st.plotly_chart(create_technology_comparison_chart(scenarios_results), 
                       use_container_width=True)
        
        # Analyse multicritère
        st.subheader("🎯 Analyse Multicritère")
        st.plotly_chart(create_radar_comparison_chart(scenarios_results), 
                       use_container_width=True)
        
        # Recommandation finale
        st.subheader("🏆 RECOMMANDATION")
        
        # Calcul du score pour chaque scénario (sauf S0)
        scores = []
        for s in ["S1", "S2", "S3", "S4"]:
            data = scenarios_results[s]
            score = (
                data["grid_reduction_percent"] * 0.35 +
                data["self_consumption_percent"] * 0.25 +
                data["total_coverage_percent"] * 0.20 +
                (1 - data["annual_cost_eur"] / scenarios_results["S0"]["annual_cost_eur"]) * 100 * 0.20
            )
            scores.append({
                "Scénario": s,
                "Score": round(score, 1),
                "Réduction": data["grid_reduction_percent"],
                "Autoconsommation": data["self_consumption_percent"],
                "Coût annuel": data["annual_cost_eur"]
            })
        
        df_scores = pd.DataFrame(scores).sort_values("Score", ascending=False)
        best = df_scores.iloc[0]
        best_data = scenarios_results[best["Scénario"]]
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.success(f"""
            **SCÉNARIO RECOMMANDÉ : {best_data['scenario_name']}**
            
            **Score : {best['Score']}/100**
            
            **Performances :**
            - Réduction appel réseau : {best['Réduction']}%
            - Autoconsommation : {best['Autoconsommation']}%
            - Couverture énergétique : {best_data['total_coverage_percent']}%
            - Économie annuelle : {scenarios_results['S0']['annual_cost_eur'] - best['Coût annuel']:,.0f} €
            
            **Configuration :**
            - PV : {selected_pv_power} kWc
            - Batterie : {best_data['battery_tech']} {best_data['battery_capacity_kwh']} kWh
            - Autonomie : {best_data['battery_discharge_kwh']/(avg_power/1000):.1f} heures
            """)
        
        with col2:
            # Graphique de score
            categories = ['Réduction', 'Autoconso.', 'Couverture', 'Économie']
            values = [
                best['Réduction'] / 100,
                best['Autoconsommation'] / 100,
                best_data['total_coverage_percent'] / 100,
                (1 - best['Coût annuel'] / scenarios_results["S0"]["annual_cost_eur"])
            ]
            
            fig_score = go.Figure(data=go.Scatterpolar(
                r=values,
                theta=categories,
                fill='toself',
                line=dict(color='green', width=3),
                marker=dict(size=8)
            ))
            fig_score.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
                showlegend=False,
                height=300,
                title="Profil de performance"
            )
            st.plotly_chart(fig_score, use_container_width=True)

with tab5:
    st.header("📥 EXPORT DES RÉSULTATS")
    
    if 'simulated' in st.session_state:
        # Préparer les données pour export
        export_data = []
        for s in ["S0", "S1", "S2", "S3", "S4"]:
            data = scenarios_results[s]
            export_data.append({
                "Scénario": data["scenario_id"],
                "Nom": data["scenario_name"],
                "Description": data["description"],
                "PV_Produit_kWh": data["pv_energy_kwh"],
                "PV_Utilisé_kWh": data["pv_used_kwh"],
                "Batterie_Charge_kWh": data["battery_charge_kwh"],
                "Batterie_Décharge_kWh": data["battery_discharge_kwh"],
                "Réseau_Import_kWh": data["grid_import_kwh"],
                "Réseau_Export_kWh": data["grid_export_kwh"],
                "Pertes_kWh": data["energy_lost_kwh"],
                "Autoconsommation_%": data["self_consumption_percent"],
                "Couverture_Totale_%": data["total_coverage_percent"],
                "Réduction_Réseau_%": data["grid_reduction_percent"],
                "Coût_Annuel_€": data["annual_cost_eur"],
                "Technologie_Batterie": data["battery_tech"],
                "Capacité_Batterie_kWh": data["battery_capacity_kwh"]
            })
        
        df_export = pd.DataFrame(export_data)
        
        # Export CSV
        csv_data = df_export.to_csv(index=False, sep=';').encode('utf-8')
        
        st.download_button(
            label="📥 Télécharger CSV",
            data=csv_data,
            file_name=f"resultats_dimensionnement_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            help="Données au format CSV (ouvrable avec Excel)"
        )
        
        # Rapport texte
        rapport_content = f"""
        RAPPORT DE DIMENSIONNEMENT - SYSTÈME PV + BATTERIE
        ==================================================
        
        Date : {datetime.now().strftime('%d/%m/%Y %H:%M')}
        
        1. PARAMÈTRES DU SYSTÈME
        -----------------------
        • Consommation annuelle : {annual_consumption:,.1f} kWh
        • Consommation nocturne : {night_percentage}% ({night_energy/365:.1f} kWh/j)
        • Ville : {city} (Irradiation : {irradiation} kWh/m²)
        • Objectif couverture PV : {pv_target_coverage}%
        • Performance Ratio : {pv_pr}%
        
        2. DIMENSIONNEMENT PV
        --------------------
        • Puissance installée : {selected_pv_power} kWc
        • Production estimée : {pv_production:,.0f} kWh/an
        • Couverture réelle : {actual_coverage:.1f}%
        • Surface nécessaire : {module_area:.1f} m²
        • Nombre de modules (330W) : {int((selected_pv_power * 1000) / 330)}
        
        3. DIMENSIONNEMENT BATTERIE
        --------------------------
        • Technologie : {battery_tech}
        • Capacité : {battery_config['capacity_kwh']} kWh
        • Énergie utilisable : {battery_config['usable_kwh']:.1f} kWh
        • Autonomie estimée : {battery_config['usable_kwh']/(avg_power/1000):.1f} heures
        • Couverture besoin nocturne : {(battery_config['usable_kwh']/(night_energy/365))*100:.1f}%
        
        4. RÉSULTATS PAR SCÉNARIO
        ------------------------
        """
        
        for data in export_data:
            rapport_content += f"""
        {data['Nom']} ({data['Scénario']}):
          • PV produit/utilisé : {data['PV_Produit_kWh']:,.0f} / {data['PV_Utilisé_kWh']:,.0f} kWh
          • Batterie (charge/décharge) : {data['Batterie_Charge_kWh']:,.0f} / {data['Batterie_Décharge_kWh']:,.0f} kWh
          • Réseau (import/export) : {data['Réseau_Import_kWh']:,.0f} / {data['Réseau_Export_kWh']:,.0f} kWh
          • Pertes : {data['Pertes_kWh']:,.0f} kWh
          • Autoconsommation : {data['Autoconsommation_%']}%
          • Couverture totale : {data['Couverture_Totale_%']}%
          • Réduction réseau : {data['Réduction_Réseau_%']}%
          • Coût annuel : {data['Coût_Annuel_€']} €
            """
        
        # Trouver le meilleur scénario
        best_score = 0
        best_scenario = ""
        for s in ["S1", "S2", "S3", "S4"]:
            data = scenarios_results[s]
            score = data["grid_reduction_percent"] * 0.4 + data["self_consumption_percent"] * 0.3 + data["total_coverage_percent"] * 0.3
            if score > best_score:
                best_score = score
                best_scenario = s
        
        best_data = scenarios_results[best_scenario]
        
        rapport_content += f"""
        
        5. RECOMMANDATION
        -----------------
        Scénario recommandé : {best_data['scenario_name']} ({best_scenario})
        
        Configuration optimale :
        • Système PV : {selected_pv_power} kWc
        • Batterie : {best_data['battery_tech']} {best_data['battery_capacity_kwh']} kWh
        • Autonomie : {best_data['battery_discharge_kwh']/(avg_power/1000):.1f} heures
        
        Performance attendue :
        • Réduction appel réseau : {best_data['grid_reduction_percent']}%
        • Autoconsommation : {best_data['self_consumption_percent']}%
        • Couverture énergétique : {best_data['total_coverage_percent']}%
        • Économie annuelle : {scenarios_results['S0']['annual_cost_eur'] - best_data['annual_cost_eur']:,.0f} €
        
        6. CONCLUSION
        -------------
        Le dimensionnement proposé permet de réduire significativement la dépendance
        au réseau électrique tout en optimisant l'autoconsommation de l'énergie
        produite localement.
        """
        
        st.download_button(
            label="📥 Télécharger Rapport Complet",
            data=rapport_content.encode('utf-8'),
            file_name=f"rapport_dimensionnement_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
            mime="text/plain"
        )
        
        # Afficher aperçu
        with st.expander("Aperçu du rapport"):
            st.text(rapport_content[:1000] + "...")
    
    else:
        st.info("Lancez d'abord une simulation pour exporter les résultats")

# ========== FOOTER ==========
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; font-size: 0.9rem;">
    <p><strong>🔋 Outil de Dimensionnement PV + Batterie - Analyse Complète</strong></p>
    <p>Tous les indicateurs énergétiques • Dimensionnement personnalisé • Recommandation optimisée</p>
    <p>© 2024 - Projet de stockage d'énergie électrique</p>
</div>
""", unsafe_allow_html=True)

# Initialisation
if 'simulated' not in st.session_state:
    st.session_state.simulated = False
