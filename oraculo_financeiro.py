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
st.set_page_config(page_title="Simulador Pro 3.5", page_icon="💰", layout="wide")
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_KEY"))
MODELO_IA = "gemini-2.5-flash"

# --- 2. BANCO DE DADOS (SQL) ---
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

# Inicia o banco ao carregar
init_db()

# --- 3. MOTOR DE DADOS (INTEGRAÇÃO) ---
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

# --- 4. CONTEÚDO EDUCACIONAL ---
CONCEITOS = {
    "Selic": "Taxa mãe da economia. Define o rendimento da Poupança e Tesouro Selic.",
    "LCI/LCA": "Isento de IR. Geralmente rende menos % bruto, mas ganha no líquido.",
    "CDB": "Tem IR (tabela regressiva), mas costuma ter taxas brutas maiores.",
    "CDI": "Referência (benchmark) para LCI e CDB."
}

# --- 5. MOTOR DE CÁLCULO ---
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
        
        # Tesouro Selic
        bruto_selic = valor * ((1 + (selic/100)) ** ano)
        lucro_selic = bruto_selic - valor
        taxa_b3 = bruto_selic * 0.002 * ano
        liq_selic = bruto_selic - (lucro_selic * (aliquota_ir/100)) - taxa_b3
        
        # LCI
        taxa_efetiva_lci = cdi * (taxa_lci_user / 100)
        liq_lci = valor * ((1 + (taxa_efetiva_lci/100)) ** ano)
        
        # CDB
        taxa_efetiva_cdb = cdi * (taxa_cdb_user / 100)
        bruto_cdb = valor * ((1 + (taxa_efetiva_cdb/100)) ** ano)
        lucro_cdb = bruto_cdb - valor
        liq_cdb = bruto_cdb - (lucro_cdb * (aliquota_ir/100))
        
        resultados.append({
            "Prazo (Anos)": ano,
            "Tesouro Selic": round(liq_selic, 2),
            f"LCI ({taxa_lci_user}% CDI)": round(liq_lci, 2),
            f"CDB ({taxa_cdb_user}% CDI)": round(liq_cdb, 2)
        })
        
    return pd.DataFrame(resultados)

def gerar_analise_ia(df, perfil):
    txt = df.to_string(index=False)
    
    contexto_perfil = ""
    if perfil == "Conservador":
        contexto_perfil = "Cliente prioriza SEGURANÇA. Tem medo de travar o dinheiro."
    elif perfil == "Arrojado":
        contexto_perfil = "Cliente prioriza LUCRO MÁXIMO. Aceita travar o dinheiro por 5 anos."
    else:
        contexto_perfil = "Cliente busca equilíbrio."

    prompt = f"""
    Consultor Financeiro Sênior.
    Tabela Líquida: {txt}
    Perfil: {perfil} ({contexto_perfil})
    
    1. Compare LCI vs CDB matematicamente.
    2. Recomende a alocação.
    
    REGRAS VISUAIS:
    - NÃO use LaTeX.
    - NÃO use cifrão ($) para dinheiro. Escreva "R$ " com espaço.
    - Use bullet points.
    """
    
    try:
        model = genai.GenerativeModel(MODELO_IA)
        resposta = model.generate_content(prompt).text
        return resposta.replace("$", "\\$")
    except:
        return "IA Indisponível."

# --- 6. INTERFACE (STREAMLIT) ---

# Sidebar
dados = buscar_dados_mercado()

with st.sidebar:
    st.header("🏦 Dados de Mercado")
    st.markdown(f"**Selic Hoje:** `{dados['selic']}%`")
    st.markdown(f"**CDI Hoje:** `{dados['cdi']:.2f}%`")
    st.success("Dados atualizados via Banco Central.")
    st.divider()
    
    # --- NOVIDADE: MODO ADMIN ---
    st.caption("Área do Analista")
    modo_admin = st.toggle("Modo Admin (Ver Banco) 🔐")
    
    st.divider()
    st.caption("Desenvolvido por David Barcellos Cardoso")


# LÓGICA DE EXIBIÇÃO: ADMIN OU USUÁRIO
if modo_admin:
    # === TELA DO ADMIN ===
    st.title("🗄️ Database Administrator")
    st.markdown("Monitoramento de simulações em tempo real.")
    
    df_db = ler_banco()
    
    if not df_db.empty:
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("Total Simulações", len(df_db))
        kpi2.metric("Ticket Médio", f"R$ {df_db['valor'].mean():,.2f}")
        kpi3.metric("Perfil Principal", df_db['perfil'].mode()[0] if not df_db['perfil'].empty else "N/A")
        
        st.dataframe(df_db, use_container_width=True, hide_index=True)
        st.download_button("📥 Baixar CSV", df_db.to_csv(), "historico.csv")
    else:
        st.info("Banco de dados vazio.")

else:
    # === TELA DO USUÁRIO (SEU LAYOUT PREFERIDO) ===
    st.title("💰 Simulador Estratégico de Renda Fixa")
    st.markdown("Descubra se vale mais a pena pagar imposto no CDB ou pegar a isenção da LCI.")

    col1, col2 = st.columns([1, 2]) # MANTIDO O LAYOUT [1, 2]

    with col1:
        st.subheader("1. Seus Dados")
        valor = st.number_input("Valor a Investir (R$)", value=10000.0, step=1000.0)
        perfil = st.selectbox("Seu Perfil", ["Conservador", "Moderado", "Arrojado"])
        
        st.divider()
        st.subheader("2. Taxas Encontradas")
        st.caption("Preenchemos com a média do mercado, mas você pode ajustar se achar algo melhor.")
        
        taxa_lci = st.slider("LCI/LCA (% do CDI)", 80, 110, dados['lci_padrao'], help=CONCEITOS["LCI/LCA"])
        taxa_cdb = st.slider("CDB (% do CDI)", 90, 150, dados['cdb_padrao'], help=CONCEITOS["CDB"])
        
        btn_calcular = st.button("Analisar Cenários", type="primary", use_container_width=True)

    with col2:
        if btn_calcular:
            with st.spinner("Processando..."):
                # Cálculos
                df = simular_cenarios(valor, dados, taxa_lci, taxa_cdb)
                
                # Gráfico
                st.subheader("📈 Evolução Patrimonial")
                df_melt = df.melt('Prazo (Anos)', var_name='Produto', value_name='R$ Líquido')
                fig = px.line(df_melt, x="Prazo (Anos)", y="R$ Líquido", color='Produto', markers=True, template="plotly_white")
                st.plotly_chart(fig, use_container_width=True)
                
                # Tabela
                with st.expander("Ver Tabela Detalhada (Valores Líquidos)"):
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    
                # IA
                st.divider()
                st.subheader("🤖 O Veredito da IA")
                analise = gerar_analise_ia(df, perfil)
                st.markdown(analise)
                
                # --- NOVIDADE: SALVAR NO BANCO ---
                salvar_no_banco(valor, perfil, dados['selic'], analise)
                
        else:
            st.info("👈 Ajuste as taxas e clique em 'Analisar Cenários' para começar.")
            st.markdown("""
            ### 💡 Como funciona?
            1. O sistema busca a **Selic** direto no Banco Central.
            2. Calculamos automaticamente o imposto de renda regressivo.
            3. Comparamos **LCI Isenta** vs **CDB Tributado**.
            
            Clique em **Simular** para ver o resultado.
            """)