import streamlit as st
import pandas as pd
import datetime
import psycopg2

ITENS_DOBRAGEM = ["Lençol", "Fronha", "Capote", "Camisola", "Oleado", "Calça", "Camisa", "Cobertor", "Colcha", "Toalha", "Traçado"]

# --- CONEXÃO COM O BANCO DE DADOS ---
def conectar_banco(db_uri):
    return psycopg2.connect(db_uri)

# Gravação Genérica no Banco SQL
def registrar_dados_sql(db_uri, tabela, colunas, dados):
    try:
        conexao = conectar_banco(db_uri)
        cursor = conexao.cursor()
        
        placeholders = ", ".join(["%s"] * len(dados))
        colunas_str = ", ".join(colunas)
        query = f"INSERT INTO {tabela} ({colunas_str}) VALUES ({placeholders})"
        
        cursor.execute(query, dados)
        conexao.commit()
        st.success(f"✅ Gravado com sucesso em {tabela.capitalize()}!")
    except Exception as e:
        st.error(f"❌ Erro ao salvar no banco: {e}")
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conexao' in locals(): conexao.close()

# Puxa o histórico de um setor específico
def puxar_historico_sql(db_uri, tabela):
    try:
        conexao = conectar_banco(db_uri)
        query = f"SELECT * FROM {tabela} ORDER BY id DESC LIMIT 10"
        df = pd.read_sql_query(query, conexao)
        
        if df.empty:
            st.info("Tabela vazia sem registros.")
        else:
            st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.error(f"❌ Erro ao buscar histórico: {e}")
    finally:
        if 'conexao' in locals(): conexao.close()

# Gera relatórios consolidados usando queries SQL
def gerar_relatorios_sql(db_uri, filtro_cliente):
    try:
        conexao = conectar_banco(db_uri)
        setores = ["lavagem", "lavados", "secagem", "pesagem", "dobragem"]
        df_geral = []
        
        for s in setores:
            query = f"SELECT executante, '{s}' as setor FROM {s}"
            if filtro_cliente:
                query += f" WHERE cliente ILIKE %s"
                df = pd.read_sql_query(query, conexao, params=(f"%{filtro_cliente}%",))
            else:
                df = pd.read_sql_query(query, conexao)
                
            if not df.empty:
                df_geral.append(df)

        st.subheader("1. Quantidade de Operações por Funcionário / Setor")
        if df_geral:
            res = pd.concat(df_geral, ignore_index=True).groupby(["executante", "setor"]).size().unstack(fill_value=0)
            res["Total Geral"] = res.sum(axis=1)
            st.dataframe(res, use_container_width=True)
        else:
            st.info("Nenhum dado encontrado para gerar o resumo de funcionários.")

        st.subheader("2. Total de Peças Dobradas por Cliente e Executante")
        cols_sql = ", ".join([it.lower().replace("ç", "c").replace("ã", "a") for it in ITENS_DOBRAGEM])
        query_dob = f"SELECT cliente, executante, {cols_sql} FROM dobragem"
        
        if filtro_cliente:
            query_dob += " WHERE cliente ILIKE %s"
            df_dob = pd.read_sql_query(query_dob, conexao, params=(f"%{filtro_cliente}%",))
        else:
            df_dob = pd.read_sql_query(query_dob, conexao)

        if not df_dob.empty:
            mapeamento = {it.lower().replace("ç", "c").replace("ã", "a"): it for it in ITENS_DOBRAGEM}
            df_dob = df_dob.rename(columns=mapeamento)
            
            res_pecas = df_dob.groupby(["Cliente", "executante"]).sum()
            res_pecas["Total de Peças"] = res_pecas.sum(axis=1)
            st.dataframe(res_pecas, use_container_width=True)
        else:
            st.info("Nenhum registro encontrado em Dobragem.")
            
    except Exception as e:
        st.error(f"Erro nos relatórios: {e}")
    finally:
        if 'conexao' in locals(): conexao.close()

# --- FORMULÁRIOS DE LANÇAMENTO ---
def pag_lavagem(dt, db_uri):
    st.header("Lançamento - Setor de Lavagem")
    with st.form("f_lav", clear_on_submit=True):
        c, m, p = st.text_input("Cliente"), st.text_input("Máquina"), st.text_input("Peso (ex: 45kg)")
        i, t, e = st.text_input("Horário Início"), st.text_input("Horário Término"), st.text_input("Executante")
        if st.form_submit_button("Gravar Lavagem"):
            if db_uri:
                if c and e: 
                    colunas = ["cliente", "data", "maquina", "peso", "horario_inicio", "horario_termino", "executante"]
                    registrar_dados_sql(db_uri, "lavagem", colunas, [c, dt, m, p, i, t, e])
                else: st.warning("Preencha Cliente e Executante.")
            else: st.error("⚠️ Configure a String de Conexão SQL no menu lateral.")

def pag_lavados(dt, db_uri):
    st.header("Lançamento - Setor de Lavados")
    with st.form("f_lvd", clear_on_submit=True):
        c, m, p = st.text_input("Cliente"), st.text_input("Máquina"), st.text_input("Peso")
        i, t, e = st.text_input("Horário Início"), st.text_input("Horário Término"), st.text_input("Executante")
        if st.form_submit_button("Gravar Lavados"):
            if db_uri:
                if c and e: 
                    colunas = ["cliente", "data", "maquina", "peso", "horario_inicio", "horario_termino", "executante"]
                    registrar_dados_sql(db_uri, "lavados", colunas, [c, dt, m, p, i, t, e])
                else: st.warning("Preencha os campos obrigatórios.")
            else: st.error("⚠️ Configure os dados de acesso.")

def pag_secagem(dt, db_uri):
    st.header("Lançamento - Setor de Secagem")
    with st.form("f_sec", clear_on_submit=True):
        m, c, ent, sai, e = st.text_input("Máquina"), st.text_input("Cliente"), st.text_input("Horário Entrada"), st.text_input("Horário Saída"), st.text_input("Executante")
        if st.form_submit_button("Gravar Secagem"):
            if db_uri:
                if c and e: 
                    colunas = ["maquina", "cliente", "data", "horario_entrada", "horario_saida", "executante"]
                    registrar_dados_sql(db_uri, "secagem", colunas, [m, c, dt, ent, sai, e])
                else: st.warning("Preencha os campos obrigatórios.")
            else: st.error("⚠️ Configure os dados de acesso.")

def pag_pesagem(dt, db_uri):
    st.header("Lançamento - Setor de Pesagem")
    with st.form("f_pes", clear_on_submit=True):
        c, p, e = st.text_input("Cliente"), st.text_input("Pesagem"), st.text_input("Executante")
        tipo = st.radio("Tipo de Operação", ["Normal", "Relave"])
        if st.form_submit_button("Gravar Pesagem"):
            if db_uri:
                if c and e: 
                    colunas = ["cliente", "data", "pesagem", "executante", "tipo_operacao"]
                    registrar_dados_sql(db_uri, "pesagem", colunas, [c, dt, p, e, tipo])
                else: st.warning("Preencha os campos obrigatórios.")
            else: st.error("⚠️ Configure os dados de acesso.")

def pag_dobragem(dt, db_uri):
    st.header("Lançamento - Setor de Dobragem")
    with st.form("f_dob", clear_on_submit=True):
        c, e = st.text_input("Cliente"), st.text_input("Executante")
        st.markdown("### Contagem de Itens Dobrados")
        qtds = {it: st.number_input(f"Qtd {it}:", min_value=0, step=1, key=f"d_{it}") for it in ITENS_DOBRAGEM}
        if st.form_submit_button("Gravar Dobragem"):
            if db_uri:
                if c and e:
                    colunas_itens = [it.lower().replace("ç", "c").replace("ã", "a") for it in ITENS_DOBRAGEM]
                    colunas = ["cliente", "data", "executante"] + colunas_itens
                    valores = [c, dt, e] + [int(qtds[it]) for it in ITENS_DOBRAGEM]
                    registrar_dados_sql(db_uri, "dobragem", colunas, valores)
                else: st.warning("Preencha Cliente e Executante.")
            else: st.error("⚠️ Configure os dados de acesso.")

def pag_analises(dt, db_uri):
    st.header("📊 Painel Estatístico e Resumos")
    filtro = st.text_input("🔍 Filtrar por Cliente (Vazio para todos)")
    if st.button("Gerar / Atualizar Relatórios"): 
        if db_uri: gerar_relatorios_sql(db_uri, filtro)
        else: st.error("⚠️ Configure os dados de acesso.")

def pag_correcoes(dt, db_uri):
    st.header("🛠️ Histórico de Lançamentos")
    s = st.selectbox("Setor:", ["lavagem", "lavados", "secagem", "pesagem", "dobragem"])
    if st.button("Visualizar Últimas Linhas"): 
        if db_uri: puxar_historico_sql(db_uri, s)
        else: st.error("⚠️ Configure os dados de acesso no menu lateral.")

# --- CORPO PRINCIPAL INTERFACE ---
st.set_page_config(page_title="Controle Lavanderia", layout="wide")

# Configurações de Conexão na Sidebar (Banco SQL na Nuvem)
st.sidebar.title("⚙️ Configurações Nuvem")
input_db_uri = st.sidebar.text_input("String de Conexão SQL (PostgreSQL URI):", type="password")

st.sidebar.markdown("---")
st.sidebar.title("🧼 Navegação")
opcoes_menu = {
    "Lavagem": pag_lavagem, 
    "Lavados": pag_lavados, 
    "Secagem": pag_secagem,
    "Pesagem": pag_pesagem, 
    "Dobragem": pag_dobragem, 
    "📊 Resumos e Análises": pag_analises,
    "🛠️ Histórico": pag_correcoes
}
menu = st.sidebar.radio("Selecione o Setor:", list(opcoes_menu.keys()))

dt_global = st.sidebar.date_input("Data do Lançamento:", datetime.date.today())

# Executa a página correspondente passando os parâmetros SQL atualizados
opcoes_menu[menu](dt_global, input_db_uri)
