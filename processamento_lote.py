"""
-------------------------------------------------------------------------
NOME DO SCRIPT: sistema_logistico_v3.py
AUTOR: David
DATA: 12/01/2026
DESCRIÇÃO: 
    Calcula fretes em lote baseado em regras de peso e urgência.
    Processa listas de dicionários e gera relatórios financeiros.
-------------------------------------------------------------------------
"""

# 1. IMPORTAÇÕES (Bibliotecas externas)
# import pandas as pd  <-- (Usaremos na próxima aula)
import math # Exemplo: caso precisasse arredondar números complexos

# 2. CONSTANTES E CONFIGURAÇÕES (O "Painel de Controle")
# Se a taxa mudar ano que vem, você só altera aqui, e o código todo atualiza.
FRETE_BASE = 10.00
CUSTO_KM_EXTRA = 2.00
ADICIONAL_DISTANCIA = 20.00
LIMITE_DISTANCIA_KM = 100
LIMITE_PESO_KG = 20.0
MULTIPLICADOR_URGENCIA = 2

# 3. FUNÇÕES (Definições de Lógica)
# (Por enquanto deixaremos vazio, mas é aqui que você criaria ferramentas personalizadas)

# 4. ENTRADA DE DADOS (Input / Leitura de Arquivos)
# Simulação de dados vindos de uma API ou Excel
dados_pedidos = [
    {"id": 1, "peso": 4.0, "urgente": False},
    {"id": 2, "peso": 12.0, "urgente": True},
    {"id": 3, "peso": 25.0, "urgente": False},
    {"id": 4, "peso": 2.0, "urgente": True}
]

distancia_entrega = 150 # Exemplo de input

# 5. EXECUÇÃO PRINCIPAL (Processamento / ETL)
def main():
    print("\n>>> INICIANDO PROCESSAMENTO DE CARGAS <<<\n")
    
    faturamento_total = 0.00
    
    for pedido in dados_pedidos:
        # Extração de variáveis para facilitar leitura
        peso = pedido["peso"]
        urgente = pedido["urgente"]
        id_pedido = pedido["id"]
        
        # --- Lógica de Validação ---
        if peso <= 0 or peso > LIMITE_PESO_KG:
            print(f"[!] Pedido #{id_pedido} REJEITADO: Problema de peso ({peso}kg)")
            continue
            
        # --- Lógica de Cálculo ---
        custo_pedido = 0.0
        
        # Regra do Peso
        if peso <= 5:
            custo_pedido = FRETE_BASE
        else:
            excedente = peso - 5
            custo_pedido = FRETE_BASE + (excedente * CUSTO_KM_EXTRA)
            
        # Regra da Distância
        if distancia_entrega > LIMITE_DISTANCIA_KM:
            custo_pedido += ADICIONAL_DISTANCIA
            
        # Regra da Urgência
        if urgente:
            custo_pedido *= MULTIPLICADOR_URGENCIA
            print(f"    -> Pedido #{id_pedido} (URGENTE) processado.")
        else:
            print(f"    -> Pedido #{id_pedido} (NORMAL) processado.")
            
        # Acumulação
        faturamento_total += custo_pedido

    # 6. SAÍDA DE DADOS (Output / Relatórios)
    print("-" * 40)
    print(f"TOTAL FATURADO: R$ {faturamento_total:.2f}")
    print("-" * 40)
    print(">>> PROCESSAMENTO CONCLUÍDO <<<")

# Bloco de Segurança (Good Practice)
# Isso garante que esse código só rode se você clicar no Play, 
# e não se ele for importado por outro sistema.
if __name__ == "__main__":
    main()