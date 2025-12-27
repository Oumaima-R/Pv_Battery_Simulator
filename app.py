import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime
import io
import os

# Configuration de la page
st.set_page_config(
    page_title="Simulateur PV + Batterie - Analyse Complète",
    page_icon="🔋",
    layout="wide"
)

# Titre principal
st.title("🔋 SIMULATEUR PV + BATTERIE - ANALYSE COMPLÈTE")
st.markdown("**Analyse détaillée avec tous les indicateurs de performance**")

# ===== DONNÉES DE BASE DU RAPPORT =====
BASE_DATA = {
    "annual_consumption": 4479.3,  # kWh/an
    "pv_production": 3562.5,  # kWh/an
    "pv_coverage": 79.5,  # %
    "battery_capacity": 5.5,  # kWh
    "battery_usable": 4.44,  # kWh
    "autonomy": 8.7,  # heures
    "night_coverage": 102.5,  # %
    "self_consumption": "85-90",  # %
    "grid_reduction": 70,  # %
}

# ===== DONNÉES DÉTAILLÉES PAR SCÉNARIO =====
SCENARIOS_DATA = {
    "S0": {
        "name": "Scénario 0",
        "description": "Réseau seul (référence)",
        "pv_energy": 0,
        "battery_charge": 0,
        "battery_discharge": 0,
        "grid_import": 4479.3,
        "grid_export": 0,
        "energy_lost": 0,
        "self_consumption_rate": 0,
        "total_coverage": 0,
        "grid_reduction": 0,
        "cost": 671.9,
        "tech": "Aucune"
    },
    "S1": {
        "name": "Scénario 1",
        "description": "PV seul",
        "pv_energy": 3562.5,
        "battery_charge": 0,
        "battery_discharge": 0,
        "grid_import": 1791.7,
        "grid_export": 712.5,
        "energy_lost": 106.3,
        "self_consumption_rate": 65,
        "total_coverage": 79.5,
        "grid_reduction": 60,
        "cost": 268.8,
        "tech": "PV seul"
    },
    "S2": {
        "name": "Scénario 2",
        "description": "PV + Plomb",
        "pv_energy": 3562.5,
        "battery_charge": 1425.0,
        "battery_discharge": 1211.3,
        "grid_import": 895.9,
        "grid_export": 356.3,
        "energy_lost": 213.7,
        "self_consumption_rate": 75,
        "total_coverage": 87.5,
        "grid_reduction": 80,
        "cost": 134.4,
        "tech": "Plomb-acide"
    },
    "S3": {
        "name": "Scénario 3",
        "description": "PV + Li-ion",
        "pv_energy": 3562.5,
        "battery_charge": 1425.0,
        "battery_discharge": 1353.8,
        "grid_import": 671.9,
        "grid_export": 178.1,
        "energy_lost": 106.3,
        "self_consumption_rate": 85,
        "total_coverage": 91.5,
        "grid_reduction": 85,
        "cost": 100.8,
        "tech": "Lithium-ion"
    },
    "S4": {
        "name": "Scénario 4",
        "description": "Optimisé",
        "pv_energy": 3562.5,
        "battery_charge": 1425.0,
        "battery_discharge": 1425.0,
        "grid_import": 447.9,
        "grid_export": 89.1,
        "energy_lost": 71.3,
        "self_consumption_rate": 90,
        "total_coverage": 94.5,
        "grid_reduction": 90,
        "cost": 67.2,
        "tech": "Li-ion optimisé"
    }
}

# ===== SIDEBAR =====
with st.sidebar:
    st.header("⚙️ PARAMÈTRES")
    
    # Paramètres de base
    st.subheader("🏠 Consommation")
    annual_consumption = st.number_input(
        "Consommation annuelle (kWh)",
        value=BASE_DATA["annual_consumption"],
        min_value=1000.0,
        max_value=20000.0
    )
    
    st.subheader("☀️ Système PV")
    pv_power = st.slider("Puissance PV (kWc)", 1.0, 10.0, 2.5)
    pv_pr = st.slider("Performance Ratio (%)", 50, 90, 75)
    
    st.subheader("🔋 Système de stockage")
    battery_tech = st.selectbox(
        "Technologie",
        ["Lithium-ion", "Plomb-acide", "Aucune"]
    )
    
    if battery_tech != "Aucune":
        battery_capacity = st.slider(
            "Capacité batterie (kWh)", 
            1.0, 20.0, 
            BASE_DATA["battery_capacity"] if battery_tech == "Lithium-ion" else 10.0
        )
    
    # Bouton simulation
    if st.button("🚀 LANCER L'ANALYSE", type="primary", use_container_width=True):
        st.session_state.analyzed = True

# ===== FONCTIONS DE VISUALISATION =====
def create_energy_flow_chart():
    """Crée un graphique des flux énergétiques"""
    fig = go.Figure()
    
    # Données pour S4 (optimisé)
    scenario = SCENARIOS_DATA["S4"]
    
    # Diagramme en barres empilées
    categories = ["PV", "Batterie", "Réseau"]
    positive = [scenario["pv_energy"], scenario["battery_discharge"], 0]
    negative = [0, -scenario["battery_charge"], -scenario["grid_import"]]
    
    fig.add_trace(go.Bar(
        name='Production/Apport',
        x=categories,
        y=positive,
        marker_color=['orange', 'green', 'gray']
    ))
    
    fig.add_trace(go.Bar(
        name='Consommation/Stockage',
        x=categories,
        y=negative,
        marker_color=['darkorange', 'darkgreen', 'darkgray']
    ))
    
    fig.update_layout(
        title="📊 Flux Énergétiques - Scénario Optimisé (S4)",
        barmode='relative',
        yaxis_title="Énergie (kWh/an)",
        template="plotly_white",
        height=400
    )
    
    return fig

def create_scenario_comparison_chart():
    """Crée un graphique de comparaison des scénarios"""
    scenarios = ["S0", "S1", "S2", "S3", "S4"]
    
    # Données pour le graphique
    grid_import = [SCENARIOS_DATA[s]["grid_import"] for s in scenarios]
    self_cons = [SCENARIOS_DATA[s]["self_consumption_rate"] for s in scenarios]
    coverage = [SCENARIOS_DATA[s]["total_coverage"] for s in scenarios]
    reduction = [SCENARIOS_DATA[s]["grid_reduction"] for s in scenarios]
    
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=("Importation Réseau", "Autoconsommation", 
                       "Couverture Totale", "Réduction Réseau"),
        vertical_spacing=0.15,
        horizontal_spacing=0.15
    )
    
    # Graphique 1: Importation réseau
    fig.add_trace(
        go.Bar(
            x=scenarios,
            y=grid_import,
            name="Import réseau",
            marker_color=["red", "orange", "yellow", "lightgreen", "green"]
        ),
        row=1, col=1
    )
    
    # Graphique 2: Autoconsommation
    fig.add_trace(
        go.Scatter(
            x=scenarios,
            y=self_cons,
            mode='lines+markers',
            name="Autoconsommation",
            line=dict(color='blue', width=3),
            marker=dict(size=10)
        ),
        row=1, col=2
    )
    
    # Graphique 3: Couverture totale
    fig.add_trace(
        go.Scatter(
            x=scenarios,
            y=coverage,
            mode='lines+markers',
            name="Couverture",
            line=dict(color='green', width=3),
            marker=dict(size=10)
        ),
        row=2, col=1
    )
    
    # Graphique 4: Réduction réseau
    fig.add_trace(
        go.Bar(
            x=scenarios,
            y=reduction,
            name="Réduction",
            marker_color=["gray", "lightblue", "blue", "darkblue", "navy"]
        ),
        row=2, col=2
    )
    
    fig.update_layout(
        title="📈 Comparaison des Scénarios (S0 à S4)",
        showlegend=False,
        height=600,
        template="plotly_white"
    )
    
    # Mise à jour des axes
    fig.update_yaxes(title_text="kWh/an", row=1, col=1)
    fig.update_yaxes(title_text="%", row=1, col=2)
    fig.update_yaxes(title_text="%", row=2, col=1)
    fig.update_yaxes(title_text="%", row=2, col=2)
    
    return fig

def create_technology_comparison_chart():
    """Crée un graphique de comparaison des technologies"""
    tech_data = {
        "Technologie": ["Aucune", "PV seul", "Plomb-acide", "Lithium-ion", "Li-ion optimisé"],
        "Coût annuel (€)": [671.9, 268.8, 134.4, 100.8, 67.2],
        "Autonomie (h)": [0, 0, 7.2, 8.7, 9.5],
        "Rendement (%)": [0, 65, 75, 85, 90],
        "Durée de vie (ans)": [0, 25, 5, 10, 12]
    }
    
    df = pd.DataFrame(tech_data)
    
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=("Coût annuel", "Autonomie", "Rendement", "Durée de vie"),
        specs=[[{"type": "bar"}, {"type": "bar"}],
               [{"type": "bar"}, {"type": "bar"}]]
    )
    
    # Coût annuel
    fig.add_trace(
        go.Bar(
            x=df["Technologie"],
            y=df["Coût annuel (€)"],
            name="Coût",
            marker_color="red"
        ),
        row=1, col=1
    )
    
    # Autonomie
    fig.add_trace(
        go.Bar(
            x=df["Technologie"],
            y=df["Autonomie (h)"],
            name="Autonomie",
            marker_color="blue"
        ),
        row=1, col=2
    )
    
    # Rendement
    fig.add_trace(
        go.Bar(
            x=df["Technologie"],
            y=df["Rendement (%)"],
            name="Rendement",
            marker_color="green"
        ),
        row=2, col=1
    )
    
    # Durée de vie
    fig.add_trace(
        go.Bar(
            x=df["Technologie"],
            y=df["Durée de vie (ans)"],
            name="Durée vie",
            marker_color="orange"
        ),
        row=2, col=2
    )
    
    fig.update_layout(
        title="🔧 Comparaison des Technologies de Stockage",
        showlegend=False,
        height=600,
        template="plotly_white"
    )
    
    return fig

def create_radar_chart():
    """Crée un graphique radar pour comparaison multicritère"""
    scenarios = ["S0", "S1", "S2", "S3", "S4"]
    criteria = ["Réduction", "Autoconsommation", "Couverture", "Économie", "Autonomie"]
    
    # Normalisation des données
    normalized_data = {}
    
    for s in scenarios:
        data = SCENARIOS_DATA[s]
        values = [
            data["grid_reduction"] / 100,  # Normalisé 0-1
            data["self_consumption_rate"] / 100,
            data["total_coverage"] / 100,
            (671.9 - data["cost"]) / 671.9,  # Économie relative
            (9.5 if s == "S4" else 8.7 if s == "S3" else 7.2 if s == "S2" else 0) / 10
        ]
        normalized_data[s] = values
    
    fig = go.Figure()
    
    colors = ["red", "orange", "yellow", "lightgreen", "green"]
    
    for i, s in enumerate(scenarios):
        fig.add_trace(go.Scatterpolar(
            r=normalized_data[s] + [normalized_data[s][0]],  # Fermer le polygone
            theta=criteria + [criteria[0]],
            name=f"Scénario {s[-1]}",
            line=dict(color=colors[i], width=3),
            fill='toself',
            opacity=0.3
        ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 1]
            )
        ),
        title="🎯 Analyse Multicritère des Scénarios",
        showlegend=True,
        height=500,
        template="plotly_white"
    )
    
    return fig

# ===== ONGLETS PRINCIPAUX =====
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 INDICATEURS CLÉS",
    "📈 COMPARAISON SCÉNARIOS",
    "🔧 TECHNOLOGIES",
    "🎯 ANALYSE MULTICRITÈRE",
    "📥 EXPORT RAPPORT"
])

with tab1:
    st.header("📊 INDICATEURS DE PERFORMANCE PAR SCÉNARIO")
    
    # Tableau des indicateurs
    indicators_data = []
    for key, data in SCENARIOS_DATA.items():
        indicators_data.append({
            "Scénario": key,
            "Description": data["description"],
            "PV (kWh)": data["pv_energy"],
            "Batt. Charge (kWh)": data["battery_charge"],
            "Batt. Décharge (kWh)": data["battery_discharge"],
            "Réseau Import (kWh)": data["grid_import"],
            "Réseau Export (kWh)": data["grid_export"],
            "Pertes (kWh)": data["energy_lost"],
            "Autoconso. (%)": data["self_consumption_rate"],
            "Couverture (%)": data["total_coverage"],
            "Réduc. (%)": data["grid_reduction"]
        })
    
    df_indicators = pd.DataFrame(indicators_data)
    st.dataframe(df_indicators, use_container_width=True)
    
    # Graphique des flux énergétiques
    st.subheader("📊 Flux Énergétiques")
    st.plotly_chart(create_energy_flow_chart(), use_container_width=True)
    
    # Métriques clés
    st.subheader("🎯 Indicateurs Clés du Système")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Consommation annuelle", f"{BASE_DATA['annual_consumption']:,.1f} kWh")
        st.metric("Production PV", f"{BASE_DATA['pv_production']:,.1f} kWh")
    
    with col2:
        st.metric("Couverture PV", f"{BASE_DATA['pv_coverage']}%")
        st.metric("Autoconsommation", f"{BASE_DATA['self_consumption']}%")
    
    with col3:
        st.metric("Batterie (utilisable)", f"{BASE_DATA['battery_usable']} kWh")
        st.metric("Autonomie", f"{BASE_DATA['autonomy']} h")
    
    with col4:
        st.metric("Couverture nuit", f"{BASE_DATA['night_coverage']}%")
        st.metric("Réduction réseau", f"{BASE_DATA['grid_reduction']}%")

with tab2:
    st.header("📈 COMPARAISON DÉTAILLÉE DES SCÉNARIOS")
    
    st.plotly_chart(create_scenario_comparison_chart(), use_container_width=True)
    
    # Analyse détaillée par scénario
    st.subheader("📋 Analyse par Scénario")
    
    selected_scenario = st.selectbox(
        "Choisir un scénario pour analyse détaillée",
        list(SCENARIOS_DATA.keys()),
        format_func=lambda x: f"{x}: {SCENARIOS_DATA[x]['name']}"
    )
    
    if selected_scenario:
        data = SCENARIOS_DATA[selected_scenario]
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Importation réseau", f"{data['grid_import']:,.1f} kWh")
            st.metric("Autoconsommation", f"{data['self_consumption_rate']}%")
            st.metric("Pertes système", f"{data['energy_lost']:,.1f} kWh")
        
        with col2:
            st.metric("Réduction réseau", f"{data['grid_reduction']}%")
            st.metric("Couverture totale", f"{data['total_coverage']}%")
            st.metric("Coût annuel", f"{data['cost']:,.1f} €")
        
        # Diagramme circulaire
        if data['pv_energy'] > 0:
            labels = ['Autoconsommation', 'Export réseau', 'Pertes', 'Charge batterie']
            values = [
                data['pv_energy'] * data['self_consumption_rate'] / 100,
                data['grid_export'],
                data['energy_lost'],
                data['battery_charge']
            ]
            
            fig_pie = go.Figure(data=[go.Pie(
                labels=labels,
                values=values,
                hole=0.4,
                marker_colors=['green', 'blue', 'red', 'orange']
            )])
            
            fig_pie.update_layout(title=f"Répartition Production PV - {data['name']}")
            st.plotly_chart(fig_pie, use_container_width=True)

with tab3:
    st.header("🔧 COMPARAISON DES TECHNOLOGIES DE STOCKAGE")
    
    st.plotly_chart(create_technology_comparison_chart(), use_container_width=True)
    
    # Tableau comparatif technologies
    st.subheader("📋 Caractéristiques Techniques")
    
    tech_comparison = {
        "Paramètre": ["DoD typique", "Rendement", "Durée de vie", "Cycles", "Coût", "Encombrement", "Maintenance"],
        "Aucune": ["-", "-", "-", "-", "0 €", "-", "-"],
        "PV seul": ["-", "65-70%", "25 ans", "-", "1.2 €/W", "Faible", "Faible"],
        "Plomb-acide": ["50%", "80-85%", "3-5 ans", "500-800", "200 €/kWh", "Élevé", "Élevée"],
        "Lithium-ion": ["80-90%", "90-95%", "8-12 ans", "3000-6000", "500 €/kWh", "Faible", "Faible"],
        "Li-ion optimisé": ["85%", "95%", "10-15 ans", "4000-8000", "450 €/kWh", "Très faible", "Nulle"]
    }
    
    df_tech = pd.DataFrame(tech_comparison)
    st.dataframe(df_tech, use_container_width=True)
    
    # Recommandation
    st.subheader("✅ Recommandation Technologique")
    
    st.success("""
    **Technologie recommandée : LITHIUM-ION**
    
    **Pourquoi ?**
    - ✓ Rendement élevé (95%)
    - ✓ Longue durée de vie (10-15 ans)
    - ✓ Faible encombrement
    - ✓ Pas de maintenance
    - ✓ DoD élevé (85%)
    - ✓ Meilleur rapport performance/coût à long terme
    """)

with tab4:
    st.header("🎯 ANALYSE MULTICRITÈRE ET RECOMMANDATION")
    
    st.plotly_chart(create_radar_chart(), use_container_width=True)
    
    # Calcul du score global
    st.subheader("🏆 Classement des Scénarios")
    
    scores = []
    for key, data in SCENARIOS_DATA.items():
        score = (
            data["grid_reduction"] * 0.3 +  # Poids 30%
            data["self_consumption_rate"] * 0.25 +  # Poids 25%
            data["total_coverage"] * 0.2 +  # Poids 20%
            ((671.9 - data["cost"]) / 671.9 * 100) * 0.15 +  # Poids 15%
            (8.7 if "S3" in key else 9.5 if "S4" in key else 7.2 if "S2" in key else 0) * 10 * 0.1  # Poids 10%
        )
        scores.append({
            "Scénario": key,
            "Nom": data["name"],
            "Score": round(score, 1),
            "Technologie": data["tech"]
        })
    
    df_scores = pd.DataFrame(scores).sort_values("Score", ascending=False)
    df_scores["Rang"] = range(1, len(df_scores) + 1)
    
    st.dataframe(df_scores[["Rang", "Scénario", "Nom", "Score", "Technologie"]], use_container_width=True)
    
    # Meilleur scénario
    best = df_scores.iloc[0]
    
    st.subheader("🏅 SCÉNARIO RECOMMANDÉ")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.success(f"""
        **{best['Nom']} ({best['Scénario']})**
        
        **Score global : {best['Score']}/100**
        
        **Performance :**
        - Réduction réseau : {SCENARIOS_DATA[best['Scénario']]['grid_reduction']}%
        - Autoconsommation : {SCENARIOS_DATA[best['Scénario']]['self_consumption_rate']}%
        - Couverture totale : {SCENARIOS_DATA[best['Scénario']]['total_coverage']}%
        - Économie annuelle : {671.9 - SCENARIOS_DATA[best['Scénario']]['cost']:,.1f} €
        """)
    
    with col2:
        # Diagramme de score
        categories = ['Réduction', 'Autoconso.', 'Couverture', 'Économie', 'Autonomie']
        values = [
            SCENARIOS_DATA[best['Scénario']]['grid_reduction'],
            SCENARIOS_DATA[best['Scénario']]['self_consumption_rate'],
            SCENARIOS_DATA[best['Scénario']]['total_coverage'],
            ((671.9 - SCENARIOS_DATA[best['Scénario']]['cost']) / 671.9) * 100,
            85 if best['Scénario'] == "S4" else 75
        ]
        
        fig_score = go.Figure(data=go.Scatterpolar(
            r=values,
            theta=categories,
            fill='toself',
            line=dict(color='green', width=3)
        ))
        
        fig_score.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            showlegend=False,
            height=300,
            width=300
        )
        
        st.plotly_chart(fig_score, use_container_width=True)

with tab5:
    st.header("📥 EXPORT DU RAPPORT COMPLET")
    
    # Chemin des Téléchargements Windows
    downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")
    
    # 1. Rapport Excel complet
    st.subheader("📊 Exporter les Données Excel")
    
    # Créer un DataFrame complet
    full_data = []
    for key, data in SCENARIOS_DATA.items():
        full_data.append({
            "Scénario": key,
            "Nom": data["name"],
            "Description": data["description"],
            "Énergie_PV_kWh": data["pv_energy"],
            "Batterie_Charge_kWh": data["battery_charge"],
            "Batterie_Décharge_kWh": data["battery_discharge"],
            "Réseau_Import_kWh": data["grid_import"],
            "Réseau_Export_kWh": data["grid_export"],
            "Énergie_Perte_kWh": data["energy_lost"],
            "Taux_Autoconsommation_%": data["self_consumption_rate"],
            "Taux_Couverture_%": data["total_coverage"],
            "Réduction_Réseau_%": data["grid_reduction"],
            "Coût_Annuel_€": data["cost"],
            "Technologie": data["tech"]
        })
    
    df_full = pd.DataFrame(full_data)
    
    # Convertir en Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Feuille 1: Résultats scénarios
        df_full.to_excel(writer, sheet_name='Scénarios', index=False)
        
        # Feuille 2: Indicateurs système
        system_data = {
            "Paramètre": list(BASE_DATA.keys()),
            "Valeur": list(BASE_DATA.values()),
            "Unité": ["kWh/an", "kWh/an", "%", "kWh", "kWh", "heures", "%", "%", "%"]
        }
        pd.DataFrame(system_data).to_excel(writer, sheet_name='Système', index=False)
        
        # Feuille 3: Comparaison technologies
        df_tech.to_excel(writer, sheet_name='Technologies', index=False)
    
    excel_data = output.getvalue()
    excel_filename = f"rapport_pv_batterie_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    excel_path = os.path.join(downloads_path, excel_filename)
    
    st.download_button(
        label="📥 Télécharger Excel Complet",
        data=excel_data,
        file_name=excel_filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        help="Le fichier sera sauvegardé dans votre dossier Téléchargements"
    )
    
    # 2. Rapport PDF/Text
    st.subheader("📄 Générer le Rapport d'Analyse")
    
    rapport_content = f"""
    RAPPORT D'ANALYSE - SYSTÈME PV + BATTERIE
    =========================================
    
    Date : {datetime.now().strftime('%d/%m/%Y %H:%M')}
    
    1. PARAMÈTRES DU SYSTÈME
    -----------------------
    • Consommation annuelle : {BASE_DATA['annual_consumption']:,.1f} kWh
    • Production PV : {BASE_DATA['pv_production']:,.1f} kWh
    • Taux couverture PV : {BASE_DATA['pv_coverage']}%
    • Batterie : {BASE_DATA['battery_capacity']} kWh (Li-ion)
    • Énergie utilisable : {BASE_DATA['battery_usable']} kWh
    • Autonomie : {BASE_DATA['autonomy']} heures
    • Couverture besoins nocturnes : {BASE_DATA['night_coverage']}%
    • Autoconsommation estimée : {BASE_DATA['self_consumption']}%
    • Réduction injection réseau : {BASE_DATA['grid_reduction']}%
    
    2. ANALYSE DES SCÉNARIOS
    -----------------------
    """
    
    for key, data in SCENARIOS_DATA.items():
        rapport_content += f"""
    {data['name']} ({key}) :
      • Énergie PV : {data['pv_energy']:,.1f} kWh
      • Batterie (charge/décharge) : {data['battery_charge']:,.1f} / {data['battery_discharge']:,.1f} kWh
      • Réseau (import/export) : {data['grid_import']:,.1f} / {data['grid_export']:,.1f} kWh
      • Pertes : {data['energy_lost']:,.1f} kWh
      • Autoconsommation : {data['self_consumption_rate']}%
      • Couverture totale : {data['total_coverage']}%
      • Réduction réseau : {data['grid_reduction']}%
      • Coût annuel : {data['cost']:,.1f} €
        """
    
    best_scenario = df_scores.iloc[0]
    best_data = SCENARIOS_DATA[best_scenario['Scénario']]
    
    rapport_content += f"""
    
    3. RECOMMANDATION
    -----------------
    Scénario recommandé : {best_scenario['Nom']} ({best_scenario['Scénario']})
    Score global : {best_scenario['Score']}/100
    
    Configuration :
    • Système PV : {pv_power} kWc
    • Batterie : {best_data['tech']}
    • Autonomie : {BASE_DATA['autonomy']} heures
    
    Performance :
    • Réduction appel réseau : {best_data['grid_reduction']}%
    • Autoconsommation : {best_data['self_consumption_rate']}%
    • Couverture énergétique : {best_data['total_coverage']}%
    • Économie annuelle : {671.9 - best_data['cost']:,.1f} €
    
    4. CONCLUSION
    -------------
    Le scénario {best_scenario['Scénario']} offre le meilleur compromis entre :
    - Performance énergétique
    - Réduction des coûts
    - Autonomie du système
    - Retour sur investissement
    
    Cette configuration permet une réduction de 90% de l'appel au réseau
    tout en maximisant l'autoconsommation de l'énergie produite.
    """
    
    txt_filename = f"rapport_analyse_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
    txt_path = os.path.join(downloads_path, txt_filename)
    
    st.download_button(
        label="📥 Télécharger Rapport Texte",
        data=rapport_content.encode('utf-8'),
        file_name=txt_filename,
        mime="text/plain",
        help="Le rapport sera sauvegardé dans votre dossier Téléchargements"
    )
    
    # 3. Résumé graphique
    st.subheader("🖼️ Exporter les Graphiques")
    
    if st.button("📸 Capturer les Graphiques"):
        st.info(f"Les graphiques peuvent être capturés via :")
        st.markdown("""
        1. **Capture d'écran** (Win + Shift + S)
        2. **Téléchargement direct** (clic droit sur chaque graphique → Save image)
        3. **Export PDF** via l'impression de la page (Ctrl + P)
        
        **Conseil :** Utilisez la fonction de capture Windows pour sauvegarder chaque graphique.
        """)
    
    # Affichage du chemin
    st.subheader("📁 Emplacement des Fichiers")
    st.info(f"""
    **Vos fichiers seront téléchargés dans :**
    ```
    {downloads_path}
    ```
    
    **Fichiers générés :**
    1. `{excel_filename}` - Données complètes Excel
    2. `{txt_filename}` - Rapport d'analyse texte
    
    **Pour y accéder rapidement :**
    - Ouvrez l'Explorateur de fichiers
    - Allez dans "Téléchargements" dans la barre latérale
    - Ou collez ce chemin : `{downloads_path}`
    """)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; font-size: 0.9rem;">
    <p><strong>🔋 Simulateur PV + Batterie - Analyse Complète des Performances</strong></p>
    <p>Tous les indicateurs énergétiques • Comparaison 5 scénarios • Recommandation optimale</p>
    <p>© 2024 - Projet de stockage d'énergie électrique</p>
</div>
""", unsafe_allow_html=True)

# Initialisation de l'état
if 'analyzed' not in st.session_state:
    st.session_state.analyzed = False

# Message d'accueil
if not st.session_state.analyzed:
    st.info("👈 **Configurez les paramètres dans la sidebar et cliquez sur 'LANCER L'ANALYSE'**")
