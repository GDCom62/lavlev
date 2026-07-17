import datetime
import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials

# 1. Configuração de Acesso ao Google Sheets
# Lembre-se de baixar seu arquivo JSON de credenciais do Google Cloud Console
CONEXAO_JSON = "suas-credenciais.json" 
NOME_PLANILHA = "Controle_Lavanderia"

def conectar_sheets():
    escopo = ["https://google.com", "https://googleapis.com"]
    credenciais = ServiceAccountCredentials.from_json_keyfile_name(CONEXAO_JSON, escopo)
    cliente = gspread.authorize(credenciais)
    return cliente.open(NOME_PLANILHA)

# 2. Função para Inserir Dados em Qualquer Setor
def registrar_producao(setor, dados):
    """
    setor: 'Lavagem', 'Lavados', 'Secagem', 'Pesagem' ou 'Dobragem'
    dados: Lista com os valores na ordem exata das colunas
    """
    try:
        planilha = conectar_sheets()
        aba = planilha.worksheet(setor)
        aba.append_row(dados)
        print(f"✅ Dados registrados com sucesso no setor: {setor}!")
    except Exception as e:
        print(f"❌ Erro ao registrar dados: {e}")

# 3. Função de Análise e Resumo de Produção Individual
def gerar_resumo_executantes():
    planilha = conectar_sheets()
    setores = ["Lavagem", "Lavados", "Secagem", "Pesagem", "Dobragem"]
    df_geral = []

    print("\n📊 Buscando dados para análise de produção...")
    
    for setor in setores:
        aba = planilha.worksheet(setor)
        dados = aba.get_all_records()
        if dados:
            df = pd.DataFrame(dados)
            # Padroniza o nome da coluna do funcionário para consolidação
            df = df.rename(columns={"Nome Executante": "Executante"})
            df["Setor"] = setor
            df_geral.append(df[["Executante", "Setor"]])

    if not df_geral:
        print("Nenhum dado encontrado para gerar o resumo.")
        return

    # Consolida todos os setores em um único DataFrame
    df_consolidado = pd.concat(df_geral, ignore_index=True)

    # Gera a matriz de produtividade (Quantidade de ações por setor para cada executante)
    resumo = df_consolidado.groupby(["Executante", "Setor"]).size().unstack(fill_value=0)
    
    # Adiciona total de ordens finalizadas por ele
    resumo["Total Geral"] = resumo.sum(axis=1)
    
    print("\n================ RESUMO DE PRODUÇÃO INDIVIDUAL ================")
    print(resumo.to_string())
    print("===============================================================")
    
    # Opcional: Salvar o resumo em uma aba própria na planilha chamada 'Resumo'
    try:
        aba_resumo = planilha.worksheet("Resumo")
        aba_resumo.clear()
        # Atualiza o cabeçalho e os dados
        aba_resumo.update([resumo.reset_index().columns.values.tolist()] + resumo.reset_index().values.tolist())
        print("🔄 Aba 'Resumo' atualizada diretamente no Google Sheets!")
    except gspread.exceptions.WorksheetNotFound:
        # Cria a aba caso ela não exista
        aba_resumo = planilha.add_worksheet(title="Resumo", rows="100", cols="10")
        aba_resumo.update([resumo.reset_index().columns.values.tolist()] + resumo.reset_index().values.tolist())
        print("✨ Aba 'Resumo' criada e atualizada no Google Sheets!")

# ==============================================================================
# EXEMPLOS DE USO NO DIA A DIA
# ==============================================================================
if __name__ == "__main__":
    data_hoje = datetime.date.today().strftime("%d/%m/%Y")

    # Exemplo 1: Registrando uma lavagem
    # Colunas: Cliente, Data, Máquina, Peso, Início, Término, Nome Executante
    dados_lavagem = ["Hotel Estrela", data_hoje, "MÁQUINA 02", "45kg", "08:00", "09:15", "Carlos Silva"]
    registrar_producao("Lavagem", dados_lavagem)

    # Exemplo 2: Registrando uma pesagem (com filtro Normal/Relave)
    # Colunas: Cliente, Data, Pesagem, Nome Executante, Tipo (Normal/Relave)
    dados_pesagem = ["Hospital São Lucas", data_hoje, "120kg", "Ana Souza", "Normal"]
    registrar_producao("Pesagem", dados_pesagem)
    
    # Exemplo 3: Registrando uma dobragem com contagem de rouparia
    # Colunas: Cliente, Data, Item Rouparia, Quantidade, Nome Executante
    dados_dobragem = ["Pousada do Sol", data_hoje, "Lençol Casal", 35, "Carlos Silva"]
    registrar_producao("Dobragem", dados_dobragem)

    # Exemplo 4: Gerar relatório de desempenho
    gerar_resumo_executantes()
