import google.generativeai as genai
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

# --- CONFIGURAÇÃO ---
# Substitua pela sua chave ou use os.getenv("GEMINI_KEY")
CHAVE_API = os.getenv("GEMINI_KEY") 

if not CHAVE_API:
    print("⚠️ Erro: Chave API não encontrada. Configure a variável ou cole a chave.")
    exit()

genai.configure(api_key=CHAVE_API)

# 1. Carregar os dados que o robô gerou
try:
    df = pd.read_excel("Dados_Tesouro.xlsx")
    print("✅ Dados carregados do Excel.")
except:
    print("❌ Não achei o arquivo 'Dados_Tesouro.xlsx'. Rode o robô de coleta primeiro!")
    exit()

# 2. Engenharia de Prompt (A Mágica)
# Transformamos a tabela em texto para a IA ler
tabela_texto = df.to_string(index=False)

prompt_do_sistema = f"""
Você é um Consultor Financeiro Sênior especializado em Renda Fixa brasileira.
Seu cliente é conservador, avesso a riscos e busca proteção de patrimônio.

Abaixo estão as taxas coletadas HOJE do site do Tesouro Direto:
---
{tabela_texto}
---

REGRAS DE ANÁLISE OBRIGATÓRIAS:
1. **Atenção à Selic:** O valor mostrado na tabela para o 'Tesouro Selic' é apenas a taxa EXTRA (spread). A taxa Selic base da economia hoje é de 11.25%. Some isso mentalmente para avaliar o retorno real (aprox 11.35% total).
2. **IPCA+:** Considere que taxas reais acima de 6% são historicamente excelentes no Brasil.
3. O cliente quer investir R$ 1.000,00 com foco em 2 anos.

Sua Missão:
Escreva um e-mail curto para o David (máximo 3 parágrafos).
- Diga qual é a MELHOR oportunidade matemática da lista.
- Explique por que ela vence as outras.
- Use tom profissional, encorajador e use emojis financeiros.
"""

# 3. Chamando o Cérebro
print("🤖 A IA está analisando os dados... aguarde...")

model = genai.GenerativeModel('gemini-2.5-flash') # Modelo rápido e eficiente
resposta = model.generate_content(prompt_do_sistema)

print("\n" + "="*40)
print("📧 E-MAIL GERADO PELA IA:")
print("="*40)
print(resposta.text)