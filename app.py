import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import datetime
import json
import os

NOME_PLANILHA = "Controle_Lavanderia"
ITENS_DOBRAGEM = ["Lençol", "Fronha", "Capote", "Camisola", "Oleado", "Calça", "Camisa", "Cobertor", "Colcha", "Toalha", "Traçado"]

def conectar_sheets():
    escopo = ["https://googleapis.com", "https://googleapis.com"]
    credenciais_dict = None
    
    # 1. Tenta carregar do arquivo físico local se ele existir
    if os.path.exists("lavanderia_key.json"):
        try:
            with open("lavanderia_key.json", "r", encoding="utf-8") as f:
                credenciais_dict = json.load(f)
        except Exception:
            pass
            
    # 2. Se não existir o arquivo físico, usa o arquivo enviado na tela do navegador
    elif "google_json_data" in st.session_state and st.session_state["google_json_data"] is not None:
        try:
            credenciais_dict = json.loads(st.session_state["google_json_data"])
        except Exception:
            return None
            
    if credenciais_dict is not None:
        try:
            # Conecta usando os dados puros e originais do JSON do Google
            credenciais = Credentials.from_service_account_info(credenciais_dict, scopes=escopo)
            return gspread.authorize(credenciais).open(NOME_PLANILHA)
        except Exception as error_auth:
            st.error(f"⚠️ Erro de validação do Google: {error_auth}")
            
    return None

def registrar_dados(setor, dados):
    planilha = conectar_sheets()
    if planilha is None:
        st.error("❌ Erro: Selecione ou reenvie o arquivo .json válido na barra lateral.")
        return
    try:
        planilha.worksheet(setor).append_row(dados)
        st.success(f"✅ Gravado com sucesso em {setor}!")
    except Exception as e:
        st.error(f"❌ Erro ao gravar: {e}")

def deletar_ultima_linha(setor):
    planilha = conectar_sheets()
    if planilha is None: 
        st.error("❌ Envie o arquivo .json primeiro.")
        return
    try:
        aba = planilha.worksheet(setor)
        total = len(aba.get_all_values())
        if total > 1:
            aba.delete_rows(total)
            st.success(f"💥 Último registro de {setor} apagado!")
        else:
            st.warning("⚠️ Nada para apagar além do cabeçalho.")
    except Exception as e: 
        st.error(f"❌ Erro ao deletar: {e}")

def puxar_historico_setor(setor):
    planilha = conectar_sheets()
    if planilha is None: 
        st.info("Envie o arquivo .json para ver o histórico.")
        return
    try:
        dados = planilha.worksheet(setor).get_all_records()
        if not dados: 
            st.info("Aba vazia.")
        else: 
            st.dataframe(pd.DataFrame(dados).tail(10), use_container_width=True)
    except Exception as e: 
        st.error(f"Erro: {e}")

def gerar_relatorios(filtro_cliente):
    planilha = conectar_sheets()
    if planilha is None: 
        st.info("Envie o arquivo .json para ver os relatórios.")
        return
    try:
        df_geral = []
        for s in ["Lavagem", "Lavados", "Secagem", "Pesagem", "Dobragem"]:
            dados = planilha.worksheet(s).get_all_records()
            if dados:
                df = pd.DataFrame(dados).rename(columns={"Nome Executante": "Executante"})
                if filtro_cliente:
                    df = df[df["Cliente"].astype(str).str.contains(filtro_cliente, case=False, na=False)]
                df["Setor"] = s
                if "Executante" in df.columns: 
                    df_geral.append(df[["Executante", "Setor"]])

        st.subheader("1. Quantidade de Operações por Funcionário / Setor")
        if df_geral:
            res = pd.concat(df_geral, ignore_index=True).groupby(["Executante", "Setor"]).size().unstack(fill_value=0)
            res["Total Geral"] = res.sum(axis=1)
            st.dataframe(res, use_container_width=True)
        else: 
            st.info("Nenhum dado encontrado.")

        st.subheader("2. Total de Peças Dobradas por Cliente e Executante")
        dados_dob = planilha.worksheet("Dobragem").get_all_records()
        if dados_dob:
            df_dob = pd.DataFrame(dados_dob).rename(columns={"Nome Executante": "Executante"})
            if filtro_cliente:
                df_dob = df_dob[df_dob["Cliente"].astype(str).str.contains(filtro_cliente, case=False, na=False)]
            for it in ITENS_DOBRAGEM:
                if it in df_dob.columns: 
                    df_dob[it] = pd.to_numeric(df_dob[it], errors='coerce').fillna(0)
            cols_soma = [it for it in ITENS_DOBRAGEM if it in df_dob.columns]
            if cols_soma:
                res_pecas = df_dob.groupby(["Cliente", "Executante"])[cols_soma].sum()
                res_pecas["Total de Peças"] = res_pecas.sum(axis=1)
                st.dataframe(res_pecas, use_container_width=True)
        else: 
            st.info("Nenhum registro em Dobragem.")
    except Exception as e: 
        st.error(f"Erro nos relatórios: {e}")

# --- PÁGINAS ISOLADAS (FUNÇÕES PLANAS) ---
def pag_lavagem(dt):
    st.header("Lançamento - Setor de Lavagem")
    with st.form("f_lav", clear_on_submit=True):
        c, m, p = st.text_input("Cliente"), st.text_input("Máquina"), st.text_input("Peso (ex: 45kg)")
        i, t, e = st.text_input("Horário Início"), st.text_input("Horário Término"), st.text_input("Executante")
        if st.form_submit_button("Gravar Lavagem"):
            if c and e: 
                registrar_dados("Lavagem", [c, dt, m, p, i, t, e])
            else: 
                st.warning("Preencha Cliente e Executante.")

def pag_lavados(dt):
    st.header("Lançamento - Setor de Lavados")
    with st.form("f_lvd", clear_on_submit=True):
        c, m, p = st.text_input("Cliente"), st.text_input("Máquina"), st.text_input("Peso")
        i, t, e = st.text_input("Horário Início"), st.text_input("Horário Término"), st.text_input("Executante")
        if st.form_submit_button("Gravar Lavados"):
            if c and e: 
                registrar_dados("Lavados", [c, dt, m, p, i, t, e])
            else: 
                st.warning("Preencha os campos obrigatórios.")

def pag_secagem(dt):
    st.header("Lançamento - Setor de Secagem")
    with st.form("f_sec", clear_on_submit=True):
        m, c, ent, sai, e = st.text_input("Máquina"), st.text_input("Cliente"), st.text_input("Horário Entrada"), st.text_input("Horário Saída"), st.text_input("Executante")
        if st.form_submit_button("Gravar Secagem"):
            if c and e: 
                registrar_dados("Secagem", [m, c, dt, ent, sai, e])
            else: 
                st.warning("Preencha os campos obrigatórios.")

def pag_pesagem(dt):
    st.header("Lançamento - Setor de Pesagem")
    with st.form("f_pes", clear_on_submit=True):
        c, p, e = st.text_input("Cliente"), st.text_input("Pesagem"), st.text_input("Executante")
        tipo = st.radio("Tipo de Operação", ["Normal", "Relave"])
        if st.form_submit_button("Gravar Pesagem"):
            if c and e: 
                registrar_dados("Pesagem", [c, dt, p, e, tipo])
            else: 
                st.warning("Preencha os campos obrigatórios.")

def pag_dobragem(dt):
    st.header("Lançamento - Setor de Dobragem")
    with st.form("f_dob", clear_on_submit=True):
        c, e = st.text_input("Cliente"), st.text_input("Executante")
        st.markdown("### Contagem de Itens Dobrados")
        qtds = {it: st.number_input(f"Qtd {it}:", min_value=0, step=1, key=f"d_{it}") for it in ITENS_DOBRAGEM}
        if st.form_submit_button("Gravar Dobragem"):
            if c and e: 
                registrar_dados("Dobragem", [c, dt, e] + [int(qtds[it]) for it in ITENS_DOBRAGEM])
            else: 
                st.warning("Preencha Cliente e Executante.")

def pag_analises(dt):
    st.header("📊 Painel Estatístico e Resumos")
    filtro = st.text_input("🔍 Filtrar por Cliente (Vazio para todos)")
    if st.button("Gerar / Atualizar Relatórios"): 
        gerar_relatorios(filtro)

def pag_correcoes(dt):
    st.header("🛠️ Gerenciamento de Dados e Correções")
    s = st.selectbox("Setor:", ["Lavagem", "Lavados", "Secagem", "Pesagem", "Dobragem"])
    if st.button("Visualizar Linhas"): 
        puxar_historico_setor(s)
    st.markdown("---")
    st.caption("Apaga permanentemente a última linha adicionada na planilha selecionada acima.")
    conf = st.checkbox("Confirmar exclusão.")
    if st.button("🚨 Apagar Último Registro", disabled=not conf): 
        deletar_ultima_linha(s)

# --- CORPO PRINCIPAL DO APP ---
st.set_page_config(page_title="Controle Lavanderia", layout="wide")
st.sidebar.title("🧼 Navegação")
opcoes_menu = {
    "Lavagem": pag_lavagem, "Lavados": pag_lavados, "Secagem": pag_secagem,
    "Pesagem": pag_pesagem, "Dobragem": pag_dobragem, "📊 Resumos e Análises": pag_analises,
    "🛠️ Histórico e Deleção": pag_correcoes
}
menu = st.sidebar.radio("Selecione o Setor:", list(opcoes_menu.keys()))

st.sidebar.markdown("---")
st.sidebar.subheader("🔑 Autenticação")
arq = st.sidebar.file_uploader("Arquivo .json do Google:", type=["json"])
if arq is not None:
    st.session_state["google_json_data"] = arq.getvalue().decode("utf-8")
    st.sidebar.success("🔑 Chave carregada!")

dt_global = st.sidebar.date_input("Data do Lançamento:", datetime.date.today()).strftime("%d/%m/%Y")
st.title("🧼 Sistema de Controle de Lavanderia")

opcoes_menu[menu](dt_global)
