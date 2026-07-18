import datetime
import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
import os

# 1. Configuração de Acesso ao Google Sheets
CONEXAO_JSON = "suas-credenciais.json" 
NOME_PLANILHA = "Controle_Lavanderia"

def conectar_sheets():
    escopo = ["https://google.com", "https://googleapis.com"]
    credenciais = ServiceAccountCredentials.from_json_keyfile_name(CONEXAO_JSON, escopo)
    cliente = gspread.authorize(credenciais)
    return cliente.open(NOME_PLANILHA)

def limpar_tela():
    os.system('cls' if os.name == 'nt' else 'clear')

# 2. Função para Gravação de Dados
def registrar_producao(setor, dados):
    try:
        planilha = conectar_sheets()
        aba = planilha.worksheet(setor)
        aba.append_row(dados)
        print(f"\n✅ Dados registrados com sucesso no setor {setor.upper()}!")
    except Exception as e:
        print(f"\n❌ Erro ao conectar ou gravar no Google Sheets: {e}")
    input("\nPressione [ENTER] para voltar ao menu...")

# 3. Função de Dashboard e Análise
def gerar_resumo_executantes():
    limpar_tela()
    print("📊 Buscando dados e gerando análise de produção individual...")
    try:
        planilha = conectar_sheets()
        setores = ["Lavagem", "Lavados", "Secagem", "Pesagem", "Dobragem"]
        df_geral = []

        for setor in setores:
            aba = planilha.worksheet(setor)
            dados = aba.get_all_records()
            if dados:
                df = pd.DataFrame(dados)
                # Padroniza a coluna de funcionário para consolidação
                df = df.rename(columns={"Nome Executante": "Executante"})
                df["Setor"] = setor
                df_geral.append(df[["Executante", "Setor"]])

        if not df_geral:
            print("\n⚠️ Nenhum dado encontrado em nenhuma aba para gerar o resumo.")
            input("\nPressione [ENTER] para voltar...")
            return

        # Consolida e agrupa os dados
        df_consolidado = pd.concat(df_geral, ignore_index=True)
        resumo = df_consolidado.groupby(["Executante", "Setor"]).size().unstack(fill_value=0)
        resumo["Total Geral"] = resumo.sum(axis=1)
        
        # Exibe o resultado formatado na tela
        print("\n===============================================================")
        print("                RESUMO DE PRODUÇÃO INDIVIDUAL                ")
        print("===============================================================")
        print(resumo.to_string())
        print("===============================================================")
        
        # Atualiza a aba 'Resumo' no Google Sheets para os gestores acompanharem de fora
        try:
            aba_resumo = planilha.worksheet("Resumo")
            aba_resumo.clear()
            aba_resumo.update([resumo.reset_index().columns.values.tolist()] + resumo.reset_index().values.tolist())
            print("🔄 Aba 'Resumo' sincronizada com sucesso no Google Sheets!")
        except gspread.exceptions.WorksheetNotFound:
            aba_resumo = planilha.add_worksheet(title="Resumo", rows="100", cols="10")
            aba_resumo.update([resumo.reset_index().columns.values.tolist()] + resumo.reset_index().values.tolist())
            print("✨ Nova aba 'Resumo' criada e sincronizada no Google Sheets!")

    except Exception as e:
        print(f"❌ Erro ao gerar o resumo: {e}")
    
    input("\nPressione [ENTER] para voltar ao menu...")

# 4. Interface de Coleta de Dados por Setor
def menu_setores():
    while True:
        limpar_tela()
        data_atual = datetime.date.today().strftime("%d/%m/%Y")
        
        print("=== SISTEMA DE CONTROLE DE LAVANDERIA ===")
        print(f"Data de hoje: {data_atual}")
        print("-----------------------------------------")
        print("1. Setor de Lavagem")
        print("2. Setor de Lavados")
        print("3. Setor de Secagem")
        print("4. Setor de Pesagem")
        print("5. Setor de Dobragem")
        print("6. Ver Resumo de Produção (Dashboard)")
        print("0. Sair do Programa")
        print("-----------------------------------------")
        
        opcao = input("Escolha uma opção: ").strip()
        
        if opcao == "0":
            print("\nEncerrando o sistema. Até logo!")
            break
            
        elif opcao == "1":
            limpar_tela()
            print("--- LANÇAMENTO: SETOR DE LAVAGEM ---")
            cliente = input("Cliente: ")
            maquina = input("Máquina (ex: M1): ")
            peso = input("Peso (ex: 45kg): ")
            inicio = input("Horário de Início (ex: 08:00): ")
            termino = input("Horário de Término (ex: 09:15): ")
            executante = input("Nome do Executante: ")
            
            dados = [cliente, data_atual, maquina, peso, inicio, termino, executante]
            registrar_producao("Lavagem", dados)
            
        elif opcao == "2":
            limpar_tela()
            print("--- LANÇAMENTO: SETOR DE LAVADOS ---")
            cliente = input("Cliente: ")
            maquina = input("Máquina: ")
            peso = input("Peso: ")
            inicio = input("Horário de Início: ")
            termino = input("Horário de Término: ")
            executante = input("Nome do Executante: ")
            
            dados = [cliente, data_atual, maquina, peso, inicio, termino, executante]
            registrar_producao("Lavados", dados)
            
        elif opcao == "3":
            limpar_tela()
            print("--- LANÇAMENTO: SETOR DE SECAGEM ---")
            maquina = input("Máquina: ")
            cliente = input("Cliente: ")
            entrada = input("Horário de Entrada: ")
            saida = input("Horário de Saída: ")
            executante = input("Nome do Executante: ")
            
            dados = [maquina, cliente, data_atual, entrada, saida, executante]
            registrar_producao("Secagem", dados)
            
        elif opcao == "4":
            limpar_tela()
            print("--- LANÇAMENTO: SETOR DE PESAGEM ---")
            cliente = input("Cliente: ")
            pesagem = input("Pesagem/Peso: ")
            executante = input("Nome do Executante: ")
            
            # Validação do tipo de lavagem
            while True:
                tipo = input("Tipo de Operação (1 - Normal / 2 - Relave): ").strip()
                if tipo == "1":
                    tipo_texto = "Normal"
                    break
                elif tipo == "2":
                    tipo_texto = "Relave"
                    break
                print("⚠️ Opção inválida! Digite 1 ou 2.")
                
            dados = [cliente, data_atual, pesagem, executante, tipo_texto]
            registrar_producao("Pesagem", dados)
            
        elif opcao == "5":
            limpar_tela()
            print("--- LANÇAMENTO: SETOR DE DOBRAGEM ---")
            cliente = input("Cliente: ")
            item = input("Item da Rouparia (ex: Lençol Casal, Toalha): ")
            qtd = input("Quantidade (Contagem): ")
            executante = input("Nome do Executante (Filtro): ")
            
            dados = [cliente, data_atual, item, qtd, executante]
            registrar_producao("Dobragem", dados)
            
        elif opcao == "6":
            gerar_resumo_executantes()
            
        else:
            print("\n⚠️ Opção inválida! Tente novamente.")
            input("\nPressione [ENTER] para continuar...")

if __name__ == "__main__":
    menu_setores()
