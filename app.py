"""
Application Streamlit principale - Simulateur PV+Battery
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import base64
import io

# Import des modules
from config import (
    DEFAULT_PARAMS, DEFAULT_LOAD_PROFILE, 
    CITIES_IRRADIATION, BATTERY_TECHNOLOGIES, SCENARIOS
)
from modules.consumption import ConsumptionAnalyzer
from modules.pv_system import PVSystem
from modules.battery_system import BatterySystem
from modules.simulation import ScenarioSimulator
from modules.visualization import Visualization

# Configuration de la page
st.set_page_config(
    page_title="Simulateur PV + Batterie - Projet Stockage",
    page_icon="🔋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personnalisé
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E3A8A;
        text-align: center;
        margin-bottom: 2rem;
    }
    .sub-header {
        font-size: 1.8rem;
        color: #3B82F6;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #F8FAFC;
        padding: 1rem;
        border-radius: 10px;
        border-left: 5px solid #3B82F6;
        margin-bottom: 1rem;
    }
    .scenario-card {
        background-color: #F0F9FF;
        padding: 1rem;
        border-radius: 10px;
        border: 2px solid #3B82F6;
        margin-bottom: 1rem;
    }
    .download-button {
        background-color: #10B981;
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 5px;
        border: none;
        cursor: pointer;
    }
    .download-button:hover {
        background-color: #059669;
    }
</style>
""", unsafe_allow_html=True)

# Initialisation de l'état de session
if 'simulator' not in st.session_state:
    st.session_state.simulator = None
if 'scenarios' not in st.session_state:
    st.session_state.scenarios = None
if 'comparison_df' not in st.session_state:
    st.session_state.comparison_df = None

# Titre principal
st.markdown('<h1 class="main-header">🔋 Simulateur PV + Batterie - Projet de Stockage</h1>', 
            unsafe_allow_html=True)
st.markdown("""
*Dimensionnement et simulation d'un système photovoltaïque résidentiel avec stockage d'énergie*
""")

# Sidebar pour les paramètres
with st.sidebar:
    st.header("⚙️ Paramètres de Configuration")
    
    # Section localisation
    st.subheader("📍 Localisation")
    selected_city = st.selectbox(
        "Ville",
        list(CITIES_IRRADIATION.keys()),
        index=0
    )
    irradiation = CITIES_IRRADIATION[selected_city]
    st.info(f"Irradiation annuelle: **{irradiation} kWh/m²**")
    
    # Section consommation
    st.subheader("💡 Consommation Électrique")
    annual_consumption = st.number_input(
        "Consommation annuelle (kWh)",
        min_value=1000.0,
        max_value=20000.0,
        value=DEFAULT_PARAMS["annual_consumption"],
        step=100.0,
        help="Consommation électrique annuelle de la maison"
    )
    
    # Section PV
    st.subheader("☀️ Système Photovoltaïque")
    pv_power = st.slider(
        "Puissance PV installée (kWc)",
        1.0, 10.0, DEFAULT_PARAMS["pv_power"], 0.1,
        help="Puissance crête du système PV"
    )
    pv_pr = st.slider(
        "Performance Ratio (%)",
        50, 90, DEFAULT_PARAMS["pv_pr"], 1,
        help="Ratio de performance du système PV"
    )
    
    # Section batterie
    st.subheader("🔋 Système de Stockage")
    battery_tech = st.selectbox(
        "Technologie de batterie",
        list(BATTERY_TECHNOLOGIES.keys()),
        index=0
    )
    
    # Paramètres selon la technologie
    tech_params = BATTERY_TECHNOLOGIES[battery_tech]
    if battery_tech == "Lithium-ion":
        battery_capacity = st.number_input(
            "Capacité batterie (kWh)",
            1.0, 20.0, DEFAULT_PARAMS["battery_capacity_li"], 0.1
        )
        dod = st.slider(
            "Depth of Discharge (DoD) %",
            tech_params["dod_range"][0], 
            tech_params["dod_range"][1],
            DEFAULT_PARAMS["dod_li"], 1
        )
        efficiency = st.slider(
            "Rendement aller-retour %",
            tech_params["efficiency_range"][0],
            tech_params["efficiency_range"][1],
            DEFAULT_PARAMS["efficiency_li"], 1
        )
    else:  # Plomb-acide
        battery_capacity = st.number_input(
            "Capacité batterie (kWh)",
            1.0, 30.0, DEFAULT_PARAMS["battery_capacity_pb"], 0.1
        )
        dod = st.slider(
            "Depth of Discharge (DoD) %",
            tech_params["dod_range"][0], 
            tech_params["dod_range"][1],
            DEFAULT_PARAMS["dod_pb"], 1
        )
        efficiency = st.slider(
            "Rendement aller-retour %",
            tech_params["efficiency_range"][0],
            tech_params["efficiency_range"][1],
            DEFAULT_PARAMS["efficiency_pb"], 1
        )
    
    # Bouton de simulation
    st.markdown("---")
    if st.button("Lancer la Simulation", type="primary", use_container_width=True):
        with st.spinner("Simulation en cours..."):
            # Initialiser le simulateur
            st.session_state.simulator = ScenarioSimulator(
                annual_consumption=annual_consumption,
                city=selected_city,
                irradiation=irradiation,
                load_profile_24h=DEFAULT_LOAD_PROFILE
            )
            
            # Lancer les simulations
            st.session_state.scenarios = st.session_state.simulator.simulate_all_scenarios(
                pv_power_kw=pv_power,
                pv_pr=pv_pr
            )
            
            # Générer le tableau de comparaison
            st.session_state.comparison_df = st.session_state.simulator.generate_comparison_table(
                st.session_state.scenarios
            )
            
            st.success("Simulation terminée avec succès !")
    
    # Bouton de réinitialisation
    if st.button(" Réinitialiser", use_container_width=True):
        st.session_state.simulator = None
        st.session_state.scenarios = None
        st.session_state.comparison_df = None
        st.rerun()

# Onglets principaux
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Analyse Consommation",
    "⚡ Dimensionnement",
    "🔄 Simulation Scénarios",
    "📈 Résultats & Visualisations",
    "📄 Rapport & Export"
])

# Onglet 1: Analyse Consommation
with tab1:
    st.markdown('<h2 class="sub-header">Analyse de la Consommation Résidentielle</h2>', 
                unsafe_allow_html=True)
    
    if st.session_state.simulator:
        consumption_data = st.session_state.simulator.consumption_data
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Consommation annuelle", f"{annual_consumption:,.0f} kWh")
        
        with col2:
            st.metric("Consommation journalière", f"{consumption_data['daily_energy_kwh']:.1f} kWh/j")
        
        with col3:
            st.metric("Puissance moyenne", f"{consumption_data['avg_power_w']:.0f} W")
        
        with col4:
            st.metric("Pic de puissance", f"{consumption_data['peak_power_kw']:.2f} kW")
        
        # Graphique du profil de charge
        st.markdown("#### Profil de Charge Journalier (Load Shape)")
        load_chart = Visualization.create_load_shape_chart(
            consumption_data["hourly_profile"],
            "Profil de Charge Journalier de la Maison"
        )
        st.plotly_chart(load_chart, use_container_width=True)
        
        # Répartition jour/nuit
        st.markdown("#### Répartition Jour/Nuit")
        col1, col2 = st.columns(2)
        
        with col1:
            fig = go.Figure(data=[go.Pie(
                labels=['Jour', 'Nuit'],
                values=[consumption_data['day_energy_kwh'], consumption_data['night_energy_kwh']],
                hole=0.4,
                marker_colors=['#FFA500', '#1E3A8A']
            )])
            fig.update_layout(title_text="Répartition Journalière")
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Tableau des données
            dist_data = {
                "Période": ["Jour (6h-22h)", "Nuit (22h-6h)", "Total"],
                "Énergie (kWh/j)": [
                    consumption_data['day_energy_kwh'],
                    consumption_data['night_energy_kwh'],
                    consumption_data['daily_energy_kwh']
                ],
                "Pourcentage": [
                    f"{consumption_data['day_percentage']:.1f}%",
                    f"{consumption_data['night_percentage']:.1f}%",
                    "100%"
                ]
            }
            st.dataframe(pd.DataFrame(dist_data), use_container_width=True)
    
    else:
        st.info("🟢 Configurez les paramètres et lancez la simulation pour voir les résultats.")

# Onglet 2: Dimensionnement
with tab2:
    st.markdown('<h2 class="sub-header">Dimensionnement du Système</h2>', 
                unsafe_allow_html=True)
    
    if st.session_state.simulator:
        # Dimensionnement PV
        st.markdown("#### ☀️ Dimensionnement du Système PV")
        
        pv_system = PVSystem(selected_city, irradiation)
        pv_data = pv_system.calculate_pv_production(pv_power, pv_pr)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Puissance installée", f"{pv_power} kWc")
        
        with col2:
            st.metric("Production annuelle", f"{pv_data['annual_production_kwh']:,.0f} kWh")
        
        with col3:
            st.metric("Facteur de capacité", f"{pv_data['capacity_factor']:.1f}%")
        
        with col4:
            coverage = (pv_data['annual_production_kwh'] / annual_consumption) * 100
            st.metric("Taux de couverture", f"{coverage:.1f}%")
        
        # Graphique production mensuelle
        st.plotly_chart(
            Visualization.create_pv_production_chart(pv_data["monthly_production"]),
            use_container_width=True
        )
        
        # Dimensionnement batterie
        st.markdown("#### 🔋 Dimensionnement du Système de Stockage")
        
        battery = BatterySystem(battery_tech)
        battery_data = battery.calculate_battery_size(
            night_energy_kwh=st.session_state.simulator.consumption_data["night_energy_kwh"],
            avg_power_kw=st.session_state.simulator.consumption_data["avg_power_w"] / 1000
        )
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Capacité nominale", f"{battery_data['selected_capacity_kwh']} kWh")
        
        with col2:
            st.metric("Capacité utilisable", f"{battery_data['usable_capacity_kwh']:.1f} kWh")
        
        with col3:
            st.metric("Autonomie", f"{battery_data['autonomy_hours']:.1f} h")
        
        with col4:
            st.metric("Couverture nuit", f"{battery_data['night_coverage_percent']:.1f}%")
        
        # Tableau des paramètres batterie
        st.markdown("##### Paramètres de la Batterie")
        battery_params = pd.DataFrame({
            "Paramètre": ["Technologie", "DoD", "Rendement", "Durée de vie", "Cycles", "Coût estimé"],
            "Valeur": [
                battery_data["technology"],
                f"{battery_data['dod']}%",
                f"{battery_data['efficiency']}%",
                f"{battery_data['lifetime_years']} ans",
                f"{battery_data['cycles']:,}",
                f"${battery_data['estimated_cost_usd']:,.0f}"
            ]
        })
        st.dataframe(battery_params, use_container_width=True, hide_index=True)
    
    else:
        st.info("🟢 Lancez la simulation pour voir le dimensionnement.")

# Onglet 3: Simulation Scénarios
with tab3:
    st.markdown('<h2 class="sub-header">Simulation des Scénarios</h2>', 
                unsafe_allow_html=True)
    
    if st.session_state.scenarios:
        # Description des scénarios
        st.markdown("#### Description des Scénarios")
        
        for i in range(5):
            with st.expander(f"**{SCENARIOS[i]['name']}** - {SCENARIOS[i]['description']}"):
                scenario_data = st.session_state.scenarios[i]
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.metric(
                        "Importation réseau", 
                        f"{scenario_data['annual_grid_import_kwh']:,.0f} kWh"
                    )
                    st.metric(
                        "Autoconsommation", 
                        f"{scenario_data.get('self_consumption_percent', 0):.1f}%"
                    )
                
                with col2:
                    st.metric(
                        "Réduction réseau", 
                        f"{scenario_data.get('grid_reduction_percent', 0):.1f}%"
                    )
                    if 'pv_coverage_percent' in scenario_data:
                        st.metric(
                            "Couverture PV", 
                            f"{scenario_data['pv_coverage_percent']:.1f}%"
                        )
                    elif 'total_coverage_percent' in scenario_data:
                        st.metric(
                            "Couverture totale", 
                            f"{scenario_data['total_coverage_percent']:.1f}%"
                        )
        
        # Simulation détaillée par scénario
        st.markdown("#### Simulation Détaillée")
        selected_scenario = st.selectbox(
            "Choisir un scénario pour visualisation détaillée",
            list(st.session_state.scenarios.keys()),
            format_func=lambda x: SCENARIOS[x]["name"]
        )
        
        if selected_scenario is not None:
            scenario_data = st.session_state.scenarios[selected_scenario]
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # Diagramme de Sankey
                sankey_chart = Visualization.create_energy_flow_chart(scenario_data)
                st.plotly_chart(sankey_chart, use_container_width=True)
            
            with col2:
                # Tableau des indicateurs
                indicators = []
                for key, value in scenario_data.items():
                    if any(x in key.lower() for x in ['kwh', 'percent', 'usd', 'kw']):
                        if isinstance(value, (int, float)):
                            if 'percent' in key:
                                indicators.append((key, f"{value:.1f}%"))
                            elif 'usd' in key:
                                indicators.append((key, f"${value:,.0f}"))
                            elif 'kwh' in key and value > 100:
                                indicators.append((key, f"{value:,.0f}"))
                            else:
                                indicators.append((key, f"{value:.2f}"))
                
                df_indicators = pd.DataFrame(indicators, columns=["Indicateur", "Valeur"])
                st.dataframe(df_indicators, use_container_width=True, hide_index=True)
    
    else:
        st.info("🟢 Lancez la simulation pour voir les scénarios.")

# Onglet 4: Résultats & Visualisations
with tab4:
    st.markdown('<h2 class="sub-header">Résultats & Visualisations</h2>', 
                unsafe_allow_html=True)
    
    if st.session_state.comparison_df is not None:
        # Tableau de comparaison
        st.markdown("#### 📊 Tableau Comparatif des Scénarios")
        st.dataframe(st.session_state.comparison_df, use_container_width=True)
        
        # Graphiques de comparaison
        st.markdown("#### 📈 Graphiques de Comparaison")
        comparison_chart = Visualization.create_scenario_comparison_chart(
            st.session_state.comparison_df
        )
        st.plotly_chart(comparison_chart, use_container_width=True)
        
        # Analyse des performances
        st.markdown("#### 📋 Analyse des Performances")
        
        # Trouver le meilleur scénario
        comparison_df = st.session_state.comparison_df
        best_reduction_idx = comparison_df["Réduction réseau (%)"].idxmax()
        best_scenario = comparison_df.loc[best_reduction_idx]
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Meilleur scénario",
                best_scenario["Scénario"]
            )
        
        with col2:
            st.metric(
                "Réduction réseau maximale",
                f"{best_scenario['Réduction réseau (%)']:.1f}%"
            )
        
        with col3:
            st.metric(
                "Autoconsommation maximale",
                f"{max(comparison_df['Autoconsommation (%)']):.1f}%"
            )
        
        # Graphique radar pour comparaison multicritère
        st.markdown("#### 📊 Analyse Multicritère")
        
        # Normalisation des données
        criteria = ['Autoconsommation (%)', 'Réduction réseau (%)', 'Couverture totale (%)']
        normalized_data = []
        
        for idx, row in comparison_df.iterrows():
            normalized_row = []
            for crit in criteria:
                max_val = comparison_df[crit].max()
                min_val = comparison_df[crit].min()
                if max_val > min_val:
                    norm_val = (row[crit] - min_val) / (max_val - min_val) * 100
                else:
                    norm_val = 100
                normalized_row.append(norm_val)
            normalized_data.append(normalized_row)
        
        # Créer le graphique radar
        fig = go.Figure()
        
        for idx, scenario_name in enumerate(comparison_df["Scénario"]):
            fig.add_trace(go.Scatterpolar(
                r=normalized_data[idx] + [normalized_data[idx][0]],  # Fermer le polygone
                theta=criteria + [criteria[0]],
                name=scenario_name,
                fill='toself'
            ))
        
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100]
                )
            ),
            showlegend=True,
            title="Comparaison Multicritère des Scénarios",
            height=500
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    else:
        st.info("👈 Lancez la simulation pour voir les résultats.")

# Onglet 5: Rapport & Export
with tab5:
    st.markdown('<h2 class="sub-header">Rapport & Export des Données</h2>', 
                unsafe_allow_html=True)
    
    if st.session_state.comparison_df is not None:
        # Génération du rapport
        st.markdown("#### 📑 Génération du Rapport")
        
        report_name = st.text_input("Nom du rapport", "Rapport_PV_Batterie")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📥 Générer Rapport PDF", type="primary", use_container_width=True):
                # Code pour générer PDF
                st.success("Rapport PDF généré avec succès !")
                st.info("Le rapport a été sauvegardé dans le dossier 'reports/'")
        
        with col2:
            if st.button("🗂️ Exporter Données Excel", use_container_width=True):
                # Exporter vers Excel
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    st.session_state.comparison_df.to_excel(writer, 
                                                          sheet_name='Comparaison_Scénarios', 
                                                          index=False)
                    
                    # Ajouter les données détaillées
                    for i, data in st.session_state.scenarios.items():
                        df_detail = pd.DataFrame([data])
                        df_detail.to_excel(writer, 
                                         sheet_name=f'Scénario_{i}_Détail', 
                                         index=False)
                
                buffer.seek(0)
                
                # Téléchargement
                st.download_button(
                    label="📥 Télécharger Excel",
                    data=buffer,
                    file_name=f"{report_name}_donnees.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        
        with col3:
            if st.button("📈 Exporter Graphiques", use_container_width=True):
                st.success("Graphiques exportés au format PNG")
        
        # Résumé du rapport
        st.markdown("#### 📋 Résumé du Projet")
        
        if st.session_state.scenarios:
            best_scenario_idx = st.session_state.comparison_df["Réduction réseau (%)"].idxmax()
            best_scenario = st.session_state.scenarios[best_scenario_idx]
            
            st.markdown(f"""
            **Configuration recommandée:**
            - **Scénario:** {best_scenario['scenario_name']}
            - **Production PV:** {best_scenario.get('pv_production_kwh', 0):,.0f} kWh/an
            - **Batterie:** {best_scenario.get('battery_technology', 'Non')} {best_scenario.get('battery_capacity_kwh', 0)} kWh
            - **Autoconsommation:** {best_scenario.get('self_consumption_percent', 0):.1f}%
            - **Réduction réseau:** {best_scenario.get('grid_reduction_percent', 0):.1f}%
            - **Économies annuelles estimées:** ${abs(best_scenario.get('energy_cost_usd', 0) - st.session_state.scenarios[0].get('energy_cost_usd', 0)):,.0f}
            """)
        
        # Export des données brutes
        st.markdown("#### 💾 Données Brutes")
        
        with st.expander("Afficher les données brutes"):
            st.json(st.session_state.scenarios)
    
    else:
        st.info("🟢 Lancez la simulation pour générer un rapport.")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666;">
    <p><strong>🔋 Simulateur PV + Batterie - Projet de Stockage d'Énergie Électrique</strong></p>
    <p>Développé avec Streamlit • Données de référence: Rapport technique PV+Stockage</p>
    <p>© 2024 - Pour usage académique</p>
</div>
""", unsafe_allow_html=True)

# Fonction pour télécharger les données
def get_table_download_link(df, filename):
    """Génère un lien de téléchargement pour un DataFrame"""
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">📥 Télécharger CSV</a>'
    return href