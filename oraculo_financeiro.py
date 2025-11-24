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

# --- 2. BANCO DE DADOS (SQL) ---
def init_db():
    conn = sqlite3.connect('historico.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS simulacoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, valor REAL, perfil TEXT, selic REAL, banco TEXT, analise TEXT)''')
    conn.commit()
    conn.close()

def salvar_no_banco(valor, perfil, selic, banco, analise):
    conn = sqlite3.connect('historico.db')
    c = conn.cursor()
    data = datetime.now().strftime("%d/%m/%Y %H:%M")
    c.execute('INSERT INTO simulacoes (data, valor, perfil, selic, banco, analise) VALUES (?, ?, ?, ?, ?, ?)', 
              (data, valor, perfil, selic, banco, analise))
    conn.commit()
    conn.close()

def ler_banco():
    conn = sqlite3.connect('historico.db')
    df = pd.read_sql_query("SELECT * FROM simulacoes ORDER BY id DESC", conn)
    conn.close()
    return df

init_db()

# --- 3. DADOS DE MERCADO & BANCOS ---
@st.cache_data(ttl=3600)
def buscar_selic():
    try:
        url = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados/ultimos/1?formato=json"
        return float(requests.get(url).json()[0]['valor'])
    except: return 11.25

# VITRINE DE BANCOS (Seus dados de mercado)
def buscar_ofertas_bancos():
    return {
        "Média de Mercado": {"CDB": 105, "LCI": 90, "Obs": "Taxas padrão de grandes bancos"},
        "Banco Sofisa": {"CDB": 110, "LCI": 94, "Obs": "Liquidez diária forte"},
        "XP Investimentos": {"CDB": 130, "LCI": 96, "Obs": "Taxas promocionais (Novos Clientes)"},
        "Nubank / Inter": {"CDB": 100, "LCI": 88, "Obs": "Facilidade de app"},
        "Banco Master": {"CDB": 118, "LCI": 98, "Obs": "Foco em médio prazo"}
    }

# --- 4. CÁLCULOS E IA ---
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

def consultar_ia(df, perfil, banco_escolhido):
    try:
        txt = df.to_string(index=False)
        prompt = f"""
        Sou consultor financeiro. Cliente perfil: {perfil}. Banco: {banco_escolhido}.
        Tabela Líquida: {txt}
        1. Compare as ofertas (LCI vs CDB).
        2. Esse banco faz sentido para o perfil?
        Regra: SEM LaTeX. SEM $. Use "R$ ". Seja direto.
        """
        model = genai.GenerativeModel(MODELO_IA)
        return model.generate_content(prompt).text.replace("$", "\\$")
    except: return "IA Off."

# --- 5. GESTÃO DE PÁGINAS (SESSION STATE) ---
if 'pagina' not in st.session_state: st.session_state['pagina'] = 'quiz'
if 'perfil_usuario' not in st.session_state: st.session_state['perfil_usuario'] = 'Moderado'

# === TELA 1: O QUIZ (NOVIDADE) ===
def pagina_quiz():
    st.title("🕵️ Descubra seu Perfil")
    st.markdown("Responda 3 perguntas rápidas para calibrar a IA.")
    
    with st.form("quiz"):
        q1 = st.radio("1. Prazo do investimento:", ["Curto (Preciso sacar a qualquer hora)", "Médio (1-3 anos)", "Longo (Aposentadoria)"])
        q2 = st.radio("2. Reação a perdas:", ["Vendo tudo", "Aguardo", "Compro mais"])
        q3 = st.radio("3. Conhecimento:", ["Iniciante", "Intermediário", "Avançado"])
        
        if st.form_submit_button("🚀 Ir para o Simulador"):
            # Lógica simples
            score = 0
            if "Longo" in q1: score += 2
            if "Compro" in q2: score += 3
            if "Avançado" in q3: score += 2
            
            perfil = "Conservador"
            if score > 2: perfil = "Moderado"
            if score > 5: perfil = "Arrojado"
            
            st.session_state['perfil_usuario'] = perfil
            st.session_state['pagina'] = 'dashboard'
            st.rerun()

# === TELA 2: O DASHBOARD (SEU LAYOUT PREFERIDO) ===
def pagina_dashboard():
    selic = buscar_selic()
    ofertas = buscar_ofertas_bancos()
    perfil = st.session_state['perfil_usuario']
    
    # --- SIDEBAR (ADMIN) ---
    with st.sidebar:
        st.header(f"👤 Perfil: {perfil}")
        if st.button("Refazer Quiz"):
            st.session_state['pagina'] = 'quiz'
            st.rerun()
        st.divider()
        st.metric("Selic", f"{selic}%")
        modo_admin = st.toggle("Modo Admin 🔐")

    # Lógica Admin
    if modo_admin:
        st.title("🗄️ Dados Admin")
        df_db = ler_banco()
        if not df_db.empty:
            st.metric("Simulações", len(df_db))
            st.dataframe(df_db, use_container_width=True)
            st.download_button("Baixar CSV", df_db.to_csv(), "dados.csv")
        else: st.info("Vazio.")
        return

    # --- ÁREA PRINCIPAL (LAYOUT PRO [1, 2]) ---
    st.title("💰 Oráculo Financeiro")
    st.markdown(f"Simulador conectado ao Banco Central | Selic: **{selic}%**")

    # AQUI ESTÁ O SEU LAYOUT FAVORITO (COLUNAS 1 e 2)
    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("1. Configuração")
        
        # Seletor de Banco (NOVIDADE INTEGRADA NO LAYOUT ANTIGO)
        banco_sel = st.selectbox("Escolha o Banco", list(ofertas.keys()))
        dados_banco = ofertas[banco_sel]
        st.caption(f"ℹ️ {dados_banco['Obs']}")
        
        valor = st.number_input("Valor (R$)", 10000.0, step=1000.0)
        
        st.divider()
        st.subheader("2. Taxas")
        # Sliders puxam o valor do banco escolhido
        tx_lci = st.slider(f"LCI {banco_sel} %", 80, 120, dados_banco['LCI'])
        tx_cdb = st.slider(f"CDB {banco_sel} %", 90, 150, dados_banco['CDB'])
        
        btn = st.button("Simular", type="primary", use_container_width=True)

    with col2:
        if btn:
            with st.spinner("Processando..."):
                df = simular(valor, selic, tx_lci, tx_cdb)
                analise = consultar_ia(df, perfil, banco_sel)
                salvar_no_banco(valor, perfil, selic, banco_sel, analise)
                
                st.success("✅ Análise Pronta!")
                
                # Abas (O Visual Clean que você gosta)
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
            st.info(f"👈 Configure sua simulação com as taxas do **{banco_sel}**.")

# --- ROTEADOR ---
if st.session_state['pagina'] == 'quiz':
    pagina_quiz()
else:
    pagina_dashboard()