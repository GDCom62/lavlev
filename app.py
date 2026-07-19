import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import datetime
import json

# Nome da sua planilha no Google Drive
NOME_PLANILHA = "Controle_Lavanderia"

# Lista de itens do setor de dobragem
ITENS_DOBRAGEM = ["Lençol", "Fronha", "Capote", "Camisola", "Oleado", "Calça", "Camisa", "Cobertor", "Colcha", "Toalha", "Traçado"]

@st.cache_resource
def conectar_sheets():
    escopo = ["https://google.com", "https://googleapis.com"]
    
    # Carrega as configurações básicas dos Secrets do Streamlit Cloud
    credenciais_dict = dict(st.secrets["gcp_service_account"])
    
    # Algoritmo de limpeza para a chave criptográfica
    if "private_key" in credenciais_dict:
        pk = credenciais_dict["private_key"]
        pk = pk.strip().replace("\\n", "\n")
        if "-----BEGIN PRIVATE KEY-----" not in pk:
            pk = "-----BEGIN PRIVATE KEY-----\n" + pk
        if "-----END PRIVATE KEY-----" not in pk:
            pk = pk + "\n-----END PRIVATE KEY-----"
        pk = pk.replace("\n\n", "\n")
        credenciais_dict["private_key"] = pk
        
    credenciais = ServiceAccountCredentials.from_json_keyfile_dict(credenciais_dict, escopo)
    cliente = gspread.authorize(credenciais)
    return cliente.open(NOME_PLANILHA)

def registrar_dados(setor, dados):
    try:
        planilha = conectar_sheets()
        aba = planilha.worksheet(setor)
        aba.append_row(dados)
        st.success(f"✅ Dados gravados com sucesso no setor {setor}!")
    except Exception as e:
        st.error(f"❌ Erro ao gravar dados: {e}")

def deletar_ultima_linha(setor):
    try:
        planilha = conectar_sheets()
        aba = planilha.worksheet(setor)
        total_linhas = len(aba.get_all_values())
        if total_linhas > 1:
            aba.delete_rows(total_linhas)
            st.success(f"💥 O último lançamento do setor '{setor}' foi excluído com sucesso!")
        else:
            st.warning(f"⚠️ Não há dados para apagar no setor '{setor}' (apenas o cabeçalho existe).")
    except Exception as e:
        st.error(f"❌ Erro ao deletar dados: {e}")

def puxar_historico_setor(setor_selecionado):
    try:
        planilha = conectar_sheets()
        dados_setor = planilha.worksheet(setor_selecionado).get_all_records()
        df_historico = pd.DataFrame(dados_setor)
        if df_historico.empty:
            st.info("Aba selecionada está vazia.")
        else:
            st.write(f"📋 **Últimos registros encontrados em {setor_selecionado}:**")
            st.dataframe(df_historico.tail(10), use_container_width=True)
    except Exception as e:
        st.error(f"Erro ao carregar histórico: {e}")

def gerar_relatorios_lavanderia(filtro_cliente):
    try:
        planilha = conectar_sheets()
        setores = ["Lavagem", "Lavados", "Secagem", "Pesagem", "Dobragem"]
        df_geral = []
        
        for setor in setores:
            dados = planilha.worksheet(setor).get_all_records()
            if dados:
                df = pd.DataFrame(dados)
                df = df.rename(columns={"Nome Executante": "Executante"})
                if filtro_cliente:
                    df = df[df["Cliente"].astype(str).str.contains(filtro_cliente, case=False, na=False)]
                df["Setor"] = setor
                if "Executante" in df.columns:
                    df_geral.append(df[["Executante", "Setor"]])

        st.subheader("1. Quantidade de Operações por Funcionário / Setor")
        if df_geral:
            df_consolidado = pd.concat(df_geral, ignore_index=True)
            resumo_func = df_consolidado.groupby(["Executante", "Setor"]).size().unstack(fill_value=0)
            resumo_func["Total Geral"] = resumo_func.sum(axis=1)
            st.dataframe(resumo_func, use_container_width=True)
        else:
            st.info("Nenhum dado encontrado para o resumo de operações.")

        st.subheader("2. Total de Peças Dobradas por Cliente e Executante")
        dados_dobragem = planilha.worksheet("Dobragem").get_all_records()
        
        if dados_dobragem:
            df_dob = pd.DataFrame(dados_dobragem)
            df_dob = df_dob.rename(columns={"Nome Executante": "Executante"})
            if filtro_cliente:
                df_dob = df_dob[df_dob["Cliente"].astype(str).str.contains(filtro_cliente, case=False, na=False)]
            
            for item in ITENS_DOBRAGEM:
                if item in df_dob.columns:
                    df_dob[item] = pd.to_numeric(df_dob[item], errors='coerce').fillna(0)
            
            colunas_agrupamento = ["Cliente", "Executante"]
            colunas_soma = [item for item in ITENS_DOBRAGEM if item in df_dob.columns]
            
            if colunas_soma:
                resumo_pecas = df_dob.groupby(colunas_agrupamento)[colunas_soma].sum()
                resumo_pecas["Total de Peças"] = resumo_pecas.sum(axis=1)
                st.dataframe(resumo_pecas, use_container_width=True)
            else:
                st.info("Colunas de itens de dobragem não encontradas na planilha.")
        else:
            st.info("Nenhum registro encontrado na aba de Dobragem.")
            
    except Exception as e:
        st.error(f"Erro ao processar relatórios: {e}")

# Configuração da Página Web
st.set_page_config(page_title="Controle Lavanderia", layout="wide")

# Menu de Navegação na Barra Lateral (Sidebar)
st.sidebar.title("🧼 Navegação")
menu = st.sidebar.radio("Selecione o Setor:", [
    "Lavagem", 
    "Lavados", 
    "Secagem", 
    "Pesagem", 
    "Dobragem", 
    "📊 Resumos e Análises", 
    "🛠️ Histórico e Deleção"
])

st.title("🧼 Sistema de Controle de Lavanderia")

# Campo de data global na barra lateral
data_lancamento = st.sidebar.date_input("Data do Lançamento:", datetime.date.today())
data_formatada = data_lancamento.strftime("%d/%m/%Y")

# ---- PÁGINA: LAVAGEM ----
if menu == "Lavagem":
    st.header("Lançamento - Setor de Lavagem")
    with st.form("form_lavagem", clear_on_submit=True):
        cliente = st.text_input("Cliente")
        maquina = st.text_input("Máquina")
        peso = st.text_input("Peso (ex: 45kg)")
        inicio = st.text_input("Horário de Início (ex: 08:00)")
        termino = st.text_input("Horário de Término (ex: 09:15)")
        executante = st.text_input("Nome do Executante")
        
        if st.form_submit_button("Gravar Lavagem"):
            if cliente and executante:
                registrar_dados("Lavagem", [cliente, data_formatada, maquina, peso, inicio, termino, executante])
            else:
                st.warning("Preencha os campos obrigatórios (Cliente e Executante).")

# ---- PÁGINA: LAVADOS ----
elif menu == "Lavados":
    st.header("Lançamento - Setor de Lavados")
    with st.form("form_lavados", clear_on_submit=True):
        cliente = st.text_input("Cliente")
        maquina = st.text_input("Máquina")
        peso = st.text_input("Peso")
        inicio = st.text_input("Horário de Início")
        termino = st.text_input("Horário de Término")
        executante = st.text_input("Nome do Executante")
        
        if st.form_submit_button("Gravar Lavados"):
            if cliente and executante:
                registrar_dados("Lavados", [cliente, data_formatada, maquina, peso, inicio, termino, executante])
            else:
                st.warning("Preencha os campos obrigatórios.")

# ---- PÁGINA: SECAGEM ----
elif menu == "Secagem":
    st.header("Lançamento - Setor de Secagem")
    with st.form("form_secagem", clear_on_submit=True):
        maquina = st.text_input("Máquina")
        cliente = st.text_input("Cliente")
        entrada = st.text_input("Horário de Entrada")
        saida = st.text_input("Horário de Saída")
        executante = st.text_input("Nome do Executante")
        
        if st.form_submit_button("Gravar Secagem"):
            if cliente and executante:
                registrar_dados("Secagem", [maquina, cliente, data_formatada, entrada, saida, executante])
            else:
                st.warning("Preencha os campos obrigatórios.")

# ---- PÁGINA: PESAGEM ----
elif menu == "Pesagem":
    st.header("Lançamento - Setor de Pesagem")
    with st.form("form_pesagem", clear_on_submit=True):
        cliente = st.text_input("Cliente")
        pesagem = st.text_input("Pesagem")
        executante = st.text_input("Nome do Executante")
        tipo = st.radio("Tipo de Operação", ["Normal", "Relave"])
        
        if st.form_submit_button("Gravar Pesagem"):
            if cliente and executante:
                registrar_dados("Pesagem", [cliente, data_formatada, pesagem, executante, tipo])
            else:
                st.warning("Preencha os campos obrigatórios.")

# ---- PÁGINA: DOBRAGEM ----
elif menu == "Dobragem":
    st.header("Lançamento - Setor de Dobragem")
    with st.form("form_dobragem", clear_on_submit=True):
        cliente = st.text_input("Cliente")
        executante = st.text_input("Nome do Executante")
        st.markdown("### Contagem de Itens Dobrados")
        
        qtds = {}
        for item in ITENS_DOBRAGEM:
            qtds[item] = st.number_input(f"Quantidade de {item}:", min_value=0, step=1, key=f"dob_{item}")
        
        if st.form_submit_button("Gravar Dobragem"):
            if cliente and executante:
                linha_dobragem = [cliente, data_formatada, executante] + [int(qtds[it]) for it in ITENS_DOBRAGEM]
                registrar_dados("Dobragem", linha_dobragem)
            else:
                st.warning("Preencha Cliente e Executante antes de salvar.")

# ---- PÁGINA: RESUMOS E ANÁLISES ----
elif menu == "📊 Resumos e Análises":
    st.header("📊 Painel Estatístico e Resumos")
    filtro_cli = st.text_input("🔍 Filtrar Resumos por Cliente (Deixe vazio para todos)")
    if st.button("Gerar / Atualizar Relatórios"):
        gerar_relatorios_lavanderia(filtro_cli)

# ---- PÁGINA: HISTÓRICO E DELEÇÃO ----
