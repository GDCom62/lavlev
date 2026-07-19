import streamlit as st
import pandas as pd
import datetime
import requests

# === CONFIGURAÇÃO DEFINITIVA (INSIRA SEUS DADOS AQUI) ===
API_KEY = "COLE_AQUI_A_SUA_CHAVE_DE_API_GERADA_NO_PASSO_2"
# Abra sua planilha e copie o código grande de letras e números que fica no link dela:
SPREADSHEET_ID = "COLE_AQUI_O_ID_DA_SUA_PLANILHA" 

ITENS_DOBRAGEM = ["Lençol", "Fronha", "Capote", "Camisola", "Oleado", "Calça", "Camisa", "Cobertor", "Colcha", "Toalha", "Traçado"]

def registrar_dados_api(setor, dados):
    try:
        # Url oficial do Google Sheets para inserção via API simples REST
        url = f"https://googleapis.com{SPREADSHEET_ID}/values/{setor}:append"
        params = {"valueInputOption": "USER_ENTERED", "key": API_KEY}
        payload = {"values": [dados]}
        
        resposta = requests.post(url, params=params, json=payload)
        if resposta.status_code == 200:
            st.success(f"✅ Gravado com sucesso em {setor}!")
        else:
            st.error(f"❌ Erro na API do Google: {resposta.text}")
    except Exception as e:
        st.error(f"❌ Erro ao conectar: {e}")

def puxar_historico_api(setor):
    try:
        url = f"https://googleapis.com{SPREADSHEET_ID}/values/{setor}!A1:Z100"
        params = {"key": API_KEY}
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

def gerar_relatorios_api(filtro_cliente):
    try:
        setores = ["Lavagem", "Lavados", "Secagem", "Pesagem", "Dobragem"]
        df_geral = []
        
        for s in setores:
            url = f"https://googleapis.com{SPREADSHEET_ID}/values/{s}!A1:Z500"
            resposta = requests.get(url, params={"key": API_KEY})
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
            st.info("Nenhum dado encontrado.")

        st.subheader("2. Total de Peças Dobradas por Cliente e Executante")
        url_dob = f"https://googleapis.com{SPREADSHEET_ID}/values/Dobragem!A1:Z500"
        resp_dob = requests.get(url_dob, params={"key": API_KEY})
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
                st.info("Nenhum registro em Dobragem.")
    except Exception as e:
        st.error(f"Erro nos relatórios: {e}")

# --- FORMULÁRIOS DE LANÇAMENTO ---
def pag_lavagem(dt):
    st.header("Lançamento - Setor de Lavagem")
    with st.form("f_lav", clear_on_submit=True):
        c, m, p = st.text_input("Cliente"), st.text_input("Máquina"), st.text_input("Peso (ex: 45kg)")
        i, t, e = st.text_input("Horário Início"), st.text_input("Horário Término"), st.text_input("Executante")
        if st.form_submit_button("Gravar Lavagem"):
            if c and e: registrar_dados_api("Lavagem", [c, dt, m, p, i, t, e])
            else: st.warning("Preencha Cliente e Executante.")

def pag_lavados(dt):
    st.header("Lançamento - Setor de Lavados")
    with st.form("f_lvd", clear_on_submit=True):
        c, m, p = st.text_input("Cliente"), st.text_input("Máquina"), st.text_input("Peso")
        i, t, e = st.text_input("Horário Início"), st.text_input("Horário Término"), st.text_input("Executante")
        if st.form_submit_button("Gravar Lavados"):
            if c and e: registrar_dados_api("Lavados", [c, dt, m, p, i, t, e])
            else: st.warning("Preencha os campos obrigatórios.")

def pag_secagem(dt):
    st.header("Lançamento - Setor de Secagem")
    with st.form("f_sec", clear_on_submit=True):
        m, c, ent, sai, e = st.text_input("Máquina"), st.text_input("Cliente"), st.text_input("Horário Entrada"), st.text_input("Horário Saída"), st.text_input("Executante")
        if st.form_submit_button("Gravar Secagem"):
            if c and e: registrar_dados_api("Secagem", [m, c, dt, ent, sai, e])
            else: st.warning("Preencha os campos obrigatórios.")

def pag_pesagem(dt):
    st.header("Lançamento - Setor de Pesagem")
    with st.form("f_pes", clear_on_submit=True):
        c, p, e = st.text_input("Cliente"), st.text_input("Pesagem"), st.text_input("Executante")
        tipo = st.radio("Tipo de Operação", ["Normal", "Relave"])
        if st.form_submit_button("Gravar Pesagem"):
            if c and e: registrar_dados_api("Pesagem", [c, dt, p, e, tipo])
            else: st.warning("Preencha os campos obrigatórios.")

def pag_dobragem(dt):
    st.header("Lançamento - Setor de Dobragem")
    with st.form("f_dob", clear_on_submit=True):
        c, e = st.text_input("Cliente"), st.text_input("Executante")
        st.markdown("### Contagem de Itens Dobrados")
        qtds = {it: st.number_input(f"Qtd {it}:", min_value=0, step=1, key=f"d_{it}") for it in ITENS_DOBRAGEM}
        if st.form_submit_button("Gravar Dobragem"):
            if c and e: registrar_dados_api("Dobragem", [c, dt, e] + [int(qtds[it]) for it in ITENS_DOBRAGEM])
            else: st.warning("Preencha Cliente e Executante.")

def pag_analises(dt):
    st.header("📊 Painel Estatístico e Resumos")
    filtro = st.text_input("🔍 Filtrar por Cliente (Vazio para todos)")
    if st.button("Gerar / Atualizar Relatórios"): gerar_relatorios_api(filtro)

def pag_correcoes(dt):
    st.header("🛠️ Histórico de Lançamentos")
    s = st.selectbox("Setor:", ["Lavagem", "Lavados", "Secagem", "Pesagem", "Dobragem"])
    if st.button("Visualizar Últimas Linhas"): puxar_historico_api(s)

# --- CORPO PRINCIPAL ---
st.set_page_config(page_title="Controle Lavanderia", layout="wide")
st.sidebar.title("🧼 Navegação")
opcoes_menu = {
    "Lavagem": pag_lavagem, "Lavados": pag_lavados, "Secagem": pag_secagem,
    "Pesagem": pag_pesagem, "Dobragem": pag_dobragem, "📊 Resumos e Análises": pag_analises,
    "🛠️ Histórico": pag_correcoes
}
menu = st.sidebar.radio("Selecione o Setor:", list(opcoes_menu.keys()))

dt_global = st.sidebar.date_input("Data do Lançamento:", datetime.date.today()).strftime("%d/%m/%Y")
opcoes_menu[menu](dt_global)
