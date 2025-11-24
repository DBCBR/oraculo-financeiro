import streamlit as st
import pandas as pd
import google.generativeai as genai
import os
import plotly.express as px
import requests
import sqlite3
from datetime import datetime
from dotenv import load_dotenv

# --- 1. CONFIGURAÇÃO E AMBIENTE ---
st.set_page_config(page_title="Oráculo Hub", page_icon="🏦", layout="wide")
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_KEY"))
MODELO_IA = "gemini-2.5-flash"

# --- 2. BANCO DE DADOS (CORREÇÃO V2) ---
# Mudamos para 'simulacoes_v2' para corrigir o erro de colunas antigas automaticamente
def init_db():
    conn = sqlite3.connect('historico.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS simulacoes_v2 (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        data TEXT, 
        valor REAL, 
        perfil TEXT, 
        selic REAL, 
        banco TEXT, 
        analise TEXT)''')
    conn.commit()
    conn.close()

def salvar_no_banco(valor, perfil, selic, banco, analise):
    conn = sqlite3.connect('historico.db')
    c = conn.cursor()
    data = datetime.now().strftime("%d/%m/%Y %H:%M")
    c.execute('INSERT INTO simulacoes_v2 (data, valor, perfil, selic, banco, analise) VALUES (?, ?, ?, ?, ?, ?)', 
              (data, valor, perfil, selic, banco, analise))
    conn.commit()
    conn.close()

def ler_banco():
    conn = sqlite3.connect('historico.db')
    try:
        df = pd.read_sql_query("SELECT * FROM simulacoes_v2 ORDER BY id DESC", conn)
    except:
        df = pd.DataFrame() # Retorna vazio se não tiver tabela ainda
    conn.close()
    return df

init_db()

# --- 3. DADOS DE MERCADO ---
@st.cache_data(ttl=3600)
def buscar_dados_mercado():
    try:
        url = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados/ultimos/1?formato=json"
        selic = float(requests.get(url).json()[0]['valor'])
    except: selic = 11.25
    
    cdi = selic - 0.10
    return {"selic": selic, "cdi": cdi}

# VITRINE DE BANCOS (Inteligência de Mercado)
def buscar_ofertas_bancos():
    return {
        "Média de Mercado": {"CDB": 105, "LCI": 90, "Obs": "Taxas padrão de grandes bancos"},
        "Banco Sofisa": {"CDB": 110, "LCI": 94, "Obs": "Liquidez diária forte (110% CDI)"},
        "XP Investimentos": {"CDB": 130, "LCI": 96, "Obs": "Promoção novos clientes (Curto Prazo)"},
        "Nubank / Inter": {"CDB": 100, "LCI": 88, "Obs": "Facilidade de app (100% CDI)"},
        "Banco Master": {"CDB": 118, "LCI": 98, "Obs": "Foco em médio prazo (118% CDI)"}
    }

# --- 4. CÁLCULOS E IA ---
CONCEITOS = {
    "LCI/LCA": "Isento de IR. Geralmente rende menos % bruto, mas ganha no líquido.",
    "CDB": "Tem IR (tabela regressiva), mas costuma ter taxas brutas maiores."
}

def calcular_ir(dias):
    if dias <= 180: return 22.5
    elif dias <= 360: return 20.0
    elif dias <= 720: return 17.5
    else: return 15.0

def simular(valor, selic, tx_lci, tx_cdb):
    cdi = selic - 0.10
    res = []
    for ano in [1, 2, 3, 4, 5]:
        dias = ano * 365
        ir = calcular_ir(dias)
        
        # Tesouro Selic
        bruto_sel = valor * ((1 + (selic/100))**ano)
        liq_sel = bruto_sel - ((bruto_sel-valor)*(ir/100)) - (bruto_sel*0.002*ano)
        
        # LCI
        liq_lci = valor * ((1 + (cdi*(tx_lci/100)/100))**ano)
        
        # CDB
        bruto_cdb = valor * ((1 + (cdi*(tx_cdb/100)/100))**ano)
        liq_cdb = bruto_cdb - ((bruto_cdb-valor)*(ir/100))
        
        res.append({"Prazo (Anos)": ano, "Tesouro Selic": round(liq_sel, 2), "LCI/LCA": round(liq_lci, 2), "CDB Banco": round(liq_cdb, 2)})
    return pd.DataFrame(res)

def consultar_ia(df, perfil, banco):
    try:
        txt = df.to_string(index=False)
        prompt = f"""
        Sou consultor financeiro. Cliente perfil: {perfil}. Banco: {banco}.
        Tabela Líquida: {txt}
        1. Compare LCI vs CDB matematicamente.
        2. Esse banco faz sentido para o perfil?
        Regra: SEM LaTeX. SEM $. Use "R$ ". Seja direto.
        """
        model = genai.GenerativeModel(MODELO_IA)
        return model.generate_content(prompt).text.replace("$", "\\$")
    except: return "IA Off."

# --- 5. NAVEGAÇÃO (QUIZ -> DASHBOARD) ---
if 'pagina' not in st.session_state: st.session_state['pagina'] = 'quiz'
if 'perfil_usuario' not in st.session_state: st.session_state['perfil_usuario'] = 'Moderado'

# === TELA 1: QUIZ DE PERFIL ===
def pagina_quiz():
    st.title("🕵️ Perfil de Investidor")
    st.markdown("Responda rápido para personalizarmos sua experiência.")
    
    with st.form("quiz"):
        q1 = st.radio("Objetivo principal:", ["Liquidez (Reserva de Emergência)", "Aposentadoria (Longo Prazo)", "Multiplicar Capital (Médio Prazo)"])
        q2 = st.radio("Se o mercado cair 20%:", ["Entro em pânico", "Aguardo", "Compro mais"])
        
        if st.form_submit_button("🚀 Acessar Simulador"):
            score = 0
            if "Longo" in q1: score += 2
            if "Compro" in q2: score += 3
            
            perfil = "Conservador"
            if score >= 2: perfil = "Moderado"
            if score >= 4: perfil = "Arrojado"
            
            st.session_state['perfil_usuario'] = perfil
            st.session_state['pagina'] = 'dashboard'
            st.rerun()

# === TELA 2: DASHBOARD (SEU LAYOUT PREFERIDO RESTAURADO) ===
def pagina_dashboard():
    dados = buscar_dados_mercado()
    ofertas = buscar_ofertas_bancos()
    perfil = st.session_state['perfil_usuario']
    
    # --- SIDEBAR (Visual Original Restaurado) ---
    with st.sidebar:
        st.header("🏛️ Painel de Controle")
        
        # Métricas que você gostava
        col_s1, col_s2 = st.columns(2)
        col_s1.metric("Selic", f"{dados['selic']}%")
        col_s2.metric("CDI", f"{dados['cdi']:.2f}%")
        
        st.divider()
        st.info(f"👤 Perfil Ativo: **{perfil}**")
        if st.button("Refazer Quiz"):
            st.session_state['pagina'] = 'quiz'
            st.rerun()
            
        st.divider()
        modo_admin = st.toggle("Modo Admin 🔐")

    # Admin
    if modo_admin:
        st.title("🗄️ Dados Admin")
        df_db = ler_banco()
        if not df_db.empty:
            st.metric("Total Simulações", len(df_db))
            st.dataframe(df_db, use_container_width=True)
            st.download_button("📥 CSV", df_db.to_csv(), "dados.csv")
        else: st.info("Vazio.")
        return

    # --- ÁREA PRINCIPAL (Layout Pro [1, 1.5]) ---
    st.title("💼 Simulador Estratégico")
    st.markdown(f"Comparador de **LCI vs CDB** em tempo real.")

    col1, col2 = st.columns([1, 1.5], gap="large")

    with col1:
        st.subheader("1. Configuração")
        
        # Seletor de Banco (NOVIDADE)
        banco_sel = st.selectbox("Escolha o Banco", list(ofertas.keys()))
        dados_banco = ofertas[banco_sel]
        st.info(f"📢 {dados_banco['Obs']}")
        
        valor = st.number_input("Valor (R$)", 10000.0, step=1000.0)
        
        st.divider()
        st.subheader("2. Taxas")
        
        # Sliders Automáticos (Puxam do Banco escolhido)
        tx_lci = st.slider(f"LCI {banco_sel} %", 80, 120, dados_banco['LCI'], help=CONCEITOS['LCI/LCA'])
        tx_cdb = st.slider(f"CDB {banco_sel} %", 90, 150, dados_banco['CDB'], help=CONCEITOS['CDB'])
        
        btn = st.button("Simular", type="primary", use_container_width=True)

    with col2:
        if btn:
            with st.spinner("Analisando..."):
                # Cálculos
                df = simular(valor, dados['selic'], tx_lci, tx_cdb)
                
                # IA
                analise = consultar_ia(df, perfil, banco_sel)
                
                # Salvar (Tabela V2)
                salvar_no_banco(valor, perfil, dados['selic'], banco_sel, analise)
                
                st.success("✅ Análise Pronta!")
                
                # Abas (Visual Limpo Original)
                t1, t2, t3 = st.tabs(["📈 Gráfico", "📋 Tabela", "🤖 IA"])
                
                with t1:
                    df_melt = df.melt('Prazo (Anos)', var_name='Ativo', value_name='R$ Líquido')
                    fig = px.line(df_melt, x='Prazo (Anos)', y='R$ Líquido', color='Ativo', markers=True, template='plotly_white')
                    st.plotly_chart(fig, use_container_width=True)
                with t2:
                    st.dataframe(df, use_container_width=True, hide_index=True)
                with t3:
                    st.info(analise)
        else:
            st.info("👈 Ajuste as taxas do banco selecionado para simular.")

# --- ROTEADOR ---
if st.session_state['pagina'] == 'quiz':
    pagina_quiz()
else:
    pagina_dashboard()