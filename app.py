import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import google.auth.transport.requests
import pandas as pd
import datetime
import json
import os

# Nome da sua planilha no Google Drive
NOME_PLANILHA = "Controle_Lavanderia"

# Lista de itens do setor de dobragem
ITENS_DOBRAGEM = ["Lençol", "Fronha", "Capote", "Camisola", "Oleado", "Calça", "Camisa", "Cobertor", "Colcha", "Toalha", "Traçado"]

def conectar_sheets():
    escopo = [
        "https://googleapis.com",
        "https://googleapis.com"
    ]
    
    credenciais = None
    credenciais_dict = None
    
    # 1. Tenta carregar do arquivo físico local se ele existir
    if os.path.exists("lavanderia_key.json"):
        try:
            with open("lavanderia_key.json", "r", encoding="utf-8") as f:
                credenciais_dict = json.load(f)
        except Exception:
            pass
            
    # 2. Se não existir o arquivo físico, tenta carregar do arquivo enviado na tela
    elif "google_json_data" in st.session_state and st.session_state["google_json_data"] is not None:
        try:
            credenciais_dict = json.loads(st.session_state["google_json_data"])
        except Exception:
            return None
            
    if credenciais_dict is not None:
        try:
            if "private_key" in credenciais_dict:
                pk = credenciais_dict["private_key"]
                pk = pk.strip().strip('"').strip("'").replace("\\n", "\n")
                
                conteudo_puro = pk.replace("-----BEGIN PRIVATE KEY-----", "").replace("-----END PRIVATE KEY-----", "")
                conteudo_puro = conteudo_puro.replace("\n", "").replace("\r", "").replace(" ", "")
                linhas_remontadas = [conteudo_puro[i:i+64] for i in range(0, len(conteudo_puro), 64)]
                credenciais_dict["private_key"] = "-----BEGIN PRIVATE KEY-----\n" + "\n".join(linhas_remontadas) + "\n-----END PRIVATE KEY-----\n"
            
            credenciais = Credentials.from_service_account_info(credenciais_dict, scopes=escopo)
            requisicao = google.auth.transport.requests.Request()
            credenciais.refresh(requisicao)
            
            cliente = gspread.authorize(credenciais)
            return cliente.open(NOME_PLANILHA)
        except Exception as error_auth:
            st.error(f"⚠️ Erro interno de validação do Google: {error_auth}")
            return None
            
    return None

def registrar_dados(setor, dados):
    planilha = conectar_sheets()
    if planilha is None:
        st.error("❌ Erro de Autenticação: Por favor, selecione ou reenvie o arquivo .json válido na barra lateral.")
        return
    try:
        aba = planilha.worksheet(setor)
        aba.append_row(dados)
        st.success(f"✅ Dados gravados com sucesso no setor {setor}!")
    except Exception as e:
        st.error(f"❌ Erro ao gravar dados no Sheets: {e}")

def deletar_ultima_linha(setor):
    planilha = conectar_sheets()
    if planilha is None:
        st.error("❌ Envie o arquivo .json válido na barra lateral primeiro.")
        return
    try:
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
    planilha = conectar_sheets()
    if planilha is None:
        st.info("Aguardando o envio de um arquivo .json válido na barra lateral.")
        return
    try:
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
    planilha = conectar_sheets()
    if planilha is None:
        st.info("Aguardando o envio de um arquivo .json válido na barra lateral.")
        return
    try:
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

# Menu de Navegação Lateral
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

# Área de upload de chave
st.sidebar.markdown("---")
st.sidebar.subheader("🔑 Chave do Google Sheets")
arquivo_carregado = st.sidebar.file_uploader("Envie seu arquivo .json do Google:", type=["json"])

if arquivo_carregado is not None:
    conteudo_string = arquivo_carregado.getvalue().decode("utf-8")
    st.session_state["google_json_data"] = conteudo_string
    st.sidebar.success("🔑 Chave carregada com sucesso!")

data_lancamento = st.sidebar.date_input("Data do Lançamento:", datetime.date.today())
data_formatada = data_lancamento.strftime("%d/%m/%Y")

st.title("🧼 Sistema de Controle de Lavanderia")

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
        parent = st.text_input("Horário de Entrada")
        saida = st.text_input("Horário de Saída")
        executante = st.text_input("Nome do Executante")
        if st.form_submit_button("Gravar Secagem"):
