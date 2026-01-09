import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from database import criar_tabelas, conectar, registrar_venda, registrar_movimento_db, atualizar_produto_db

criar_tabelas()

st.set_page_config(page_title="SmartCommerce - Gestão", layout="wide")
# Inicializa o carrinho na memória da sessão se não existir
if 'carrinho' not in st.session_state:
    st.session_state.carrinho = []

# Funções de integração com o Banco
def listar_produtos():
    conn = conectar()
    df = pd.read_sql_query("SELECT * FROM produtos", conn)
    conn.close()
    return df

def adicionar_produto(nome, qtd, custo, venda):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO produtos (nome, quantidade, preco_custo, preco_venda)
        VALUES (?, ?, ?, ?)
    ''', (nome, qtd, custo, venda))
    conn.commit()
    conn.close()

# Interface do App
st.title("🛍️ SmartCommerce Manager")

tab1, tab2, tab3, = st.tabs(["📊 Dashboard", "💰 Ponto de Venda", "📦 Estoque"])

with tab1:
    st.header("📊 Inteligência de Negócio Avançada")
    
    conn = conectar()
    query = """
    SELECT 
        v.quantidade, 
        v.valor_total as faturamento, 
        p.preco_custo,
        (p.preco_custo * v.quantidade) as custo_total,
        (v.valor_total - (p.preco_custo * v.quantidade)) as lucro,
        v.data_venda,
        p.nome as produto,
        p.marca
    FROM vendas v
    JOIN produtos p ON v.produto_id = p.id
    """
    df_vendas = pd.read_sql_query(query, conn)
    conn.close()

    if df_vendas.empty:
        st.info("Realize vendas para visualizar o dashboard.")
    else:
        # Tratamento de datas
        df_vendas['data_venda'] = pd.to_datetime(df_vendas['data_venda'])
        df_vendas['data_only'] = df_vendas['data_venda'].dt.date

        # --- FILTROS LATERAIS ---
        st.sidebar.subheader("Filtros do Dashboard")
        data_inicio = st.sidebar.date_input("Início", df_vendas['data_only'].min())
        data_fim = st.sidebar.date_input("Fim", df_vendas['data_only'].max())

        # Filtrando o dataframe
        df_filtrado = df_vendas[(df_vendas['data_only'] >= data_inicio) & (df_vendas['data_only'] <= data_fim)]

        # --- KPIs PRINCIPAIS ---
        fat_total = df_filtrado['faturamento'].sum()
        lucro_total = df_filtrado['lucro'].sum()
        margem_total = (lucro_total / fat_total * 100) if fat_total > 0 else 0
        ticket_medio = df_filtrado['faturamento'].mean() if not df_filtrado.empty else 0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Faturamento", f"R$ {fat_total:,.2f}")
        c2.metric("Lucro Líquido", f"R$ {lucro_total:,.2f}")
        c3.metric("Margem", f"{margem_total:.1f}%")
        c4.metric("Ticket Médio", f"R$ {ticket_medio:,.2f}")

        st.write("")

        if not df_vendas.empty:
            # --- 1. GRÁFICO: VENDA DIÁRIA + CURVA ACUMULADA ---
            st.subheader("📈 Evolução e Acúmulo de Vendas")
            
            # Agrupamento por dia
            vendas_dia = df_vendas.groupby(df_vendas['data_venda'].dt.date)['faturamento'].sum().reset_index()
            vendas_dia = vendas_dia.sort_values('data_venda')
            
            # Cálculo da Curva Acumulada
            vendas_dia['faturamento_acumulado'] = vendas_dia['faturamento'].cumsum()
            vendas_dia['data_br'] = pd.to_datetime(vendas_dia['data_venda']).dt.strftime('%d/%m/%Y')

            # Criando o gráfico com dois eixos ou duas linhas
            fig_evolucao = px.line(vendas_dia, x='data_br', y=['faturamento', 'faturamento_acumulado'],
                                markers=True, 
                                title="Vendas Diárias vs. Faturamento Acumulado",
                                labels={'value': 'Valor (R$)', 'data_br': 'Data', 'variable': 'Indicador'})
            
            fig_evolucao.update_xaxes(type='category')
            st.plotly_chart(fig_evolucao, use_container_width=True)

            # --- 2. GRÁFICOS DE PERFORMANCE E ESTOQUE ---
            col_esq, col_dir = st.columns(2)

            with col_esq:
                st.subheader("🏆 Top Produtos (Qtd Vendida)")
                # Ranking de qual produto sai mais em quantidade
                top_qtd = df_vendas.groupby('produto')['quantidade'].sum().sort_values(ascending=True).reset_index()
                fig_top_qtd = px.bar(top_qtd, x='quantidade', y='produto', orientation='h',
                                    title="Produtos Mais Vendidos (Volume)",
                                    color='quantidade', color_continuous_scale='Blues')
                st.plotly_chart(fig_top_qtd, use_container_width=True)

            with col_dir:
                st.subheader("📦 Composição do Estoque")
                # Gráfico de pizza com o que você tem parado no estoque hoje
                df_estoque_atual = listar_produtos() # Função que você já tem no database.py
                fig_pizza_est = px.pie(df_estoque_atual, values='quantidade', names='nome', 
                                    hole=0.4, title="Distribuição de Itens em Estoque")
                st.plotly_chart(fig_pizza_est, use_container_width=True)
                
            st.divider()

            # --- TABELA DE ESTORNO (Onde deu o erro) ---
            st.subheader("🧾 Histórico e Estorno de Vendas")
            
            conn = conectar()
            query_hist = """
                SELECT v.id as venda_id, p.id as produto_id, v.data_venda, 
                    p.nome as Produto, v.quantidade as Qtd, v.valor_total as Total
                FROM vendas v
                JOIN produtos p ON v.produto_id = p.id
                ORDER BY v.data_venda DESC
            """
            df_hist = pd.read_sql_query(query_hist, conn)
            conn.close()

            if not df_hist.empty:
                st.info("Clique em uma linha para selecionar e estornar a venda.")
                
                # CORREÇÃO AQUI: selection_mode="single-row" (com hífen)
                event = st.dataframe(
                    df_hist,
                    use_container_width=True,
                    hide_index=True,
                    on_select="rerun",
                    selection_mode="single-row", 
                    column_config={
                        "venda_id": None, "produto_id": None,
                        "data_venda": st.column_config.DatetimeColumn("Data", format="DD/MM/YYYY HH:mm"),
                        "Total": st.column_config.NumberColumn("Total", format="R$ %.2f")
                    }
                )

                # Lógica do Botão de Estorno
                selecionado = event.selection.rows
                if selecionado:
                    venda_sel = df_hist.iloc[selecionado[0]]
                    st.warning(f"⚠️ Confirmar estorno de {venda_sel['Qtd']}x {venda_sel['Produto']}?")
                    
                    if st.button("Confirmar e Devolver ao Estoque", type="primary"):
                        from database import estornar_venda_db
                        sucesso, msg = estornar_venda_db(
                            int(venda_sel['venda_id']), 
                            int(venda_sel['produto_id']), 
                            int(venda_sel['Qtd'])
                        )
                        if sucesso:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)

with tab2:
    st.header("🛒 Ponto de Venda Profissional")
    
    df_p = listar_produtos()
    
    if df_p.empty:
        st.warning("Cadastre produtos no estoque primeiro.")
    else:
        # --- PARTE 1: SELEÇÃO ---
        col_selecao, col_feedback = st.columns([2, 1])
        with col_selecao:
            prod_nome = st.selectbox("Selecione o Produto", options=df_p['nome'].unique())
            info = df_p[df_p['nome'] == prod_nome].iloc[0]
            
        with col_feedback:
            # Mostra estoque e preço antes de adicionar
            estoque_real = int(info['quantidade'])
            # Se o estoque for negativo por erro, mostramos 0 para não travar a UI
            estoque_exibicao = estoque_real if estoque_real > 0 else 0
            
            st.metric("Disponível", f"{estoque_real} un")
            st.metric("Preço Unit.", f"R$ {info['preco_venda']:,.2f}")

        col_qtd, col_btn = st.columns([2, 1])
        with col_qtd:
            # Aqui está o segredo: o max_value nunca será menor que o min_value (1)
            max_permitido = max(1, estoque_real)
            qtd_item = st.number_input(
                "Quantidade a vender", 
                min_value=1, 
                max_value=max_permitido, 
                step=1,
                disabled=(estoque_real <= 0) # Desabilita se não tiver estoque
            )
            if estoque_real <= 0:
                st.warning("⚠️ Produto sem estoque disponível.")
        
        with col_btn:
            st.write(" ") 
            if st.button("➕ Adicionar ao Carrinho", use_container_width=True):
                item = {
                    "ID": int(info['id']),
                    "Produto": prod_nome,
                    "Qtd": int(qtd_item),
                    "Unitário": float(info['preco_venda']),
                    "Subtotal": float(qtd_item * info['preco_venda'])
                }
                st.session_state.carrinho.append(item)
                st.rerun()

        st.divider()

        # --- PARTE 2: CARRINHO BLINDADO ---
        if st.session_state.carrinho:
            st.subheader("📋 Itens no Pedido")
            
            # Criamos o DataFrame e removemos qualquer linha que tenha ficado vazia/nula
            df_cart_base = pd.DataFrame(st.session_state.carrinho).dropna()
            
            if not df_cart_base.empty:
                # Conversão segura: preenche vazios com 0 antes de converter
                df_cart_base['Qtd'] = df_cart_base['Qtd'].fillna(0).astype(int)
                df_cart_base['Unitário'] = df_cart_base['Unitário'].fillna(0.0).astype(float)

                editado_df = st.data_editor(
                    df_cart_base,
                    use_container_width=True,
                    num_rows="fixed",
                    column_config={
                        "ID": st.column_config.NumberColumn("ID", disabled=True),
                        "Produto": st.column_config.TextColumn("Produto", disabled=True),
                        "Unitário": st.column_config.NumberColumn("Preço Unit.", format="R$ %.2f", disabled=True),
                        "Qtd": st.column_config.NumberColumn("Qtd", min_value=1, step=1, disabled=False),
                        "Subtotal": st.column_config.NumberColumn("Subtotal", format="R$ %.2f", disabled=True),
                    },
                    hide_index=True
                )

                # Recálculo automático
                editado_df["Subtotal"] = editado_df["Qtd"] * editado_df["Unitário"]
                
                # Sincroniza com a sessão apenas se houver mudança real
                if not editado_df.equals(df_cart_base):
                    st.session_state.carrinho = editado_df.to_dict('records')
                    st.rerun()

                total_venda = editado_df['Subtotal'].sum()
                st.markdown(f"### Total do Pedido: R$ {total_venda:,.2f}")
                
                c_vaz, c_limpar, c_vender = st.columns([1, 1, 1])
                if c_limpar.button("🗑️ Esvaziar Tudo", use_container_width=True):
                    st.session_state.carrinho = []
                    st.rerun()

                if c_vender.button("✅ Fechar Venda", type="primary", use_container_width=True):
                    from database import registrar_venda
                    
                    erros = []
                    # Usamos o editado_df que é o DataFrame atualizado do carrinho
                    for _, linha in editado_df.iterrows():
                        # Verifique se os nomes das chaves ['ID'], ['Qtd'] e ['Subtotal'] 
                        # são EXATAMENTE iguais aos que você definiu ao adicionar no carrinho
                        sucesso, msg = registrar_venda(
                            int(linha['ID']), 
                            int(linha['Qtd']), 
                            float(linha['Subtotal']) # O 3º argumento que estava faltando
                        )
                        if not sucesso:
                            erros.append(msg)
                    
                    if erros:
                        for erro in erros:
                            st.error(erro)
                    else:
                        st.session_state.carrinho = []
                        st.success("Venda processada com sucesso!")
                        st.rerun()


with tab3:
    st.header("📦 Gestão de Inventário")
    
    # --- FORMULÁRIO DE NOVO PRODUTO ---
    with st.expander("➕ Cadastrar Novo Produto"):
        with st.form("novo_produto", clear_on_submit=True):
            nome_n = st.text_input("Nome do Produto")
            marca_n = st.text_input("Marca")
            c1, c2, c3 = st.columns(3)
            qtd_n = c1.number_input("Qtd Inicial", min_value=0, step=1)
            custo_n = c2.number_input("Custo", min_value=0.0, format="%.2f")
            venda_n = c3.number_input("Venda", min_value=0.0, format="%.2f")
            
            if st.form_submit_button("Salvar Novo Produto"):
                if nome_n:
                    conn = conectar()
                    cursor = conn.cursor()
                    # 1. Insere o produto
                    cursor.execute("INSERT INTO produtos (nome, marca, quantidade, preco_custo, preco_venda) VALUES (?,?,?,?,?)",
                                (nome_n, marca_n, qtd_n, custo_n, venda_n))
                    novo_id = cursor.lastrowid # Pega o ID gerado automaticamente
                    conn.commit()
                    conn.close()
                    
                    # 2. Registra a quantidade inicial como uma 'COMPRA' no histórico
                    if qtd_n > 0:
                        registrar_movimento_db(novo_id, 'COMPRA', qtd_n, custo_n)
                        
                    st.success(f"Produto {nome_n} cadastrado e entrada de estoque registrada!")
                    st.rerun()

    st.divider()

    # --- TABELA DE EDIÇÃO EM MASSA ---
    st.subheader("📝 Editar Produtos Existentes")
    st.info("Altere os valores diretamente na tabela e clique em 'Salvar Alterações'.")
    
    df_estoque_atual = listar_produtos()
    
    # Configurando o editor de estoque
    estoque_editado = st.data_editor(
        df_estoque_atual,
        use_container_width=True,
        column_config={
            "id": st.column_config.NumberColumn("ID", disabled=True),
            "quantidade": st.column_config.NumberColumn("Estoque", step=1),
            "preco_custo": st.column_config.NumberColumn("Custo", format="R$ %.2f"),
            "preco_venda": st.column_config.NumberColumn("Venda", format="R$ %.2f"),
        },
        hide_index=True,
        key="editor_estoque"
    )

    if st.button("💾 Salvar Alterações no Estoque"):
        from database import atualizar_produto_db, registrar_movimento_db
        
        for index, row in estoque_editado.iterrows():
            # 1. Busca os dados que estão no banco AGORA (antes de atualizar)
            # É importante filtrar pelo ID correto em cada linha do loop
            dados_atuais = df_estoque_atual[df_estoque_atual['id'] == row['id']].iloc[0]
            qtd_anterior = int(dados_atuais['quantidade'])
            custo_atual = float(dados_atuais['preco_custo'])
            
            # 2. Verifica se houve aumento de estoque
            qtd_nova = int(row['quantidade'])
            
            if qtd_nova > qtd_anterior:
                diferenca = qtd_nova - qtd_anterior
                valor_compra = diferenca * custo_atual
                
                # Registra na tabela de movimentações
                # IMPORTANTE: Passamos a diferença e o custo unitário
                registrar_movimento_db(row['id'], 'COMPRA', diferenca, custo_atual)
                st.toast(f"Entrada: +{diferenca} un. de {row['nome']} (R$ {valor_compra:,.2f})", icon="📦")

            # 3. Atualiza o cadastro no banco (independente de ser compra ou apenas mudança de preço)
            atualizar_produto_db(
                row['id'], row['nome'], row.get('marca', ''), 
                row['quantidade'], row['preco_custo'], row['preco_venda']
            )
        
        st.success("Estoque e histórico de movimentações atualizados!")
        st.rerun()