"""
-------------------------------------------------------------------------
NOME: analisador_vendas.py
DESCRIÇÃO: 
    Lê uma planilha Excel de vendas, calcula o faturamento por produto
    e gera o faturamento total da loja.
-------------------------------------------------------------------------
"""

# 1. IMPORTAÇÕES
import pandas as pd  # 'pd' é o apelido universal para Pandas
import os # Para verificar se o arquivo existe

# 2. CONSTANTES
ARQUIVO_VENDAS = "vendas.xlsx"
META_FATURAMENTO = 2000.00  # Meta de faturamento para o mês

# 3. FUNÇÕES
def carregar_dados(caminho_arquivo):
    """Carrega os dados de vendas do arquivo Excel."""
    if not os.path.exists(caminho_arquivo):
        raise FileNotFoundError(f"O arquivo {caminho_arquivo} não foi encontrado.")

    try:
        tabela = pd.read_excel(caminho_arquivo, engine='openpyxl')
        return tabela
    except Exception as e:
        raise RuntimeError(f"Erro ao ler o arquivo Excel: {e}")
    
# 4. EXECUÇÃO PRINCIPAL
def main():
    print("\n>> INICIANDO ANÁLISE DE VENDAS <<\n")
    
    # Passo 1: Carregar os dados
    df_vendas = carregar_dados(ARQUIVO_VENDAS)
    
    if df_vendas is None:
        return
    
    # Passo 2: Visualizar os dados carregados (Sanity Check)
    print("--- Dados Carregados ---")
    print(df_vendas.head(), "\n")
    print("-" * 40)
    
    # Passo 3: Criar uma COLUNA NOVA calculada
    df_vendas["Total_Item"] = df_vendas["Valor"] * df_vendas["Quantidade"]
    df_limpo = df_vendas[df_vendas["Quantidade"] > 0]
    # Passo 4: Calcular o faturamento total
    faturamento_bruto = df_limpo["Total_Item"].sum()
    total_itens_vendidos = df_limpo["Quantidade"].sum()
    
    # Passo 5: Relatório Gerencial
    print("\n--- RELATÓRIO FINAL ---")
    print(df_limpo[["Produto", "Total_Item"]])
    
    # --- NOVO BLOCO: EXPORTAÇÃO (AQUI ESTÁ O DINHEIRO) ---
    print("\n[Genarando arquivo Excel final...]")
    
    # Vamos salvar o DataFrame completo (com a coluna nova) num arquivo novo
    # index=False serve para não salvar aquela coluna de números (0, 1, 2...) do lado esquerdo
    df_limpo.to_excel("vendas_limpas.xlsx", index=False)
    
    print("SUCESSO: Arquivo 'vendas_limpas.xlsx' criado na pasta!")
        
if __name__ == "__main__":
    main()