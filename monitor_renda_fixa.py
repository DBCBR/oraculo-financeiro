from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import pandas as pd
import time

# --- CONFIGURAÇÕES DE SIMULAÇÃO ---
INVESTIMENTO = 1000.00 
ANOS = 2 

# --- CONFIGURAÇÃO DA "CAMUFLAGEM" DO ROBÔ ---
opcoes = Options()
# IMPORTANTE: Deixei o headless DESATIVADO (comentado) para você ver o site abrindo
# opcoes.add_argument("--headless") 
opcoes.add_argument("--start-maximized") # Abre a tela cheia
opcoes.add_argument("--disable-blink-features=AutomationControlled") # Tenta esconder que é automação

# O "Pulo do Gato": User-Agent (A identidade do navegador)
opcoes.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

print("⏳ Iniciando Analista de Investimentos (Modo Visual)...")
servico = Service(ChromeDriverManager().install())
navegador = webdriver.Chrome(service=servico, options=opcoes)

try:
    print("1. Acessando Tesouro Direto...")
    navegador.get("https://www.tesourodireto.com.br/titulos/precos-e-taxas.htm")
    
    print("   -> Aguardando carregamento (10s)...")
    time.sleep(10) # Espera "bruta" para garantir

    # Tenta fechar cookies
    try:
        navegador.find_element(By.ID, "onetrust-accept-btn-handler").click()
    except:
        pass

    print("2. Lendo a tabela (Estratégia Arrastão)...")
    
    # MUDANÇA AQUI: Em vez de procurar classes específicas, pegamos TODAS as linhas de tabela
    elementos = navegador.find_elements(By.TAG_NAME, "tr")
    
    # Debug: Vamos ver quantas linhas ele achou
    print(f"   -> Encontrei {len(elementos)} linhas na página.")

    lista_final = []

    for item in elementos:
        texto = item.text
        # Se a linha estiver vazia, pula
        if not texto:
            continue

        # Filtro Conservador (Procura palavras-chave no texto da linha)
        if "Selic" in texto or "IPCA+" in texto:
            # O texto geralmente vem assim: "Tesouro Selic 2029 R$ 14.000,00 10,50% ..."
            # Vamos quebrar por espaço ou nova linha
            
            # Regra de Extração de Taxa (Procura o %)
            taxa_encontrada = 0.0
            palavras = texto.replace("\n", " ").split(" ")
            
            for p in palavras:
                if "%" in p:
                    # Limpa o valor (tira %, troca vírgula)
                    valor_limpo = p.replace("%", "").replace(",", ".")
                    try:
                        taxa_encontrada = float(valor_limpo)
                        # Filtro de segurança: Taxa de juros no Brasil é entre 4 e 20%. 
                        # Se pegar "100%" ou "0.1%" pode ser erro de leitura.
                        if taxa_encontrada > 3 and taxa_encontrada < 20:
                            break 
                    except:
                        continue
            
            if taxa_encontrada > 0:
                # Pega o nome do título (geralmente são as 3 primeiras palavras da linha)
                # Ex: "Tesouro IPCA+ 2029"
                nome_titulo = " ".join(palavras[:3]) 
                
                # Simulação Financeira
                bruto = INVESTIMENTO * ((1 + (taxa_encontrada/100)) ** ANOS)
                lucro = bruto - INVESTIMENTO
                
                lista_final.append({
                    "Título": nome_titulo,
                    "Taxa (%)": taxa_encontrada,
                    "Lucro (2 anos)": f"R$ {lucro:.2f}"
                })

    # Resultado
    if len(lista_final) > 0:
        df = pd.DataFrame(lista_final).sort_values(by="Taxa (%)", ascending=False)
        print("\n" + "="*60)
        print(f"📊 RELATÓRIO TESOURO DIRETO (Investimento: R$ {INVESTIMENTO})")
        print("="*60)
        print(df.to_string(index=False))
        print("="*60)
        df.to_excel("Dados_Tesouro.xlsx", index=False)
    else:
        print("⚠️ Ainda não encontrei. Pode ser que o site não use tabela (<tr>).")
        print("   -> Dica: Tente aumentar o tempo de espera ou verifique se a página carregou.")

except Exception as e:
    print(f"❌ Erro: {e}")

finally:
    # Input para não fechar na sua cara, assim você vê se deu erro na tela
    input("Pressione ENTER para encerrar o robô...")
    navegador.quit()
    