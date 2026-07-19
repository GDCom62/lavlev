import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import datetime
import base64
import json

# Nome da sua planilha no Google Drive
NOME_PLANILHA = "Controle_Lavanderia"

# === CREDENCIAIS DO GOOGLE EM BASE64 (BLINDADO CONTRA ERROS) ===
CREDENCIAIS_BASE64 = "ewogICJ0eXBlIjogInNlcnZpY2VfYWNjb3VudCIsCiAgInByb2plY3RfaWQiOiAibGF2YW5kZXJpYS12MjYiLAogICJwcm9qZWN0X2tleV9pZCI6ICI1ZDk0OGU1NDk2M2JmZWZjYjUxZjUxOWE5MmFjMGM4NmI3YzEyYTkiLAogICJwcml2YXRlX2tleSI6ICItLS0tLUJFR0lOIFBSSVZBVEUgS0VZLS0tLS1cbk1JSUV2QUlCQURBTkJna3Foa2lHOXcwQkFRRUZBQVNDQktZd2dnU2lBZ0VBQW9JQkFRQ20zTXVreEptUks0YkoXbkVsNmtlRTBkR0JUZjkvdUFGNDgvan野生dXQ0dTgvdC81M0owQ2l2NHB1K2d0dys2WFVlb horrificNjg3cThZSXJ6eFlzXG4ydnBqd25ReWNERXpLMDREVHpEaDhHZGoya1JrZFFJaHFNakphTVRKMHlzQ3c2M3Q0YnBUV0FlRTB2RUhScUR6XG4yS2xreloadingNxREZLNlowV0d6bVBVOGVER2tTZnRnNkZCN0F5MTNyc2lxbjYva09tU0RJZmZ4ZVJmUGcxVnZWZVxu国防ZXg3Y1V6SHNzR2ZSWXhFdlNYN3loWkg2WFhyK0FtZlxuZlZSbTF3VFhSUnVxL211YStta3dwb3ZvOVVDdlRaMHZWVHd3RkVNb2tQZER6a0dGY2dyYUhUNm9PdTZmaHlIdlxuS3NMRFF1NFJBZ01CQUFFQ2dnRUFGRUZKWFpVQi83R2lUQXBsTDI4VWdrZDc4amVJb2FNS2ZpRStxR0FicFhjVVxuNWpzZk1SclI2RGlGVnNiUFdaaHdURDF5SEVvcWdGMmtIZ2dMVEx5TUxSckIyQnIzZXBXdjAvOWlGNGlGWE0wUVxuMEF2c2FxbURlTkhmdnRkSng4OXV0aU1CajZXcEFTWjVQM3h4alZYeHZMMCExak5XUnJYTFAtOElYUlJCdmVhYVxuSjZzS3B3MlI3a3dCcU5pSGVPeXFYclZ0bEYwVVVjNUNLS0tvdUpzU203Z253T01zWTd6Z1VSdFVLRmwxazhsb1xueDZxbE9NRW1nNXNHRDY3MGIvUU54OStJNngreUJwZE1iWERlTThOWE5nbDBXM1ZnNGFrMW1NdEpKRmVENTkvaVx3XG5FemJUcFZvcWpOeW9VbjUvWUIxeVNJUVhoVVoySEcwdndCNXRkUmV3T1FLQmdRRGVMRUN2MzVYSTVjZEJpWDY3XG40NG5hR0ZiZVRKWFhkb255OHZxeXZjSHZXUmlYd1lSbVJJdWdaY3hwS3lBVis2TmlkRElHenQ5S3NYT2NDTlloXG5xcFNlclN6RWg4Z0plTXExS0hBQWxYT216TGVtT2R4czBIaHZJQ2d4VlJFdHpHa2JVMjZyeDRId0tneVIvQ2RKXG5CY2JKRjAyamIrWDZsalMvQ0RMWmhjc09RS0JnUURBUks1cjQ5WWhNM2tmNUhRbGtONWpuM210UlZoWk93b1Ncbk9obGlMOS90Q0hpcW5VYXBoR011QmpiZFUrK3ZZNW9pR1JPZ2czWS91cGVPMTNDV01QaWpBUUJqQVhZSjh2U1lcbnpYVHJTekJ2c0dTNk9YRk9pdXNJMnRQaGlmaDFjaEpOWkxvZDNCaW1pcFYxL3d5TG84N3FRQUpENTtnTG42Si9cbjR0czRUVU5BbVFLQmdHU0lFN0ZCYyt1TXhmQUMzbVQ0bmcwdGhERlhFdzlqTHpMb3hkbkdkRTk5UktvNm8wMWRQXG5WdnI2b01mcDZyZm55Tk9wRG1ZRVFBZlZhaUhGNGRjVUQvSUpISVBGaVIrNEY4bUhiNzdONGFvdFlrQ0dXQmFvXG44b1llUC9HcXMzNU15NWJBMXdoRjNNekFUalhVcXBYaFZnVHlWWUF3c0JFRzNORkFUSHJiUmtzSkFvR0FVSkozXG5wYTdzNVN6MDdYQ0hXOWJCMjIzUlI5TnZtclVyRzBoTnF0LzFMeGdGdVRuL2lycDM5YW1WQkZ0UWJtZUhDQk1LXG5McEhvMC93VjF6NWhhQTlOb3NHZ3I5ekU0cFoxK2pMZmRFQldJL24vdkNxbVdRdk9Rdit4R3lyK2UvazV3a1ViXG4yYmVLZlFCR2NoUlg1WXpZQVVOaHNHTlcwc2dyQ1B6QWNXK29zc0VDZ1lCR243cXArVWp3dTNLclVYZlVDV2Z4XG42U1U0WE9QbWtPR2FaYzBTTjNIXFQ4Z1d0ZEc0YVZyTkNQakppWHpyUmlHWktoN2lZTTUwQUhiWkt2T01HbFlcbnJ6N2ZRV3NkRlB6dHF4UFFCUTRidVlMQVdldGRxOGJQaEM4aW9TYk5jcXZveU1IVitJaHhvVkZDMUtEN2JoRUJca2krS1JwQnl3S1JveUFHUHRMSG9xQT09XG4tLS0tLUVORCBQUklWQVRFIEtFWS0tLS0tXG4iLAogICJjbGllbnRfZW1haWwiOiAibGF2bGV2QGxhdmFuZGVyaWEtdjI2LmlhbS5nc2VydmljZWFjY291bnQuY29tIiwK  "client_id": "114411858353263035553bIiwKICAiYXV0aF91cmkiOiAiaHR0cHM6Ly9hY2NvdW50cy5nb29nbGUuY29tL28vb2F1dGgyL2F1dGgiLAogICJ0b2tlbl91cmkiOiAiaHR0cHM6Ly9vYXV0aDIuZ29vZ2xlYXBpcy5jb20vdG9rZW4iLAogICJhdXRoX3Byb3ZpZGVyX3g1MDlfY2VydF91cmkiOiAiaHR0cHM6Ly93d3cuZ29vZ2xlYXBpcy5jb20vb2F1dGgyL3YxL2NlcnRzIiwKICAiY2xpZW50X3g1MDlfY2VydF91cmkiOiAiaHR0cHM6Ly93d3cuZ29vZ2xlYXBpcy5jb20vcm9ib3QvdjEvbWV0YWRhdGEveDUwOS9sYXZsZXYlNDBsYXZhbmRlcmlhLXYyNi5pYW0uZ3NlcnZpY2VhY291bnQuY29tIiwKICAidW5pdmVyc2VfZG9tYWluIjogImdvb2dsZWFwaXMuY29tIgp9"

# Lista de itens do setor de dobragem
ITENS_DOBRAGEM = ["Lençol", "Fronha", "Capote", "Camisola", "Oleado", "Calça", "Camisa", "Cobertor", "Colcha", "Toalha", "Traçado"]

@st.cache_resource
def conectar_sheets():
    escopo = ["https://google.com", "https://googleapis.com"]
    
    # Decodifica as credenciais salvas de forma direta no código
    json_reconstruido = base64.b64decode(CREDENCIAIS_BASE64).decode('utf-8')
    credenciais_dict = json.loads(json_reconstruido)
    
    if "private_key" in credenciais_dict:
        credenciais_dict["private_key"] = credenciais_dict["private_key"].replace("\\n", "\n")
        
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
