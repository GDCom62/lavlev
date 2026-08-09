import streamlit as st
import pandas as pd
import datetime
import psycopg2

st.set_page_config(page_title="Controle Lavanderia", layout="wide")

ITENS_DOBRAGEM = ["Lençol", "Fronha", "Capote", "Camisola", "Oleado", "Calça", "Camisa", "Cobertor", "Colcha", "Toalha", "Traçado"]

def conectar_banco():
    try:
        if "banco_dados" in st.secrets and "uri" in st.secrets["banco_dados"]:
            return psycopg2.connect(st.secrets["banco_dados"]["uri"])
        st.error("⚠️ Configuração 'uri' ausente nos Secrets!")
        return None
    except Exception as e:
        st.error(f"⚠️ Erro de conexão com o banco de dados: {e}")
        return None

def registrar_dados_sql(tabela, colunas, dados):
    conexao = conectar_banco()
    if conexao is None: return
    try:
        cursor = conexao.cursor()
        placeholders = ", ".join(["%s"] * len(dados))
        colunas_str = ", ".join(colunas)
        query = f"INSERT INTO {tabela} ({colunas_str}) VALUES ({placeholders})"
        cursor.execute(query, dados)
        conexao.commit()
        st.success(f"✅ Gravado com sucesso em {tabela.capitalize()}!")
    except Exception as e:
        st.error(f"❌ Erro ao salvar: {e}")
    finally:
        if conexao: conexao.close()

def puxar_historico_filtrado_sql(tabela, filtro_cliente, filtro_colaborador):
    conexao = conectar_banco()
    if conexao is None: return pd.DataFrame()
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
        return pd.read_sql_query(query, conexao, params=params)
    except Exception as e:
        st.error(f"❌ Erro ao buscar dados na tabela {tabela}: {e}")
        return pd.DataFrame()
    finally:
        if conexao: conexao.close()

def salvar_alteracoes_banco(tabela, df_original, e_editado):
    conexao = conectar_banco()
    if conexao is None: return
    try:
        cursor = conexao.cursor()
        sucesso = False
        if "deleted_rows" in e_editado and e_editado["deleted_rows"]:
            for indice in e_editado["deleted_rows"]:
                id_reg = int(df_original.iloc[indice]["id"])
                cursor.execute(f"DELETE FROM {tabela} WHERE id = %s", (id_reg,))
            sucesso = True
        if "edited_rows" in e_editado and e_editado["edited_rows"]:
            for idx_str, mudancas in e_editado["edited_rows"].items():
                id_reg = int(df_original.iloc[int(idx_str)]["id"])
                for col, valor in mudancas.items():
                    if col == "id": continue
                    cursor.execute(f"UPDATE {tabela} SET {col} = %s WHERE id = %s", (valor, id_reg))
            sucesso = True
        if sucesso:
            conexao.commit()
            st.success("✅ Alterações salvas com sucesso no banco de dados!")
            st.rerun()
    except Exception as e:
        conexao.rollback()
        st.error(f"❌ Erro ao atualizar registros: {e}")
    finally:
        if conexao: conexao.close()

def gerar_relatorios_sql(filtro_cliente):
    conexao = conectar_banco()
    if conexao is None: return
    try:
        setores = ["lavagem", "lavados", "secagem", "pesagem", "dobragem"]
        df_geral = []
        for s in setores:
            query = f"SELECT executante, '{s}' as sector FROM {s}"
            if filtro_cliente:
                df = pd.read_sql_query(query + " WHERE cliente ILIKE %s", conexao, params=(f"%{filtro_cliente}%",))
            else:
                df = pd.read_sql_query(query, conexao)
            if not df.empty: df_geral.append(df)
        st.subheader("1. Quantidade de Operações por Funcionário / Setor")
        if df_geral:
            res = pd.concat(df_geral, ignore_index=True).groupby(["executante", "sector"]).size().unstack(fill_value=0)
            res["Total Geral"] = res.sum(axis=1)
            st.dataframe(res, use_container_width=True)
        else:
            st.info("Nenhum dado encontrado para gerar relatórios operacionais.")
        st.subheader("2. Total de Peças Dobradas por Cliente e Executante")
        cols_sql = ", ".join([it.lower().replace("ç", "c").replace("ã", "a") for it in ITENS_DOBRAGEM])
        if filtro_cliente:
            df_dob = pd.read_sql_query(f"SELECT cliente, executante, {cols_sql} FROM dobragem WHERE cliente ILIKE %s", conexao, params=(f"%{filtro_cliente}%",))
        else:
            df_dob = pd.read_sql_query(f"SELECT cliente, executante, {cols_sql} FROM dobragem", conexao)
        if not df_dob.empty:
            mapeamento = {it.lower().replace("ç", "c").replace("ã", "a"): it for it in ITENS_DOBRAGEM}
            df_dob = df_dob.rename(columns=mapeamento)
            res_pecas = df_dob.groupby(["cliente", "executante"]).sum()
            res_pecas["Total de Peças"] = res_pecas.sum(axis=1)
            st.dataframe(res_pecas, use_container_width=True)
        else:
            st.info("Nenhum registro de dobras encontrado.")
    except Exception as e:
        st.error(f"Erro nos relatórios: {e}")
    finally:
        if conexao: conexao.close()

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
            if c and e: registrar_dados_sql("lavagem", ["cliente", "data", "maquina", "peso", "horario_inicio", "horario_termino", "executante"], [c, dt, m, p, i, t, e])
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
            if c and e: registrar_dados_sql("lavados", ["cliente", "data", "maquina", "peso", "horario_inicio", "horario_termino", "executante"], [c, dt, m, p, i, t, e])
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
            if c and e: registrar_dados_sql("secagem", ["maquina", "cliente", "data", "horario_entrada", "horario_saida", "executante"], [m, c, dt, ent, sai, e])
            else: st.warning("Preencha os campos obrigatórios.")

def pag_pesagem(dt):
    st.header("Lançamento - Setor de Pesagem")
    with st.form("f_pes", clear_on_submit=True):
        c = st.text_input("Cliente")
        p = st.text_input("Pesagem")
        e = st.text_input("Executante")
        tipo = st.radio("Tipo de Operação", ["Normal", "Relave"])
        if st.form_submit_button("Gravar Pesagem"):
            if c and e: registrar_dados_sql("pesagem", ["cliente", "data", "pesagem", "executante", "tipo_operacao"], [c, dt, p, e, tipo])
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
                cols_it = [it.lower().replace("ç", "c").replace("ã", "a") for it in ITENS_DOBRAGEM]
                registrar_dados_sql("dobragem", ["cliente", "data", "executante"] + cols_it, [c, dt, e] + [int(qtds[it]) for it in ITENS_DOBRAGEM])
            else: st.warning("Preencha Cliente e Executante.")

def pag_analises(dt):
    st.header("📊 Painel Estatístico e Resumos")
    filtro = st.text_input("🔍 Filtrar por Cliente (Vazio para todos)")
    gerar_relatorios_sql(filtro)

def pag_correcoes(dt):
    st.header("🛠️ Gerenciamento e Correção de Lançamentos")
    st.markdown("Altere os dados nas células ou apagar linhas usando a tecla Delete.")
    s = st.selectbox("Selecione o Setor para visualização:", ["lavagem", "lavados", "secagem", "pesagem", "dobragem"])
    f_cliente = st.text_input("🔍 Filtrar por Cliente (Opcional):")
    f_colab = st.text_input("👤 Filtrar por Colaborador / Executante (Opcional):")
    
    df_dados = puxar_historico_filtrado_sql(s, f_cliente, f_colab)
    
    if df_dados is not None and not df_dados.empty:
        st.markdown("### 📋 Dados Encontrados no Banco:")
        dados_editados = st.data_editor(df_dados, use_container_width=True, num_rows="dynamic", disabled=["id"], key=f"ed_{s}")
        
        mudancas = st.session_state.get(f"ed_{s}", {})
        houve_mudanca = len(mudancas.get("edited_rows", {})) > 0 or len(mudancas.get("deleted_rows", [])) > 0
        
        if houve_mudanca:
            st.warning("⚠️ Existem alterações não salvas nesta tabela!")
            if st.button("💾 CONFIRMAR E SALVAR ALTERAÇÕES NO BANCO"):
                salvar_alteracoes_banco(s, df_dados, mudancas)
    else:
