import os
import smtplib
import time
import pandas as pd
import google.generativeai as genai
from email.message import EmailMessage
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

# --- 1. CONFIGURAÇÕES INICIAIS ---
load_dotenv() # Carrega senhas do .env

# Configuração da IA
genai.configure(api_key=os.getenv("GEMINI_KEY"))
MODELO_IA = "gemini-2.5-flash" # Usando sua versão Pro

# Configuração do E-mail
EMAIL_REMETENTE = "davidbarcellos@gmail.com"
SENHA_EMAIL = os.getenv("senha")
EMAIL_DESTINATARIO = "davidbarcellos@gmail.com"

# Configuração Financeira
INVESTIMENTO = 1000.00
ANOS = 2
TAXA_SELIC_ATUAL = 11.25

def consultar_tesouro():
    """Parte 1: RPA - Coleta Inteligente v2.0"""
    print("🕵️ Iniciando coleta refinada...")
    
    opcoes = Options()
    opcoes.add_argument("--headless")
    opcoes.add_argument("--disable-gpu")
    opcoes.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    servico = Service(ChromeDriverManager().install())
    navegador = webdriver.Chrome(service=servico, options=opcoes)
    
    lista_final = []
    
    try:
        navegador.get("https://www.tesourodireto.com.br/titulos/precos-e-taxas.htm")
        time.sleep(10)
        
        elementos = navegador.find_elements(By.TAG_NAME, "tr")
        
        for item in elementos:
            texto = item.text
            if not texto: continue
            
            if "Selic" in texto or "IPCA+" in texto:
                palavras = texto.replace("\n", " ").split(" ")
                
                # 1. Tentar extrair o ANO de vencimento (geralmente é um número tipo 2029, 2035)
                ano_vencimento = "-"
                for p in palavras:
                    if p.isdigit() and int(p) > 2024: # Se for um ano futuro
                        ano_vencimento = p
                        break
                
                # 2. Extrair a Taxa
                taxa_encontrada = 0.0
                for p in palavras:
                    if "%" in p:
                        v = p.replace("%", "").replace(",", ".")
                        try:
                            val = float(v)
                            if 0 < val < 20: taxa_encontrada = val
                            break
                        except: continue
                
                if taxa_encontrada > 0:
                    nome = " ".join(palavras[:3])
                    
                    # --- A GRANDE MUDANÇA MATEMÁTICA ---
                    if "Selic" in nome:
                        # Soma a taxa do site (0.05%) com a Selic Economia (11.25%)
                        taxa_final_calculo = taxa_encontrada + TAXA_SELIC_ATUAL
                        tipo_rentabilidade = "Nominal (Já inclui Selic)"
                    else:
                        # IPCA mantemos a taxa real
                        taxa_final_calculo = taxa_encontrada 
                        tipo_rentabilidade = "Real + Inflação (IPCA)"

                    # Simulação de Retorno (Bruta)
                    bruto = INVESTIMENTO * ((1 + (taxa_final_calculo/100)) ** ANOS)
                    
                    lista_final.append({
                        "Título": nome,
                        "Vencimento": ano_vencimento,
                        "Taxa Site": f"{taxa_encontrada}%",
                        "Rentabilidade Considerada": f"{taxa_final_calculo:.2f}% ({tipo_rentabilidade})",
                        "Valor Final Aprox.": f"R$ {bruto:.2f}"
                    })
                    
    except Exception as e:
        print(f"❌ Erro na coleta: {e}")
    finally:
        navegador.quit()
        
    return pd.DataFrame(lista_final)

def analisar_com_ia(df):
    """Parte 2: Cérebro - Análise Estratégica v2.0"""
    print("🧠 Enviando dados refinados para o Gemini...")
    
    tabela_str = df.to_string(index=False)
    
    prompt = f"""
    Você é um Consultor Financeiro Pessoal para o David (Conservador).
    Objetivo: Investir R$ {INVESTIMENTO} para resgatar em {ANOS} anos exatos.
    
    Dados do Mercado Hoje:
    {tabela_str}
    
    Instruções de Análise:
    1. **O Dilema do Prazo:** Compare o ano de vencimento do título com o prazo do David (daqui a 2 anos). 
    2. **Risco de Mercado:** Se indicar um título IPCA+ longo (ex: 2035/2045) para um prazo curto (2 anos), ALERTE sobre o risco de marcação a mercado (perda se vender antes).
    3. **Segurança:** Se o Tesouro Selic estiver pagando bem (agora os dados incluem a taxa de 11.25%), considere ele como opção mais segura para curto prazo.
    
    Sua resposta deve ser o corpo de um e-mail curto, direto e com recomendação final clara.
    """
    
    model = genai.GenerativeModel(MODELO_IA)
    resposta = model.generate_content(prompt)
    return resposta.text

def enviar_email(analise_ia):
    """Parte 3: Comunicação - Envia o resultado"""
    print("📧 Enviando e-mail...")
    try:
        msg = EmailMessage()
        msg['Subject'] = "💰 Relatório Diário: Oportunidades no Tesouro"
        msg['From'] = EMAIL_REMETENTE
        msg['To'] = EMAIL_DESTINATARIO
        msg.set_content(analise_ia)
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_REMETENTE, SENHA_EMAIL)
            smtp.send_message(msg)
        print("✅ E-mail enviado com sucesso!")
        
    except Exception as e:
        print(f"❌ Erro no envio de e-mail: {e}")

# --- ORQUESTRAÇÃO (MAIN) ---
if __name__ == "__main__":
    start_time = time.time()
    
    # 1. Coletar
    df_dados = consultar_tesouro()
    
    if not df_dados.empty:
        print(f"   -> Encontradas {len(df_dados)} oportunidades.")
        
        # 2. Analisar
        texto_analise = analisar_com_ia(df_dados)
        
        # 3. Enviar
        enviar_email(texto_analise)
    else:
        print("⚠️ Nenhuma taxa encontrada. O site pode ter mudado ou bloqueado.")
        
    print(f"🏁 Processo finalizado em {time.time() - start_time:.2f} segundos.")