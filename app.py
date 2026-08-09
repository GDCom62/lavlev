import streamlit as st
import pandas as pd
import datetime
import psycopg2

ITENS_DOBRAGEM = ["Lençol", "Fronha", "Capote", "Camisola", "Oleado", "Calça", "Camisa", "Cobertor", "Colcha", "Toalha", "Traçado"]

try:
    DB_URI = st.secrets["banco_dados"]["uri"]
except Exception:
    DB_URI = None

def conectar_banco():
    if not DB_URI:
        st.error("⚠️ Configuração de banco de dados não encontrada nos Secrets do Streamlit!")
        st.stop()
    return psycopg2.connect(DB_URI)

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

def puxar_historico_filtrado_sql(tabela, filtro_cliente, filtro_colaborador):
    try:
        conexao = conectar_banco()
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
        if 'conexao' in locals(): conexao.close()

def salvar_alteracoes_banco(tabela, df_original, e_editado):
    conexao = conectar_banco()
    cursor = conexao.cursor()
    sucesso = False
    try:
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
        cursor.close()
        conexao.close()

def gerar_relatorios_sql(filtro_cliente):
    try:
        conexao = conectar_banco()
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
        if 'conexao' in locals(): conexao.close()

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
        gerar_relatorios_sql(filtro)

def pag_correcoes(dt):
    st.header("🛠️ Gerenciamento e Correção de Lançamentos")
    st.markdown("Use esta tela para buscar registros, alterar dados nas células ou apagar linhas.")
    s = st.selectbox("Selecione o Setor:", ["lavagem", "lavados", "secagem", "pesagem", "dobragem"])
    f_cliente = st.text_input("🔍 Filtrar por Cliente:")
    f_colab = st.text_input("👤 Filtrar por Colaborador (Executante):")
    df_dados = puxar_historico_filtrado_sql(s, f_cliente, f_colab)
    if not df_dados.empty:
        st.markdown("""
        ### 📋 Instruções de Comando:
        * ✏️ **Para Editar:** Clique duas vezes em qualquer célula da tabela abaixo, mude o valor e aperte *Enter*.
        * ❌ **Para Excluir:** Clique no quadradinho no início da linha correspondente e aperte a tecla **Delete** do seu teclado.
        """)
        dados_editados = st.data_editor(df_dados, use_container_width=True, num_rows="dynamic", disabled=["id"], key=f"editor_{s}")
        chave_estado = f"editor_{s}"
