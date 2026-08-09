import streamlit as st
import pandas as pd
import datetime
import psycopg2

st.set_page_config(page_title="Controle Lavanderia", layout="wide")

ITENS_DOBRAGEM = ["Lençol", "Fronha", "Capote", "Camisola", "Oleado", "Calça", "Camisa", "Cobertor", "Colcha", "Toalha", "Traçado"]

# --- FUNÇÃO DE CONEXÃO ---
def abrir_conexao_banco():
    try:
        if "banco_dados" in st.secrets and "uri" in st.secrets["banco_dados"]:
            return psycopg2.connect(st.secrets["banco_dados"]["uri"])
        st.error("⚠️ Configuração 'uri' ausente nos Secrets!")
        return None
    except Exception as e:
        st.error(f"⚠️ Erro na conexão do banco: {e}")
        return None

# --- FUNÇÃO ISOLADA PARA SALVAR ALTERAÇÕES DO HISTÓRICO ---
def executar_salvamento_historico(tabela, df_com_checkboxes, mudancas_editor):
    db = abrir_conexao_banco()
    if not db:
        return
    try:
        cursor = db.cursor()
        if "edited_rows" in mudancas_editor:
            for idx_str, campos in mudancas_editor["edited_rows"].items():
                if campos.get("Selecionar para Excluir") is True:
                    id_reg = int(df_com_checkboxes.iloc[int(idx_str)]["id"])
                    cursor.execute(f"DELETE FROM {tabela} WHERE id = %s", (id_reg,))
            for idx_str, campos in mudancas_editor["edited_rows"].items():
                if campos.get("Selecionar para Excluir") is not True:
                    id_reg = int(df_com_checkboxes.iloc[int(idx_str)]["id"])
                    for col, valor in campos.items():
                        if col != "id" and col != "Selecionar para Excluir":
                            cursor.execute(f"UPDATE {tabela} SET {col} = %s WHERE id = %s", (valor, id_reg))
        db.commit()
        st.success("✅ Banco de dados atualizado com sucesso!")
        st.rerun()
    except Exception as err:
        db.rollback()
        st.error(f"❌ Erro ao salvar alterações no banco: {err}")
    finally:
        db.close()

# --- TELAS DE LANÇAMENTO ---
def tela_lavagem(dt):
    st.header("Lançamento - Setor de Lavagem")
    c = st.text_input("Cliente", key="lav_c")
    m = st.text_input("Máquina", key="lav_m")
    p = st.text_input("Peso (ex: 45kg)", key="lav_p")
    i = st.text_input("Horário Início", key="lav_i")
    t = st.text_input("Horário Término", key="lav_t")
    e = st.text_input("Executante", key="lav_e")
    if st.button("Gravar Lavagem"):
        db = abrir_conexao_banco()
        if db:
            try:
                cursor = db.cursor()
                cursor.execute("INSERT INTO lavagem (cliente, data, maquina, peso, horario_inicio, horario_termino, executante) VALUES (%s, %s, %s, %s, %s, %s, %s)", (c, dt, m, p, i, t, e))
                db.commit()
                st.success("✅ Lançamento de Lavagem gravado com sucesso!")
            except Exception as err: st.error(f"❌ Erro ao salvar: {err}")
            finally: db.close()

def tela_lavados(dt):
    st.header("Lançamento - Setor de Lavados")
    c = st.text_input("Cliente", key="lvd_c")
    m = st.text_input("Máquina", key="lvd_m")
    p = st.text_input("Peso", key="lvd_p")
    i = st.text_input("Horário Início", key="lav_i_2")
    t = st.text_input("Horário Término", key="lav_t_2")
    e = st.text_input("Executante", key="lvd_e")
    if st.button("Gravar Lavados"):
        db = abrir_conexao_banco()
        if db:
            try:
                cursor = db.cursor()
                cursor.execute("INSERT INTO lavados (cliente, data, maquina, peso, horario_inicio, horario_termino, executante) VALUES (%s, %s, %s, %s, %s, %s, %s)", (c, dt, m, p, i, t, e))
                db.commit()
                st.success("✅ Lançamento de Lavados gravado!")
            except Exception as err: st.error(f"❌ Erro ao salvar: {err}")
            finally: db.close()

def tela_secagem(dt):
    st.header("Lançamento - Setor de Secagem")
    m = st.text_input("Máquina", key="sec_m")
    c = st.text_input("Cliente", key="sec_c")
    ent = st.text_input("Horário Entrada", key="sec_ent")
    sai = st.text_input("Horário Saída", key="sec_sai")
    e = st.text_input("Executante", key="sec_e")
    if st.button("Gravar Secagem"):
        db = abrir_conexao_banco()
        if db:
            try:
                cursor = db.cursor()
                cursor.execute("INSERT INTO secagem (maquina, cliente, data, horario_entrada, horario_saida, executante) VALUES (%s, %s, %s, %s, %s, %s)", (m, c, dt, ent, sai, e))
                db.commit()
                st.success("✅ Lançamento de Secagem gravado!")
            except Exception as err: st.error(f"❌ Erro ao salvar: {err}")
            finally: db.close()

def tela_pesagem(dt):
    st.header("Lançamento - Setor de Pesagem")
    c = st.text_input("Cliente", key="pes_c")
    p = st.text_input("Pesagem", key="pes_p")
    e = st.text_input("Executante", key="pes_e")
    tipo = st.radio("Tipo de Operação", ["Normal", "Relave"], key="pes_tipo")
    if st.button("Gravar Pesagem"):
        db = abrir_conexao_banco()
        if db:
            try:
                cursor = db.cursor()
                cursor.execute("INSERT INTO pesagem (cliente, data, pesagem, executante, tipo_operacao) VALUES (%s, %s, %s, %s, %s)", (c, dt, p, e, tipo))
                db.commit()
                st.success("✅ Lançamento de Pesagem gravado!")
            except Exception as err: st.error(f"❌ Erro ao salvar: {err}")
            finally: db.close()

def tela_dobragem(dt):
    st.header("Lançamento - Setor de Dobragem")
    c = st.text_input("Cliente", key="dob_c")
    e = st.text_input("Executante", key="dob_e")
    st.markdown("### Contagem de Itens Dobrados")
    qtds = {}
    for it in ITENS_DOBRAGEM:
        qtds[it] = st.number_input(f"Qtd {it}:", min_value=0, step=1, key=f"d_{it}")
    if st.button("Gravar Dobragem"):
        db = abrir_conexao_banco()
        if db:
            try:
                cols_it = [it.lower().replace("ç", "c").replace("ã", "a") for it in ITENS_DOBRAGEM]
                colunas_str = ", ".join(["cliente", "data", "executante"] + cols_it)
                placeholders = ", ".join(["%s"] * (3 + len(ITENS_DOBRAGEM)))
                valores = [c, dt, e] + [int(qtds[it]) for it in ITENS_DOBRAGEM]
                cursor = db.cursor()
                cursor.execute(f"INSERT INTO dobragem ({colunas_str}) VALUES ({placeholders})", valores)
                db.commit()
                st.success("✅ Lançamento de Dobragem gravado!")
            except Exception as err: st.error(f"❌ Erro ao salvar dobragem: {err}")
            finally: db.close()

def tela_analises(dt):
    st.header("📊 Painel Estatístico e Resumos")
    filtro = st.text_input("🔍 Filtrar por Cliente (Vazio para todos)", key="an_filtro")
    db = abrir_conexao_banco()
    if db:
        try:
            setores = ["lavagem", "lavados", "secagem", "pesagem", "dobragem"]
            df_geral = []
            for s in setores:
                query = f"SELECT executante, '{s}' as sector FROM {s}"
                params = []
                if filtro:
                    query += " WHERE cliente ILIKE %s"
                    params.append(f"%{filtro}%")
                df_sec = pd.read_sql_query(query, db, params=params if filtro else None)
                if not df_sec.empty: df_geral.append(df_sec)
            st.subheader("1. Quantidade de Operações por Funcionário / Setor")
            if df_geral:
                res = pd.concat(df_geral, ignore_index=True).groupby(["executante", "sector"]).size().unstack(fill_value=0)
                res["Total Geral"] = res.sum(axis=1)
                st.dataframe(res, use_container_width=True)
            else: st.info("Nenhum dado encontrado para gerar relatórios operacionais.")
            st.subheader("2. Total de Peças Dobradas por Cliente e Executante")
            cols_sql = ", ".join([it.lower().replace("ç", "c").replace("ã", "a") for it in ITENS_DOBRAGEM])
            query_dob = f"SELECT cliente, executante, {cols_sql} FROM dobragem"
            params_dob = []
            if filtro:
                query_dob += " WHERE cliente ILIKE %s"
                params_dob.append(f"%{filtro}%")
            df_dob = pd.read_sql_query(query_dob, db, params=params_dob if filtro else None)
            if not df_dob.empty:
                mapeamento = {it.lower().replace("ç", "c").replace("ã", "a"): it for it in ITENS_DOBRAGEM}
                df_dob = df_dob.rename(columns=mapeamento)
                res_pecas = df_dob.groupby(["cliente", "executante"]).sum()
                res_pecas["Total de Peças"] = res_pecas.sum(axis=1)
                st.dataframe(res_pecas, use_container_width=True)
            else: st.info("Nenhum registro de dobras encontrado.")
        except Exception as err: st.error(f"Erro nos relatórios: {err}")
        finally: db.close()

def tela_historico(dt):
    st.header("🛠️ Gerenciamento e Correção de Lançamentos")
    st.markdown("✏️ **Para Editar:** Clique duas vezes em qualquer campo, mude o valor e aperte Enter.")
    st.markdown("❌ **Para Excluir:** Marque a caixinha **'Selecionar para Excluir'** na linha desejada.")
    s = st.selectbox("Selecione o Setor para visualização:", ["lavagem", "lavados", "secagem", "pesagem", "dobragem"])
    f_cliente = st.text_input("🔍 Filtrar por Cliente (Opcional):", key="hist_fc")
    f_colab = st.text_input("👤 Filtrar por Colaborador / Executante (Opcional):", key="hist_fe")
    db = abrir_conexao_banco()
    if db:
        try:
            query_hist = f"SELECT * FROM {s} WHERE 1=1"
            params_hist = []
            if f_cliente:
                query_hist += " AND cliente ILIKE %s"
                params_hist.append(f"%{f_cliente}%")
            if f_colab:
                query_hist += " AND executante ILIKE %s"
                params_hist.append(f"%{f_colab}%")
            query_hist += " ORDER BY id DESC LIMIT 50"
