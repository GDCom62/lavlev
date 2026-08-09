import streamlit as st
import pandas as pd
import datetime
import psycopg2

# Configuração da página precisa ser O PRIMEIRO comando Streamlit executado
st.set_page_config(page_title="Controle Lavanderia", layout="wide")

ITENS_DOBRAGEM = ["Lençol", "Fronha", "Capote", "Camisola", "Oleado", "Calça", "Camisa", "Cobertor", "Colcha", "Toalha", "Traçado"]

# --- CONEXÃO COM O BANCO DE DADOS (SOB DEMANDA) ---
def conectar_banco():
    try:
        if "banco_dados" in st.secrets and "uri" in st.secrets["banco_dados"]:
            db_uri = st.secrets["banco_dados"]["uri"]
            return psycopg2.connect(db_uri)
        else:
            st.error("⚠️ Configuração 'uri' não encontrada dentro do bloco 'banco_dados' nos Secrets!")
            return None
    except Exception as e:
        st.error(f"⚠️ Erro ao tentar conectar ao PostgreSQL: {e}")
        return None

# Gravação Genérica no Banco SQL
def registrar_dados_sql(tabela, colunas, dados):
    conexao = conectar_banco()
    if conexao is None:
        st.error("❌ Não foi possível gravar. Sem conexão com o banco.")
        return
        
    try:
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
        if 'cursor' in locals() and cursor: cursor.close()
        if conexao: conexao.close()

# --- BUSCA HISTÓRICO COM FILTROS AVANÇADOS ---
def puxar_historico_filtrado_sql(tabela, filtro_cliente, filtro_colaborador):
    conexao = conectar_banco()
    if conexao is None:
        return pd.DataFrame()
        
    try:
        query = f"SELECT * FROM {tabela} WHERE 1=1"
        params = []
        if filtro_cliente:
            query += " AND cliente ILIKE %s"
            params.append(f"%{filtro_cliente}%")
        if filtro_colaborador:
            query += " AND executante ILIKE %s"
            params.append(f"%{filtro_colaborador}%")
        query += " ORDER BY id DESC LIMIT 50"
        df = pd.read_sql_query(query, conexao, params=params)
        return df
    except Exception as e:
        st.error(f"❌ Erro ao buscar dados: {e}")
        return pd.DataFrame()
    finally:
        if conexao: conexao.close()

# --- SALVAR MODIFICAÇÕES (EDIÇÃO E EXCLUSÃO) ---
def salvar_alteracoes_banco(tabela, df_original, e_editado):
    conexao = conectar_banco()
    if conexao is None:
        st.error("❌ Alterações não salvas. Sem conexão com o banco.")
        return
        
    try:
        cursor = conexao.cursor()
        sucesso = False
        
        if "deleted_rows" in e_editado and e_editado["deleted_rows"]:
            for indice in e_editado["deleted_rows"]:
                id_registro = int(df_original.iloc[indice]["id"])
                cursor.execute(f"DELETE FROM {tabela} WHERE id = %s", (id_registro,))
            sucesso = True
            
        if "edited_rows" in e_editado and e_editado["edited_rows"]:
            for indice_str, mudancas in e_editado["edited_rows"].items():
                indice = int(indice_str)
                id_registro = int(df_original.iloc[indice]["id"])
                for coluna, novo_valor in mudancas.items():
                    if coluna == "id": continue 
                    query = f"UPDATE {tabela} SET {coluna} = %s WHERE id = %s"
                    cursor.execute(query, (novo_valor, id_registro))
            sucesso = True
            
        if sucesso:
            conexao.commit()
            st.success("✅ Banco de dados atualizado com sucesso!")
            st.rerun()
    except Exception as e:
        conexao.rollback()
        st.error(f"❌ Erro ao salvar alterações: {e}")
    finally:
        if 'cursor' in locals() and cursor: cursor.close()
        if conexao: conexao.close()

# Gera relatórios consolidados usando queries SQL
def gerar_relatorios_sql(filtro_cliente):
    conexao = conectar_banco()
    if conexao is None:
        return
        
    try:
        setores = ["lavagem", "lavados", "secagem", "pesagem", "dobragem"]
        df_geral = []
        for s in setores:
            query = f"SELECT executante, '{s}' as sector FROM {s}"
            if filtro_cliente:
                query += f" WHERE cliente ILIKE %s"
                df = pd.read_sql_query(query, conexao, params=(f"%{filtro_cliente}%",))
            else:
                df = pd.read_sql_query(query, conexao)
            if not df.empty:
                df_geral.append(df)
                
        st.subheader("1. Quantidade de Operações por Funcionário / Setor")
        if df_geral:
            res = pd.concat(df_geral, ignore_index=True).groupby(["executante", "sector"]).size().unstack(fill_value=0)
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
            res_pecas = df_dob.groupby(["cliente", "executante"]).sum()
            res_pecas["Total de Peças"] = res_pecas.sum(axis=1)
            st.dataframe(res_pecas, use_container_width=True)
        else:
            st.info("Nenhum registro encontrado em Dobragem.")
    except Exception as e:
        st.error(f"Erro nos relatórios: {e}")
    finally:
        if conexao: conexao.close()

# --- FORMULÁRIOS DE LANÇAMENTO ---
def pag_lavagem(dt):
    st.header("Lançamento - Setor de Lavagem")
    with st.form("f_lav", clear_on_submit=True):
        c = st.text_input("Cliente")
        m = st.text_input("Máquina")
        p = st.text_input("Peso (ex: 45kg)")
        i = st.text_input("Horário Início")
        t = st.text_input("Horário Término")
        e = st.text_input("Executante")
        if st.form_submit_button("Gravar Lavagem"):
            if c and e: 
                colunas = ["cliente", "data", "maquina", "peso", "horario_inicio", "horario_termino", "executante"]
                registrar_dados_sql("lavagem", colunas, [c, dt, m, p, i, t, e])
            else: st.warning("Preencha Cliente e Executante.")

def pag_lavados(dt):
    st.header("Lançamento - Setor de Lavados")
    with st.form("f_lvd", clear_on_submit=True):
        c = st.text_input("Cliente")
        m = st.text_input("Máquina")
        p = st.text_input("Peso")
        i = st.text_input("Horário Início")
        t = st.text_input("Horário Término")
        e = st.text_input("Executante")
        if st.form_submit_button("Gravar Lavados"):
            if c and e: 
                colunas = ["cliente", "data", "maquina", "peso", "horario_inicio", "horario_termino", "executante"]
                registrar_dados_sql("lavados", colunas, [c, dt, m, p, i, t, e])
            else: st.warning("Preencha os campos obrigatórios.")

def pag_secagem(dt):
    st.header("Lançamento - Setor de Secagem")
    with st.form("f_sec", clear_on_submit=True):
        m = st.text_input("Máquina")
        c = st.text_input("Cliente")
        ent = st.text_input("Horário Entrada")
        sai = st.text_input("Horário Saída")
        e = st.text_input("Executante")
        if st.form_submit_button("Gravar Secagem"):
            if c and e: 
                colunas = ["maquina", "cliente", "data", "horario_entrada", "horario_saida", "executante"]
                registrar_dados_sql("secagem", colunas, [m, c, dt, ent, sai, e])
            else: st.warning("Preencha os campos obrigatórios.")

def pag_pesagem(dt):
    st.header("Lançamento - Setor de Pesagem")
    with st.form("f_pes", clear_on_submit=True):
        c = st.text_input("Cliente")
        p = st.text_input("Pesagem")
        e = st.text_input("Executante")
        tipo = st.radio("Tipo de Operação", ["Normal", "Relave"])
        if st.form_submit_button("Gravar Pesagem"):
            if c and e: 
                colunas = ["cliente", "data", "pesagem", "executante", "tipo_operacao"]
                registrar_dados_sql("pesagem", colunas, [c, dt, p, e, tipo])
            else: st.warning("Preencha os campos obrigatórios.")

def pag_dobragem(dt):
    st.header("Lançamento - Setor de Dobragem")
    with st.form("f_dob", clear_on_submit=True):
        c = st.text_input("Cliente")
        e = st.text_input("Executante")
        st.markdown("### Contagem de Itens Dobrados")
        qtds = {it: st.number_input(f"Qtd {it}:", min_value=0, step=1, key=f"d_{it}") for it in ITENS_DOBRAGEM}
        if st.form_submit_button("Gravar Dobragem"):
            if c and e:
                colunas_itens = [it.lower().replace("ç", "c").replace("ã", "a") for it in ITENS_DOBRAGEM]
                colunas = ["cliente", "data", "executante"] + colunas_itens
                valores = [c, dt, e] + [int(qtds[it]) for it in ITENS_DOBRAGEM]
                registrar_dados_sql("dobragem", colunas, valores)
            else: st.warning("Preencha Cliente e Executante.")

def pag_analises(dt):
    st.header("📊 Painel Estatístico e Resumos")
    filtro = st.text_input("🔍 Filtrar por Cliente (Vazio para todos)")
    if st.button("Gerar / Atualizar Relatórios"): 
