import datetime
import gspread
import pandas as pd
import streamlit as st
from oauth2client.service_account import ServiceAccountCredentials

# Configuração da página do Streamlit
st.set_page_config(page_title="Controle Lavanderia", page_icon="🧺", layout="wide")

# 1. Conexão Segura usando Secrets do Streamlit
def conectar_sheets():
    escopo = ["https://google.com", "https://googleapis.com"]
    # Transforma o dicionário dos Secrets em credenciais válidas
    info_credenciais = dict(st.secrets["gspread_credentials"])
    credenciais = ServiceAccountCredentials.from_json_keyfile_dict(info_credenciais, escopo)
    cliente = gspread.authorize(credenciais)
    return cliente.open(st.secrets["nome_planilha"])

# Função para Gravação
def registrar_producao(setor, dados):
    try:
        planilha = conectar_sheets()
        aba = planilha.worksheet(setor)
        aba.append_row(dados)
        st.success(f"✅ Dados registrados com sucesso no setor {setor}!")
    except Exception as e:
        st.error(f"❌ Erro ao gravar dados: {e}")

# Interface Web
st.title("🧺 Sistema de Controle de Lavanderia")

# Criando as abas de navegação na página web
aba_lancamento, aba_resumo = st.tabs(["📝 Lançar Dados", "📊 Resumo de Produção"])

with aba_lancamento:
    st.header("Novo Registro")
    setor = st.selectbox("Selecione o Setor:", ["Lavagem", "Lavados", "Secagem", "Pesagem", "Dobragem"])
    
    data_hoje = datetime.date.today().strftime("%d/%m/%Y")
    
    # Formulário dinâmico baseado no setor selecionado
    with st.form("form_registro", clear_on_submit=True):
        if setor == "Lavagem" or setor == "Lavados":
            cliente = st.text_input("Cliente")
            maquina = st.text_input("Máquina")
            peso = st.text_input("Peso (ex: 45kg)")
            inicio = st.text_input("Horário de Início (ex: 08:00)")
            termino = st.text_input("Horário de Término (ex: 09:15)")
            executante = st.text_input("Nome do Executante")
            
            enviado = st.form_submit_button("Gravar Registro")
            if enviado:
                registrar_producao(setor, [cliente, data_hoje, maquina, peso, inicio, termino, executante])
                
        elif setor == "Secagem":
            maquina = st.text_input("Máquina")
            cliente = st.text_input("Cliente")
            entrada = st.text_input("Horário de Entrada")
            saida = st.text_input("Horário de Saída")
            executante = st.text_input("Nome do Executante")
            
            enviado = st.form_submit_button("Gravar Registro")
            if enviado:
                registrar_producao(setor, [maquina, cliente, data_hoje, entrada, saida, executante])
                
        elif setor == "Pesagem":
            cliente = st.text_input("Cliente")
            pesagem = st.text_input("Pesagem / Peso")
            executante = st.text_input("Nome do Executante")
            tipo = st.radio("Tipo de Operação", ["Normal", "Relave"])
            
            enviado = st.form_submit_button("Gravar Registro")
            if enviado:
                registrar_producao(setor, [cliente, data_hoje, pesagem, executante, tipo])
                
        elif setor == "Dobragem":
            cliente = st.text_input("Cliente")
            item = st.text_input("Item da Rouparia")
            qtd = st.number_input("Quantidade", min_value=1, step=1)
            executante = st.text_input("Nome do Executante")
            
            enviado = st.form_submit_button("Gravar Registro")
            if enviado:
                registrar_producao(setor, [cliente, data_hoje, item, int(qtd), executante])

with aba_resumo:
    st.header("Análise de Produção Individual")
    
    if st.button("🔄 Atualizar Indicadores"):
        try:
            with st.spinner("Buscando dados no Google Sheets..."):
                planilha = conectar_sheets()
                setores = ["Lavagem", "Lavados", "Secagem", "Pesagem", "Dobragem"]
                df_geral = []

                for s in setores:
                    dados = planilha.worksheet(s).get_all_records()
                    if dados:
                        df = pd.DataFrame(dados)
                        df = df.rename(columns={"Nome Executante": "Executante"})
                        df["Setor"] = s
                        df_geral.append(df[["Executante", "Setor"]])

                if df_geral:
                    df_consolidado = pd.concat(df_geral, ignore_index=True)
                    resumo = df_consolidado.groupby(["Executante", "Setor"]).size().unstack(fill_value=0)
                    resumo["Total Geral"] = resumo.sum(axis=1)
                    
                    # Exibe a tabela interativa na tela do Streamlit
                    st.dataframe(resumo, use_container_width=True)
                    
                    # Atualiza a aba do Google Sheets
                    aba_resumo_sheet = planilha.worksheet("Resumo") if "Resumo" in [w.title for w in planilha.worksheets()] else planilha.add_worksheet(title="Resumo", rows="100", cols="10")
                    aba_resumo_sheet.clear()
                    aba_resumo_sheet.update([resumo.reset_index().columns.values.tolist()] + resumo.reset_index().values.tolist())
                    st.toast("Google Sheets Sincronizado!", icon="🔄")
                else:
                    st.info("Nenhum dado encontrado para gerar gráficos ou resumos.")
        except Exception as e:
            st.error(f"Erro ao processar resumo: {e}")
