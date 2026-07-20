import streamlit as st
import pandas as pd
import datetime
import requests

ITENS_DOBRAGEM = ["Lençol", "Fronha", "Capote", "Camisola", "Oleado", "Calça", "Camisa", "Cobertor", "Colcha", "Toalha", "Traçado"]

def registrar_dados_api(spreadsheet_id, api_key, setor, dados):
    try:
        # URL Oficial corrigida do Google Sheets v4 API
        url = f"https://googleapis.com{spreadsheet_id}/values/{setor}:append"
        params = {"valueInputOption": "USER_ENTERED", "key": api_key}
        payload = {"values": [dados]}
        
        resposta = requests.post(url, params=params, json=payload)
        if resposta.status_code == 200:
            st.success(f"✅ Gravado com sucesso em {setor}!")
        else:
            st.error(f"❌ Erro na API do Google: {resposta.text}")
    except Exception as e:
        st.error(f"❌ Erro ao conectar: {e}")

def puxar_historico_api(spreadsheet_id, api_key, setor):
    try:
        url = f"https://googleapis.com{spreadsheet_id}/values/{setor}!A1:Z100"
        params = {"key": api_key}
        resposta = requests.get(url, params=params)
        
        if resposta.status_code == 200:
            dados = resposta.json().get("values", [])
            if len(dados) <= 1:
                st.info("Aba vazia ou apenas com cabeçalho.")
            else:
                df = pd.DataFrame(dados[1:], columns=dados[0])
                st.dataframe(df.tail(10), use_container_width=True)
        else:
            st.error(f"❌ Erro ao buscar histórico: {resposta.text}")
    except Exception as e:
        st.error(f"Erro: {e}")

def gerar_relatorios_api(spreadsheet_id, api_key, filtro_cliente):
    try:
        setores = ["Lavagem", "Lavados", "Secagem", "Pesagem", "Dobragem"]
        df_geral = []
        
        for s in setores:
            url = f"https://googleapis.com{spreadsheet_id}/values/{s}!A1:Z500"
            resposta = requests.get(url, params={"key": api_key})
            if resposta.status_code == 200:
                dados = resposta.json().get("values", [])
                if len(dados) > 1:
                    df = pd.DataFrame(dados[1:], columns=dados[0])
                    df = df.rename(columns={"Nome Executante": "Executante"})
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
            st.info("Nenhum dado encontrado para gerar o resumo de funcionários.")

        st.subheader("2. Total de Peças Dobradas por Cliente e Executante")
        url_dob = f"https://googleapis.com{spreadsheet_id}/values/Dobragem!A1:Z500"
        resp_dob = requests.get(url_dob, params={"key": api_key})
        if resp_dob.status_code == 200:
            dados_dob = resp_dob.json().get("values", [])
            if len(dados_dob) > 1:
                df_dob = pd.DataFrame(dados_dob[1:], columns=dados_dob[0]).rename(columns={"Nome Executante": "Executante"})
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
                st.info("Nenhum registro encontrado em Dobragem.")
    except Exception as e:
        st.error(f"Erro nos relatórios: {e}")

# --- FORMULÁRIOS DE LANÇAMENTO ---
def pag_lavagem(dt, sheet_id, key):
    st.header("Lançamento - Setor de Lavagem")
    with st.form("f_lav", clear_on_submit=True):
        c, m, p = st.text_input("Cliente"), st.text_input("Máquina"), st.text_input("Peso (ex: 45kg)")
        i, t, e = st.text_input("Horário Início"), st.text_input("Horário Término"), st.text_input("Executante")
        if st.form_submit_button("Gravar Lavagem"):
            if sheet_id and key:
                if c and e: registrar_dados_api(sheet_id, key, "Lavagem", [c, dt, m, p, i, t, e])
                else: st.warning("Preencha Cliente e Executante.")
            else: st.error("⚠️ Configure a Chave de API e o ID da Planilha no menu lateral.")

def pag_lavados(dt, sheet_id, key):
    st.header("Lançamento - Setor de Lavados")
    with st.form("f_lvd", clear_on_submit=True):
        c, m, p = st.text_input("Cliente"), st.text_input("Máquina"), st.text_input("Peso")
        i, t, e = st.text_input("Horário Início"), st.text_input("Horário Término"), st.text_input("Executante")
        if st.form_submit_button("Gravar Lavados"):
            if sheet_id and key:
                if c and e: registrar_dados_api(sheet_id, key, "Lavados", [c, dt, m, p, i, t, e])
                else: st.warning("Preencha os campos obrigatórios.")
            else: st.error("⚠️ Configure os dados de acesso no menu lateral.")

def pag_secagem(dt, sheet_id, key):
    st.header("Lançamento - Setor de Secagem")
    with st.form("f_sec", clear_on_submit=True):
        m, c, ent, sai, e = st.text_input("Máquina"), st.text_input("Cliente"), st.text_input("Horário Entrada"), st.text_input("Horário Saída"), st.text_input("Executante")
        if st.form_submit_button("Gravar Secagem"):
            if sheet_id and key:
                if c and e: registrar_dados_api(sheet_id, key, "Secagem", [m, c, dt, ent, sai, e])
                else: st.warning("Preencha os campos obrigatórios.")
            else: st.error("⚠️ Configure os dados de acesso no menu lateral.")

def pag_pesagem(dt, sheet_id, key):
    st.header("Lançamento - Setor de Pesagem")
    with st.form("f_pes", clear_on_submit=True):
        c, p, e = st.text_input("Cliente"), st.text_input("Pesagem"), st.text_input("Executante")
        tipo = st.radio("Tipo de Operação", ["Normal", "Relave"])
        if st.form_submit_button("Gravar Pesagem"):
            if sheet_id and key:
                if c and e: registrar_dados_api(sheet_id, key, "Pesagem", [c, dt, p, e, tipo])
                else: st.warning("Preencha os campos obrigatórios.")
            else: st.error("⚠️ Configure os dados de acesso no menu lateral.")

def pag_dobragem(dt, sheet_id, key):
    st.header("Lançamento - Setor de Dobragem")
    with st.form("f_dob", clear_on_submit=True):
        c, e = st.text_input("Cliente"), st.text_input("Executante")
        st.markdown("### Contagem de Itens Dobrados")
        qtds = {it: st.number_input(f"Qtd {it}:", min_value=0, step=1, key=f"d_{it}") for it in ITENS_DOBRAGEM}
        if st.form_submit_button("Gravar Dobragem"):
            if sheet_id and key:
                if c and e: registrar_dados_api(sheet_id, key, "Dobragem", [c, dt, e] + [int(qtds[it]) for it in ITENS_DOBRAGEM])
                else: st.warning("Preencha Cliente e Executante.")
            else: st.error("⚠️ Configure os dados de acesso no menu lateral.")

def pag_analises(dt, sheet_id, key):
    st.header("📊 Painel Estatístico e Resumos")
    filtro = st.text_input("🔍 Filtrar por Cliente (Vazio para todos)")
    if st.button("Gerar / Atualizar Relatórios"): 
        if sheet_id and key: gerar_relatorios_api(sheet_id, key, filtro)
        else: st.error("⚠️ Configure os dados de acesso no menu lateral.")

def pag_correcoes(dt, sheet_id, key):
    st.header("🛠️ Histórico de Lançamentos")
    s = st.selectbox("Setor:", ["Lavagem", "Lavados", "Secagem", "Pesagem", "Dobragem"])
    if st.button("Visualizar Últimas Linhas"): 
        if sheet_id and key: puxar_historico_api(sheet_id, key, s)
        else: st.error("⚠️ Configure os dados de acesso no menu lateral.")

# --- CORPO PRINCIPAL ---
st.set_page_config(page_title="Controle Lavanderia", layout="wide")

# Configurações de Conexão na Sidebar (Protegido e Dinâmico)
st.sidebar.title("⚙️ Configurações Google")
input_api_key = st.sidebar.text_input("Chave de API do Google:", type="password")
input_sheet_id = st.sidebar.text_input("ID da Planilha (Spreadsheet ID):")

st.sidebar.markdown("---")
st.sidebar.title("🧼 Navegação")
opcoes_menu = {
    "Lavagem": pag_lavagem, "Lavados": pag_lavados, "Secagem": pag_secagem,
    "Pesagem": pag_pesagem, "Dobragem": pag_dobragem, "📊 Resumos e Análises": pag_analises,
    "🛠️ Histórico": pag_correcoes
}
menu = st.sidebar.radio("Selecione o Setor:", list(opcoes_menu.keys()))

dt_global = st.sidebar.date_input("Data do Lançamento:", datetime.date.today()).strftime("%d/%m/%Y")

# Executa a página enviando os parâmetros da interface de forma limpa
opcoes_menu[menu](dt_global, input_sheet_id, input_api_key)
