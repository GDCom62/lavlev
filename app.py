import streamlit as st
import pandas as pd
import datetime
import psycopg2

ITENS_DOBRAGEM = ["Lençol", "Fronha", "Capote", "Camisola", "Oleado", "Calça", "Camisa", "Cobertor", "Colcha", "Toalha", "Traçado"]

# --- LEITURA AUTOMÁTICA DO SEGREDO ---
try:
    DB_URI = st.secrets["banco_dados"]["uri"]
except Exception:
    DB_URI = None

# --- CONEXÃO COM O BANCO DE DADOS ---
def conectar_banco():
    if not DB_URI:
        st.error("⚠️ Configuração de banco de dados não encontrada nos Secrets do Streamlit!")
        st.stop()
    return psycopg2.connect(DB_URI)

# Gravação Genérica no Banco SQL
def registrar_dados_sql(tabela, colunas, dados):
    try:
        conexao = conectar_banco()
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

# Deletar um registro específico por ID
def deletar_registro_sql(tabela, registro_id):
    try:
        conexao = conectar_banco()
        cursor = conexao.cursor()
        
        query = f"DELETE FROM {tabela} WHERE id = %s"
        cursor.execute(query, (registro_id,))
        conexao.commit()
        
        if cursor.rowcount > 0:
            st.success(f"🗑️ Registro ID {registro_id} deletado com sucesso de {tabela.capitalize()}!")
            st.rerun()
        else:
            st.warning(f"⚠️ Nenhum registro encontrado com o ID {registro_id}.")
    except Exception as e:
        st.error(f"❌ Erro ao deletar: {e}")
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conexao' in locals(): conexao.close()

# Atualizar o cliente e o executante de um registro por ID
def editar_registro_sql(tabela, registro_id, novo_cliente, novo_executante):
    try:
        conexao = conectar_banco()
        cursor = conexao.cursor()
        
        query = f"UPDATE {tabela} SET cliente = %s, executante = %s WHERE id = %s"
        cursor.execute(query, (novo_cliente, novo_executante, registro_id))
        conexao.commit()
        
        if cursor.rowcount > 0:
            st.success(f"✏️ Registro ID {registro_id} atualizado com sucesso!")
            st.rerun()
        else:
            st.warning(f"⚠️ Nenhum registro encontrado com o ID {registro_id}.")
    except Exception as e:
        st.error(f"❌ Erro ao atualizar: {e}")
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conexao' in locals(): conexao.close()

# Gera relatórios consolidados usando queries SQL
def gerar_relatorios_sql(filtro_cliente):
    try:
        conexao = conectar_banco()
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
def pag_lavagem(dt):
    st.header("Lançamento - Setor de Lavagem")
    with st.form("f_lav", clear_on_submit=True):
        c, m, p = st.text_input("Cliente"), st.text_input("Máquina"), st.text_input("Peso (ex: 45kg)")
        i, t, e = st.text_input("Horário Início"), st.text_input("Horário Término"), st.text_input("Executante")
        if st.form_submit_button("Gravar Lavagem"):
            if c and e: 
                colunas = ["cliente", "data", "maquina", "peso", "horario_inicio", "horario_termino", "executante"]
                registrar_dados_sql("lavagem", colunas, [c, dt, m, p, i, t, e])
            else: st.warning("Preencha Cliente e Executante.")

def pag_lavados(dt):
    st.header("Lançamento - Setor de Lavados")
    with st.form("f_lvd", clear_on_submit=True):
        c, m, p = st.text_input("Cliente"), st.text_input("Máquina"), st.text_input("Peso")
        i, t, e = st.text_input("Horário Início"), st.text_input("Horário Término"), st.text_input("Executante")
        if st.form_submit_button("Gravar Lavados"):
            if c and e: 
                colunas = ["cliente", "data", "maquina", "peso", "horario_inicio", "horario_termino", "executante"]
                registrar_dados_sql("lavados", colunas, [c, dt, m, p, i, t, e])
            else: st.warning("Preencha os campos obrigatórios.")

def pag_secagem(dt):
    st.header("Lançamento - Setor de Secagem")
    with st.form("f_sec", clear_on_submit=True):
        m, c, ent, sai, e = st.text_input("Máquina"), st.text_input("Cliente"), st.text_input("Horário Entrada"), st.text_input("Horário Saída"), st.text_input("Executante")
        if st.form_submit_button("Gravar Secagem"):
            if c and e: 
                colunas = ["maquina", "cliente", "data", "horario_entrada", "horario_saida", "executante"]
                registrar_dados_sql("secagem", colunas, [m, c, dt, ent, sai, e])
            else: st.warning("Preencha os campos obrigatórios.")

def pag_pesagem(dt):
    st.header("Lançamento - Setor de Pesagem")
    with st.form("f_pes", clear_on_submit=True):
        c, p, e = st.text_input("Cliente"), st.text_input("Pesagem"), st.text_input("Executante")
        tipo = st.radio("Tipo de Operação", ["Normal", "Relave"])
        if st.form_submit_button("Gravar Pesagem"):
            if c and e: 
                colunas = ["cliente", "data", "pesagem", "executante", "tipo_operacao"]
                registrar_dados_sql("pesagem", colunas, [c, dt, p, e, tipo])
            else: st.warning("Preencha os campos obrigatórios.")

def pag_dobragem(dt):
    st.header("Lançamento - Setor de Dobragem")
    with st.form("f_dob", clear_on_submit=True):
        c, e = st.text_input("Cliente"), st.text_input("Executante")
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
        gerar_relatorios_sql(filtro)

def pag_correcoes(dt):
    st.header("🛠️ Histórico e Correções de Lançamentos")
    s = st.selectbox("Selecione o Setor para visualizar:", ["lavagem", "lavados", "secagem", "pesagem", "dobragem"])
    
    try:
        conexao = conectar_banco()
        query = f"SELECT id, cliente, data, executante FROM {s} ORDER BY id DESC LIMIT 15"
        df = pd.read_sql_query(query, conexao)
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        df = pd.DataFrame()
    finally:
        if 'conexao' in locals(): conexao.close()
    
    if df.empty:
        st.info("Nenhum registro encontrado neste setor.")
    else:
        st.markdown("### Últimos 15 Lançamentos")
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.markdown("### ⚙️ Painel de Alterações")
        
        col_id, col_inputs = st.columns(2)
        
        with col_id:
            id_selecionado = st.number_input("Digite o ID do lançamento:", min_value=1, step=1, key="id_corr")
            if st.button("🗑️ Deletar Registro", type="secondary", use_container_width=True):
                deletar_registro_sql(s, id_selecionado)
                
        with col_inputs:
            novo_c = st.text_input("Novo Nome do Cliente (Deixe vazio se for apenas deletar)")
            novo_e = st.text_input("Novo Nome do Executante (Deixe vazio se for apenas deletar)")
            if st.button("✏️ Salvar Alterações", type="primary", use_container_width=True):
                if novo_c and novo_e:
                    editar_registro_sql(s, id_selecionado, novo_c, novo_e)
                else:
                    st.warning("⚠️ Para editar, preencha o Novo Cliente e o Novo Executante.")
