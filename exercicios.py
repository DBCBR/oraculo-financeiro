# --- Importação das Bibliotecas ---
import smtplib
from email.message import EmailMessage
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import pandas as pd
from datetime import datetime
import os  # BIBLIOTECA NOVA: Para mexer com arquivos do Windows

# --- Configuração do E-mail ---
EMAIL_REMETENTE = "davidbarcellos@gmail.com"
SENHA_APP = os.getenv("senha")  # Pegando a senha do .env
EMAIL_DESTINATARIO = "davidbarcellos@gmail.com"

def enviar_aviso(cotacao_atual):
    try:
        msg = EmailMessage()
        msg['Subject'] = f"\U0001F916 Dólar Hoje: R$ {cotacao_atual}"
        msg['From'] = EMAIL_REMETENTE
        msg['To'] = EMAIL_DESTINATARIO
        
        # Corpo do e-mail
        msg.set_content(f"""
                        Olá, Chefe!
                        O robõ acabou de rodar.
                        \U0001F4B5 Cotação atual do Dólar Comercial: R$ {cotacao_atual}
                        \U0001F4C5 Data: {datetime.now().strftime("%d/%m/%Y %H:%M")}
                        
                        O arquivo Excel no seu computador já foi atualizado com essa cotação.
                        
                        Att.
                        Seu Robô de Python \U0001F40D
                        """)
        
        # Conexão com o servidor SMTP do Gmail
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_REMETENTE, SENHA_APP)
            smtp.send_message(msg)
            print("\U0001F4E7 E-mail enviado com sucesso!")
            
    except Exception as e:
        print(f"\u274C Erro ao enviar e-mail: {e}")
        
# --- INÍCIO DO ROBÔ ---
opcoes = Options()
opcoes.add_argument("--headless") 
opcoes.add_argument("--disable-gpu")
print(f"\U0001F680 Iniciando o robô de cotação do Dólar...")

try:
    servico = Service(ChromeDriverManager().install())
    navegador = webdriver.Chrome(service=servico, options=opcoes)
    
    print("Iniciando coleta...")
    navegador.get("https://www.melhorcambio.com/dolar-hoje")
    cotacao = navegador.find_element(By.ID, 'comercial').get_attribute('value')
    cotacao_numero = float(cotacao.replace(",", "."))
    
    # Salvar no Excel (Lógica de Histórico)
    novo_dado = {
        "Data da Coleta": [datetime.now().strftime("%d/%m/%Y %H:%M")],
        "Moeda": ["Dólar"],
        "Valor": [cotacao_numero]
    }
    
    arquivo = "Historico_Dolar.xlsx"
    if os.path.exists(arquivo):
        pd.concat([pd.read_excel(arquivo), pd.DataFrame(novo_dado)], ignore_index=True).to_excel(arquivo, index=False)
    else:
        pd.DataFrame(novo_dado).to_excel(arquivo, index=False)
        
    print("Excel atualizado!")

    # --- A GRANDE NOVIDADE: DISPARAR O E-MAIL ---
    enviar_aviso(cotacao)

except Exception as erro:
    print(f"Erro no processo: {erro}")

finally:
    if 'navegador' in locals():
        navegador.quit()