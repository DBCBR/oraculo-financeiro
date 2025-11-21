import streamlit as st
import pandas as pd
import google.generativeai as genai
import os
import plotly.express as px
import requests
from dotenv import load_dotenv

# --- 1. CONFIGURAÇÃO E AMBIENTE ---
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_KEY"))
MODELO_IA = "gemini-2.5-flash"

# --- 2. MOTOR DE DADOS (INTEGRAÇÃO) ---
@st.cache_data(ttl=3600)
def buscar_dados_mercado():
    """
    Busca dados reais do Banco Central e estima taxas de mercado.
    Retorna um dicionário com Selic, CDI e médias de mercado.
    """
    try:
        # 1. Selic Meta (API BCB)
        url = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados/ultimos/1?formato=json"
        resposta = requests.get(url)
        selic = float(resposta.json()[0]['valor'])
    except:
        selic = 11.25 # Fallback de segurança

    cdi = selic - 0.10
    
    # 2. Inteligência de Mercado (Estimativa baseada na Selic)
    # Com Selic alta (>10%), bancos tendem a pagar menos % do CDI em isentos
    if selic > 10:
        media_lci = 88 # % do CDI
        media_cdb = 105 # % do CDI
    else:
        media_lci = 92
        media_cdb = 110
        
    return {
        "selic": selic,
        "cdi": cdi,
        "lci_padrao": media_lci,
        "cdb_padrao": media_cdb
    }

# --- 3. CONTEÚDO EDUCACIONAL ---
CONCEITOS = {
    "Selic": "Taxa mãe da economia. Define o rendimento da Poupança e Tesouro Selic.",
    "LCI/LCA": "Empréstimo para setor Imobiliário/Agro. Vantagem: ISENTO de Imposto de Renda. Geralmente rende menos % bruto, mas ganha no líquido.",
    "CDB": "Empréstimo para o Banco. Tem Imposto de Renda (tabela regressiva), mas costuma ter taxas brutas maiores.",
    "CDI": "Taxa que os bancos usam entre si. É a referência (benchmark) para LCI e CDB."
}

# --- 4. MOTOR DE CÁLCULO ---
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
        
        # Tesouro Selic (Com IR e Taxa B3)
        bruto_selic = valor * ((1 + (selic/100)) ** ano)
        lucro_selic = bruto_selic - valor
        taxa_b3 = bruto_selic * 0.002 * ano
        liq_selic = bruto_selic - (lucro_selic * (aliquota_ir/100)) - taxa_b3
        
        # LCI (Isenta)
        taxa_efetiva_lci = cdi * (taxa_lci_user / 100)
        liq_lci = valor * ((1 + (taxa_efetiva_lci/100)) ** ano)
        
        # CDB (Com IR)
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
    
    # Contexto do Perfil
    contexto_perfil = ""
    if perfil == "Conservador":
        contexto_perfil = "Cliente prioriza SEGURANÇA. Tem medo de travar o dinheiro e precisar dele. Prefere liquidez a rentabilidade excessiva."
    elif perfil == "Arrojado":
        contexto_perfil = "Cliente prioriza LUCRO MÁXIMO. Aceita travar o dinheiro por 5 anos se ganhar mais. Renda Fixa é só para bater a inflação."
    else:
        contexto_perfil = "Cliente busca equilíbrio entre tempo e retorno."

    prompt = f"""
    Você é um Consultor Financeiro Sênior.
    Analise a tabela de projeção (Líquida de impostos):
    {txt}
    
    Perfil: {perfil} ({contexto_perfil})
    
    Missão:
    1. Compare LCI vs CDB matematicamente.
    2. Recomende a alocação ideal para o perfil.
    
    REGRAS VISUAIS OBRIGATÓRIAS (CRÍTICO):
    - NÃO use formatação matemática (LaTeX).
    - NÃO use cifrão ($) para dinheiro. Escreva apenas "reais" ou "R$ " (com espaço).
    - Use listas (bullet points) para organizar.
    """
    
    try:
        model = genai.GenerativeModel(MODELO_IA)
        resposta = model.generate_content(prompt).text
        
        # --- A LIMPEZA BLINDADA ---
        # Aqui trocamos qualquer cifrão que a IA tenha deixado escapar por um cifrão "escapado" (\$)
        # O Streamlit entende \$ como "texto cifrão" e não como "fórmula matemática".
        resposta_limpa = resposta.replace("$", "\\$")
        
        return resposta_limpa
    except:
        return "IA Indisponível no momento."

# --- 5. INTERFACE (STREAMLIT) ---
st.set_page_config(page_title="Simulador Pro 3.5", page_icon="💰", layout="wide")

# Sidebar com Dados de Mercado
dados = buscar_dados_mercado()

with st.sidebar:
    st.header("🏦 Dados de Mercado")
    st.markdown(f"**Selic Hoje:** `{dados['selic']}%`")
    st.markdown(f"**CDI Hoje:** `{dados['cdi']:.2f}%`")
    st.success("Dados atualizados automaticamente via Banco Central.")
    st.divider()
    st.caption("Desenvolvido por David Barcellos Cardoso")

st.title("💰 Simulador Estratégico de Renda Fixa")
st.markdown("Descubra se vale mais a pena pagar imposto no CDB ou pegar a isenção da LCI.")

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("1. Seus Dados")
    valor = st.number_input("Valor a Investir (R$)", value=10000.0, step=1000.0)
    perfil = st.selectbox("Seu Perfil", ["Conservador", "Moderado", "Arrojado"])
    
    st.divider()
    st.subheader("2. Taxas Encontradas")
    st.caption("Preenchemos com a média do mercado, mas você pode ajustar se achar algo melhor.")
    
    # Sliders já começam com o valor "inteligente" sugerido pelo Python
    taxa_lci = st.slider("LCI/LCA (% do CDI)", 80, 110, dados['lci_padrao'], help=CONCEITOS["LCI/LCA"])
    taxa_cdb = st.slider("CDB (% do CDI)", 90, 150, dados['cdb_padrao'], help=CONCEITOS["CDB"])
    
    btn_calcular = st.button("Analisar Cenários", type="primary", use_container_width=True)

with col2:
    if btn_calcular:
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
        with st.spinner("Consultando o estrategista..."):
            analise = gerar_analise_ia(df, perfil)
            st.markdown(analise)
            
    else:
        st.info("👈 Ajuste as taxas e clique em 'Analisar Cenários' para começar.")
        st.markdown("""
        ### 💡 Como funciona?
        1. O sistema busca a **Selic** direto no Banco Central.
        2. Calculamos automaticamente o imposto de renda regressivo.
        3. Comparamos **LCI Isenta** vs **CDB Tributado**.
        
        Clique em **Simular** para ver o resultado.
        """)