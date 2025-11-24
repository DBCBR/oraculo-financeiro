import streamlit as st
import pandas as pd
import google.generativeai as genai
import os
import plotly.express as px
import requests
import sqlite3
from datetime import datetime
from dotenv import load_dotenv

# --- 1. CONFIGURAÇÃO VISUAL (LAYOUT WIDE) ---
st.set_page_config(page_title="Simulador Pro SQL", page_icon="🏛️", layout="wide")
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_KEY"))
MODELO_IA = "gemini-2.5-flash"

# --- 2. BANCO DE DADOS (SQL) - MANTIDO ---
def init_db():
    conn = sqlite3.connect('historico.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS simulacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT,
            valor REAL,
            perfil TEXT,
            selic REAL,
            analise TEXT
        )
    ''')
    conn.commit()
    conn.close()

def salvar_no_banco(valor, perfil, selic, analise):
    conn = sqlite3.connect('historico.db')
    c = conn.cursor()
    data = datetime.now().strftime("%d/%m/%Y %H:%M")
    c.execute('INSERT INTO simulacoes (data, valor, perfil, selic, analise) VALUES (?, ?, ?, ?, ?)', 
              (data, valor, perfil, selic, analise))
    conn.commit()
    conn.close()

def ler_banco():
    conn = sqlite3.connect('historico.db')
    df = pd.read_sql_query("SELECT * FROM simulacoes ORDER BY id DESC", conn)
    conn.close()
    return df

# Inicializa o banco ao abrir
init_db()

# --- 3. DADOS DE MERCADO (API) ---
@st.cache_data(ttl=3600)
def buscar_mercado():
    try:
        url = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados/ultimos/1?formato=json"
        selic = float(requests.get(url).json()[0]['valor'])
    except:
        selic = 11.25 # Fallback
    
    cdi = selic - 0.10
    # Inteligência de Mercado para setar os Sliders
    if selic > 10:
        lci_padrao, cdb_padrao = 88, 105
    else:
        lci_padrao, cdb_padrao = 92, 110
        
    return {"selic": selic, "cdi": cdi, "lci_def": lci_padrao, "cdb_def": cdb_padrao}

dados = buscar_mercado()

# --- 4. MOTOR DE CÁLCULO ---
def calcular_ir(dias):
    if dias <= 180: return 22.5
    elif dias <= 360: return 20.0
    elif dias <= 720: return 17.5
    else: return 15.0

def simular(valor, selic, cdi, tx_lci, tx_cdb):
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
        
        res.append({
            "Prazo (Anos)": ano,
            "Tesouro Selic": round(liq_sel, 2),
            "LCI/LCA": round(liq_lci, 2),
            "CDB Banco": round(liq_cdb, 2)
        })
    return pd.DataFrame(res)

def consultar_ia(df, perfil):
    try:
        txt = df.to_string(index=False)
        prompt = f"""
        Sou consultor financeiro. Cliente perfil: {perfil}.
        Tabela de retornos líquidos:
        {txt}
        
        Responda: Qual a melhor alocação matemática (LCI vs CDB)?
        Regra: NÃO use LaTeX. NÃO use $. Use "R$ ". Seja direto.
        """
        model = genai.GenerativeModel(MODELO_IA)
        return model.generate_content(prompt).text.replace("$", "\\$")
    except:
        return "IA em manutenção."

# --- 5. INTERFACE (FRONTEND PRO) ---

# --- BARRA LATERAL (Sidebar Bonita) ---
with st.sidebar:
    st.header("🏛️ Painel de Controle")
    
    # Métricas Visuais (Muito melhor que texto puro)
    col_s1, col_s2 = st.columns(2)
    col_s1.metric("Selic", f"{dados['selic']}%")
    col_s2.metric("CDI", f"{dados['cdi']:.2f}%")
    
    st.divider()
    st.caption("Área do Analista")
    modo_admin = st.toggle("Ativar Modo Admin 🔐")

# --- LÓGICA DE EXIBIÇÃO ---

if modo_admin:
    # === TELA DO ADMIN ===
    st.title("🗄️ Database Administrator")
    st.markdown("Monitoramento de simulações em tempo real.")
    
    df_db = ler_banco()
    
    if not df_db.empty:
        # Dashboard Admin com KPIs
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("Total Simulações", len(df_db))
        kpi2.metric("Ticket Médio", f"R$ {df_db['valor'].mean():,.2f}")
        kpi3.metric("Perfil Principal", df_db['perfil'].mode()[0])
        
        st.dataframe(df_db, use_container_width=True, hide_index=True)
        st.download_button("📥 Baixar Dados (CSV)", df_db.to_csv(), "historico.csv")
    else:
        st.info("Banco de dados vazio.")

else:
    # === TELA DO USUÁRIO (Layout Pro) ===
    st.title("💼 Simulador Estratégico de Renda Fixa")
    st.markdown(f"**Análise Inteligente com IA** | Baseado na Selic de {dados['selic']}%")
    
    # Layout Pro: Duas Colunas bem divididas
    col_input, col_result = st.columns([1, 1.5], gap="large")
    
    with col_input:
        st.subheader("1. Configure o Aporte")
        valor = st.number_input("Valor do Investimento (R$)", value=10000.0, step=1000.0)
        perfil = st.selectbox("Seu Perfil de Risco", ["Conservador", "Moderado", "Arrojado"])
        
        st.divider()
        st.subheader("2. Taxas de Mercado")
        
        tx_lci = st.slider("LCI/LCA (% CDI)", 80, 100, dados['lci_def'])
        tx_cdb = st.slider("CDB (% CDI)", 90, 140, dados['cdb_def'])
        
        calcular = st.button("🚀 Executar Simulação", type="primary", use_container_width=True)

    with col_result:
        if calcular:
            with st.spinner("Processando cenários e salvando no banco..."):
                # 1. Calcular
                df_res = simular(valor, dados['selic'], dados['cdi'], tx_lci, tx_cdb)
                
                # 2. IA
                analise = consultar_ia(df_res, perfil)
                
                # 3. Salvar (SQL)
                salvar_no_banco(valor, perfil, dados['selic'], analise)
                
                # 4. Exibir Resultados com ABAS (O Visual Clean)
                st.success("✅ Análise Concluída e Salva!")
                
                tab1, tab2, tab3 = st.tabs(["📈 Gráfico", "📋 Tabela", "🤖 Parecer IA"])
                
                with tab1:
                    df_melt = df_res.melt('Prazo (Anos)', var_name='Ativo', value_name='Valor')
                    fig = px.line(df_melt, x='Prazo (Anos)', y='Valor', color='Ativo', markers=True, template='plotly_white')
                    st.plotly_chart(fig, use_container_width=True)
                
                with tab2:
                    st.dataframe(df_res, use_container_width=True, hide_index=True)
                    
                with tab3:
                    st.info(analise)
        
        else:
            st.info("👈 Preencha os dados para simular.")