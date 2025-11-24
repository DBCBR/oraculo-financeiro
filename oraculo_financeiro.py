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
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_KEY"))
MODELO_IA = "gemini-2.5-flash"

# --- 2. BANCO DE DADOS (SQL) ---
def init_db():
    """Cria a tabela no banco se ela não existir (Setup Inicial)"""
    conn = sqlite3.connect('historico_simulacoes.db')
    c = conn.cursor()
    # Linguagem SQL pura aqui dentro:
    c.execute('''
        CREATE TABLE IF NOT EXISTS simulacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_hora TEXT,
            valor_investido REAL,
            perfil TEXT,
            selic_dia REAL,
            recomendacao_ia TEXT
        )
    ''')
    conn.commit()
    conn.close()

def salvar_execucao(valor, perfil, selic, ia_text):
    """O Escriba: Grava o que aconteceu no banco"""
    conn = sqlite3.connect('historico_simulacoes.db')
    c = conn.cursor()
    data_agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    c.execute('''
        INSERT INTO simulacoes (data_hora, valor_investido, perfil, selic_dia, recomendacao_ia)
        VALUES (?, ?, ?, ?, ?)
    ''', (data_agora, valor, perfil, selic, ia_text))
    
    conn.commit()
    conn.close()

def carregar_historico():
    """O Historiador: Lê tudo o que está gravado"""
    conn = sqlite3.connect('historico_simulacoes.db')
    df = pd.read_sql_query("SELECT * FROM simulacoes ORDER BY id DESC", conn)
    conn.close()
    return df

# Inicializa o banco assim que o app liga
init_db()

# --- 3. MOTOR DE DADOS (API) ---
@st.cache_data(ttl=3600)
def buscar_dados_mercado():
    try:
        url = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados/ultimos/1?formato=json"
        resposta = requests.get(url)
        selic = float(resposta.json()[0]['valor'])
    except:
        selic = 11.25 

    cdi = selic - 0.10
    if selic > 10:
        media_lci = 88 
        media_cdb = 105 
    else:
        media_lci = 92
        media_cdb = 110
        
    return {"selic": selic, "cdi": cdi, "lci_padrao": media_lci, "cdb_padrao": media_cdb}

# --- 4. CÁLCULOS ---
CONCEITOS = {
    "Selic": "Taxa mãe da economia. Define o piso de rentabilidade.",
    "LCI/LCA": "Isento de IR. Foco em Imóveis/Agro.",
    "CDB": "Empréstimo bancário. Tem IR mas paga mais bruto."
}

def calcular_imposto_renda(dias):
    if dias <= 180: return 22.5
    elif dias <= 360: return 20.0
    elif dias <= 720: return 17.5
    else: return 15.0

def simular_cenarios(valor, dados_mercado, taxa_lci_user, taxa_cdb_user):
    resultados = []
    anos = [1, 2, 3, 4, 5]
    selic = dados_mercado['selic']
    cdi = dados_mercado['cdi']
    
    for ano in anos:
        dias = ano * 365
        aliquota_ir = calcular_imposto_renda(dias)
        
        bruto_selic = valor * ((1 + (selic/100)) ** ano)
        lucro_selic = bruto_selic - valor
        taxa_b3 = bruto_selic * 0.002 * ano
        liq_selic = bruto_selic - (lucro_selic * (aliquota_ir/100)) - taxa_b3
        
        taxa_efetiva_lci = cdi * (taxa_lci_user / 100)
        liq_lci = valor * ((1 + (taxa_efetiva_lci/100)) ** ano)
        
        taxa_efetiva_cdb = cdi * (taxa_cdb_user / 100)
        bruto_cdb = valor * ((1 + (taxa_efetiva_cdb/100)) ** ano)
        lucro_cdb = bruto_cdb - valor
        liq_cdb = bruto_cdb - (lucro_cdb * (aliquota_ir/100))
        
        resultados.append({
            "Prazo (Anos)": ano,
            "Tesouro Selic": round(liq_selic, 2),
            f"LCI ({taxa_lci_user}%)": round(liq_lci, 2),
            f"CDB ({taxa_cdb_user}%)": round(liq_cdb, 2)
        })
    return pd.DataFrame(resultados)

def gerar_analise_ia(df, perfil):
    txt = df.to_string(index=False)
    contexto = "Priorize SEGURANÇA" if perfil == "Conservador" else "Priorize RETORNO"
    
    prompt = f"""
    Você é um Consultor Financeiro Sênior.
    Tabela Líquida: {txt}
    Perfil: {perfil} ({contexto})
    Compare LCI vs CDB matematicamente e recomende a alocação.
    REGRAS: Sem LaTeX, sem cifrão solto. Use "R$ " com espaço. Seja breve.
    """
    try:
        model = genai.GenerativeModel(MODELO_IA)
        resp = model.generate_content(prompt).text
        return resp.replace("$", "\\$")
    except:
        return "IA Indisponível."

# --- 5. INTERFACE ---
st.set_page_config(page_title="Simulador SQL", page_icon="💾", layout="wide")

# --- ÁREA ADMIN (SECRET) ---
# Só aparece se clicar na checkbox na barra lateral
with st.sidebar:
    st.header("⚙️ Configurações")
    modo_admin = st.checkbox("Modo Administrativo (Ver Banco)")
    
    st.divider()
    dados = buscar_dados_mercado()
    st.markdown(f"Selic: `{dados['selic']}%`")

if modo_admin:
    st.title("🗄️ Banco de Dados do Oráculo")
    st.warning("Área restrita a analistas.")
    
    df_hist = carregar_historico()
    
    # Métricas do Negócio
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Total de Simulações", len(df_hist))
    if not df_hist.empty:
        media_inv = df_hist['valor_investido'].mean()
        col_b.metric("Ticket Médio", f"R$ {media_inv:,.2f}")
        perfil_top = df_hist['perfil'].mode()[0]
        col_c.metric("Perfil + Comum", perfil_top)
        
        st.dataframe(df_hist, use_container_width=True)
        
        # Botão para baixar o banco em Excel
        st.download_button("Baixar Dados em CSV", df_hist.to_csv(), "dados_oraculo.csv")
    else:
        st.info("Nenhuma simulação feita ainda.")
    
    st.stop() # Para de carregar o resto do site se estiver no modo admin

# --- ÁREA PÚBLICA (SIMULADOR) ---
st.title("💰 Simulador de Renda Fixa (Com Histórico)")

c1, c2 = st.columns([1, 2])

with c1:
    valor = st.number_input("Valor (R$)", 10000.0, step=1000.0)
    perfil = st.selectbox("Perfil", ["Conservador", "Moderado", "Arrojado"])
    taxa_lci = st.slider("LCI %", 80, 100, dados['lci_padrao'])
    taxa_cdb = st.slider("CDB %", 90, 150, dados['cdb_padrao'])
    btn = st.button("Simular", type="primary")

with c2:
    if btn:
        with st.spinner("Calculando e salvando no banco..."):
            df = simular_cenarios(valor, dados, taxa_lci, taxa_cdb)
            
            # Gráfico
            df_melt = df.melt('Prazo (Anos)', var_name='Ativo', value_name='Valor')
            fig = px.line(df_melt, x="Prazo (Anos)", y="Valor", color='Ativo')
            st.plotly_chart(fig, use_container_width=True)
            
            # IA
            analise = gerar_analise_ia(df, perfil)
            st.info(analise)
            
            # SALVAR NO BANCO (O Pulo do Gato)
            salvar_execucao(valor, perfil, dados['selic'], analise)
            st.toast("Simulação salva no banco de dados!", icon="💾")