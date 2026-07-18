import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import datetime

# Nome da sua planilha no Google Drive
NOME_PLANILHA = "Controle_Lavanderia"

# Lista de itens atualizada
ITENS_DOBRAGEM = ["Lençol", "Fronha", "Capote", "Camisola", "Oleado", "Calça", "Camisa", "Cobertor", "Colcha", "Toalha", "Traçado"]

@st.cache_resource
def conectar_sheets():
    escopo = ["https://google.com", "https://googleapis.com"]
    credenciais_dict = dict(st.secrets["gcp_service_account"])
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
        # Obtém todas as linhas para verificar a quantidade
        total_linhas = len(aba.get_all_values())
        if total_linhas > 1: # Evita apagar o cabeçalho (linha 1)
            aba.delete_rows(total_linhas)
            st.success(f"💥 O último lançamento do setor '{setor}' foi excluído com sucesso!")
        else:
            st.warning(f"⚠️ Não há dados para apagar no setor '{setor}' (apenas o cabeçalho existe).")
    except Exception as e:
        st.error(f"❌ Erro ao deletar dados: {e}")

# Interface Principal
st.set_page_config(page_title="Controle Lavanderia", layout="wide")
st.title("🧼 Sistema de Controle de Lavanderia")

# Campo de data global
data_lancamento = st.date_input("Data do Lançamento:", datetime.date.today())
data_formatada = data_lancamento.strftime("%d/%m/%Y")

# Novas abas incluindo Gerenciamento / Restauração
abas = st.tabs(["Lavagem", "Lavados", "Secagem", "Pesagem", "Dobragem", "📊 Resumos e Análises", "🛠️ Histórico e Deleção"])

# ---- ABA: LAVAGEM ----
with abas[0]:
    st.header("Lançamento - Setor de Lavagem")
    with st.form("form_lavagem", clear_on_submit=True):
        cliente = st.text_input("Cliente", key="lav_cli")
        maquina = st.text_input("Máquina", key="lav_maq")
        peso = st.text_input("Peso (ex: 45kg)", key="lav_pes")
        inicio = st.text_input("Horário de Início (ex: 08:00)", key="lav_ini")
        termino = st.text_input("Horário de Término (ex: 09:15)", key="lav_ter")
        executante = st.text_input("Nome do Executante", key="lav_exe")
        
        if st.form_submit_button("Gravar Lavagem"):
            if cliente and executante:
                registrar_dados("Lavagem", [cliente, data_formatada, maquina, peso, inicio, termino, executante])
            else:
                st.warning("Preencha os campos obrigatórios (Cliente e Executante).")

# ---- ABA: LAVADOS ----
with abas[1]:
    st.header("Lançamento - Setor de Lavados")
    with st.form("form_lavados", clear_on_submit=True):
        cliente = st.text_input("Cliente", key="lvd_cli")
        maquina = st.text_input("Máquina", key="lvd_maq")
        peso = st.text_input("Peso", key="lvd_pes")
        inicio = st.text_input("Horário de Início", key="lvd_ini")
        termino = st.text_input("Horário de Término", key="lvd_ter")
        executante = st.text_input("Nome do Executante", key="lvd_exe")
        
        if st.form_submit_button("Gravar Lavados"):
            if cliente and executante:
                registrar_dados("Lavados", [cliente, data_formatada, maquina, peso, inicio, termino, executante])
            else:
                st.warning("Preencha os campos obrigatórios.")

# ---- ABA: SECAGEM ----
with abas[2]:
    st.header("Lançamento - Setor de Secagem")
    with st.form("form_secagem", clear_on_submit=True):
        maquina = st.text_input("Máquina", key="sec_maq")
        cliente = st.text_input("Cliente", key="sec_cli")
        entrada = st.text_input("Horário de Entrada", key="sec_ent")
        saida = st.text_input("Horário de Saída", key="sec_sai")
        executante = st.text_input("Nome do Executante", key="sec_exe")
        
        if st.form_submit_button("Gravar Secagem"):
            if cliente and executante:
                registrar_dados("Secagem", [maquina, cliente, data_formatada, entrada, saida, executante])
            else:
                st.warning("Preencha os campos obrigatórios.")

# ---- ABA: PESAGEM ----
with abas[3]:
    st.header("Lançamento - Setor de Pesagem")
    with st.form("form_pesagem", clear_on_submit=True):
        cliente = st.text_input("Cliente", key="pes_cli")
        pesagem = st.text_input("Pesagem", key="pes_val")
        executante = st.text_input("Nome do Executante", key="pes_exe")
        tipo = st.radio("Tipo de Operação", ["Normal", "Relave"], key="pes_tipo")
        
        if st.form_submit_button("Gravar Pesagem"):
            if cliente and executante:
                registrar_dados("Pesagem", [cliente, data_formatada, pesagem, executante, tipo])
            else:
                st.warning("Preencha os campos obrigatórios.")

# ---- ABA: DOBRAGEM ----
with abas[4]:
    st.header("Lançamento - Setor de Dobragem")
    with st.form("form_dobragem", clear_on_submit=True):
        cliente = st.text_input("Cliente", key="dob_cli")
        executante = st.text_input("Nome do Executante", key="dob_exe")
        
        st.markdown("### Contagem de Itens Dobrados")
        col1, col2, col3, col4 = st.columns(4)
        
        qtds = {}
        for i, item in enumerate(ITENS_DOBRAGEM):
            if i % 4 == 0:
                with col1: qtds[item] = st.number_input(f"Qtd {item}", min_value=0, step=1, key=f"dob_{item}")
            elif i % 4 == 1:
                with col2: qtds[item] = st.number_input(f"Qtd {item}", min_value=0, step=1, key=f"dob_{item}")
            elif i % 4 == 2:
                with col3: qtds[item] = st.number_input(f"Qtd {item}", min_value=0, step=1, key=f"dob_{item}")
            else:
                with col4: qtds[item] = st.number_input(f"Qtd {item}", min_value=0, step=1, key=f"dob_{item}")
        
        if st.form_submit_button("Gravar Dobragem"):
            if cliente and executante:
                linha_dobragem = [cliente, data_formatada, executante] + [int(qtds[item]) for item in ITENS_DOBRAGEM]
                registrar_dados("Dobragem", linha_dobragem)
            else:
                st.warning("Preencha Cliente e Executante antes de salvar.")

# ---- ABA: RESUMOS E ANÁLISES ----
with abas[5]:
    st.header("📊 Painel Estatístico e Resumos")
    filtro_cliente = st.text_input("🔍 Filtrar Resumos por Cliente (Deixe vazio para todos)")
    
    if st.button("Gerar / Atualizar Relatórios"):
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
                st.info("Nenhum dado encontrado.")

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
        except Exception as e:
            st.error(f"Erro ao processar relatórios: {e}")

# ---- ABA: HISTÓRICO E DELEÇÃO (CORRIGIDA) ----
with abas[6]:
    st.header("🛠️ Gerenciamento de Dados e Correções")
    st.markdown("Use esta aba para conferir os últimos lançamentos de cada setor ou apagar uma linha caso tenha sido inserida com erros.")
    
    setor_selecionado = st.selectbox("Escolha o setor para verificar ou corrigir:", ["Lavagem", "Lavados", "Secagem", "Pesagem", "Dobragem"])
    
    if st.button(f"Visualizar Linhas de {setor_selecionado}"):
        try:
