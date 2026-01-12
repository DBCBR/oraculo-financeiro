print("--- SISTEMA DE CÁLCULO LOGÍSTICO V1.0 ---\n")

# ENTRADA DE DADOS (INPUT)
# O input recebe texto (string). O float() converte esse texto para número decimal.
try:
    peso = float(input("Digite o peso do pacote (kg): "))
    distancia = float(input("Digite a distância da entrega (km): "))
except ValueError:
    print("ERRO CRÍTICO: Você digitou letras em vez de números. Reinicie o programa.")
    exit() # Encerra o programa se o usuário digitar bobagem

# CONFIGURAÇÃO
frete_base = 10.00
custo_total = 0.00
erro = False

# PROCESSAMENTO (SUA LÓGICA REFINADA)
if peso <= 0:
    print("ERRO: Peso inválido. Deve ser maior que zero.")
    erro = True

elif peso > 20:
    print("ERRO: Carga muito pesada. Limite é 20kg.")
    erro = True

else:
    # Cálculo do Peso
    if peso <= 5:
        custo_total = frete_base
    else:
        excedente = peso - 5
        custo_total = frete_base + (excedente * 2.00)

    # Cálculo da Distância
    if distancia > 100:
        print("-> Adicional de longa distância aplicado (+ R$ 20.00)")
        custo_total += 20.00 # O mesmo que: custo_total = custo_total + 20

# SAÍDA (OUTPUT)
if not erro:
    print("-" * 30) # Imprime uma linha divisória visual
    print(f"CUSTO FINAL DO FRETE: R$ {custo_total:.2f}")
    print("-" * 30)