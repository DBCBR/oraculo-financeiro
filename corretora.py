salario = 1500
comissao = 200
comissao_venda = 0.05
corretor = 0
quantidade_vendas = 0
comissao_total = 0


def calcular_salario_total(salario, comissao, comissao_venda, total_vendas):
    corretor = input("Digite o nome do corretor: ")
    quantidade_vendas = int(input("Digite a quantidade de imóveis vendidos: "))
    total_vendas = float(input("Digite o valor total das vendas realizadas: "))
    if quantidade_vendas > 0:
        comissao_total = quantidade_vendas * \
            comissao + (total_vendas * comissao_venda)
    else:
        comissao_total = 0
    salario_total = salario + comissao_total
    print(f"O salário total do corretor {corretor} é: R$ {salario_total:.2f}")


def demonstrar_calculo_salario(salario, comissao, comissao_venda, quantidade_vendas, total_vendas):
    comissao_total = quantidade_vendas * \
        comissao + (total_vendas * comissao_venda)
    salario_total = salario + comissao_total
    print(f"Salário base: R$ {salario:.2f}")
    print(
        f"Comissão por imóvel vendido: R$ {comissao * quantidade_vendas:.2f}")
    print(
        f"Comissão total sobre vendas: R$ {total_vendas * comissao_venda:.2f}")
    print(f"Salário total: R$ {salario_total:.2f}")

    return salario_total


# Chama a função para calcular o salário total
if __name__ == '__main__':
    calcular_salario_total(salario, comissao, comissao_venda, 0)
    corretor = input("Digite o nome do corretor: ")
    quantidade_vendas = int(input("Digite a quantidade de imóveis vendidos: "))
    total_vendas = float(input("Digite o valor total das vendas realizadas: "))
    demonstrar_calculo_salario(
        salario, comissao, comissao_venda, quantidade_vendas, total_vendas)
