import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from pathlib import Path
from database import (
    criar_tabelas, conectar, registrar_venda, registrar_movimento_db, 
    atualizar_produto_db, estornar_venda_db
)

criar_tabelas()

# ============================================
# CONFIGURAÇÃO DA PÁGINA E CSS
# ============================================

st.set_page_config(
    page_title="SmartCommerce - Gestão Inteligente",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)

def carregar_css():
    """Carrega o arquivo CSS customizado"""
    css_file = Path(__file__).parent / "style.css"
    if css_file.exists():
        with open(css_file, encoding='utf-8') as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    else:
        st.warning("⚠️ Arquivo style.css não encontrado!")

carregar_css()

# ============================================
# FUNÇÕES HELPER VISUAIS
# ============================================

def criar_header(titulo, descricao=None):
    """Cria header estilizado"""
    if descricao:
        st.markdown(f"""
        <div class="custom-header">
            <h1>{titulo}</h1>
            <p>{descricao}</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="custom-header">
            <h1>{titulo}</h1>
        </div>
        """, unsafe_allow_html=True)

def card_metrica(label, value, icon="📊", tipo="primary", change=None):
    """Cria card de métrica estilizado"""
    change_html = ""
    if change:
        change_class = "positive" if "+" in change else "negative"
        change_html = f'<div class="metric-change {change_class}">{change}</div>'
    
    st.markdown(f"""
    <div class="metric-card {tipo}">
        <div class="metric-label">{icon} {label}</div>
        <div class="metric-value">{value}</div>
        {change_html}
    </div>
    """, unsafe_allow_html=True)

def alerta_estoque(produto, quantidade_atual, tipo="warning"):
    """Cria alerta de estoque"""
    icon = "⚠️" if tipo == "warning" else "🔴"
    st.markdown(f"""
    <div class="alert-low-stock">
        <div class="alert-icon">{icon}</div>
        <div class="alert-content">
            <strong>Atenção:</strong> {produto}<br>
            <small>Estoque atual: {quantidade_atual} unidades</small>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ============================================
# INICIALIZAÇÃO DO CARRINHO
# ============================================

if 'carrinho' not in st.session_state:
    st.session_state.carrinho = []

# ============================================
# FUNÇÕES DE BANCO DE DADOS
# ============================================

def listar_produtos():
    conn = conectar()
    df = pd.read_sql_query("SELECT * FROM produtos", conn)
    conn.close()
    return df

# ============================================
# SIDEBAR
# ============================================

with st.sidebar:
    # Logo/Título
    st.markdown("""
    <div style="text-align: center; padding: 1rem 0 2rem 0;">
        <h1 style="color: white; margin: 0; font-size: 1.75rem;">
            🛒 SmartCommerce
        </h1>
        <p style="color: rgba(255,255,255,0.8); font-size: 0.75rem; 
                  margin: 0.5rem 0 0 0; text-transform: uppercase; 
                  letter-spacing: 0.1em;">
            Gestão Inteligente
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Info do usuário/empresa
    st.markdown("""
    <div style="background: rgba(255,255,255,0.1); padding: 1rem; 
                border-radius: 0.75rem; margin-top: 2rem;">
        <p style="margin: 0; font-size: 0.875rem; color: rgba(255,255,255,0.8);">
            Logado como
        </p>
        <p style="margin: 0.25rem 0 0 0; font-weight: 600; color: white;">
            Empresa Demo
        </p>
    </div>
    """, unsafe_allow_html=True)

# ============================================
# ABAS PRINCIPAIS
# ============================================

tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "💰 Ponto de Venda", "📦 Estoque"])

# ============================================
# TAB 1: DASHBOARD
# ============================================

with tab1:
    criar_header("Dashboard", "Inteligência de negócio em tempo real")
    
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
        st.info("💡 Realize vendas para visualizar o dashboard com dados reais.")
        
        # Mostra cards zerados para visual
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            card_metrica("Faturamento Total", "R$ 0,00", "💰", "success")
        with col2:
            card_metrica("Lucro Líquido", "R$ 0,00", "📈", "success")
        with col3:
            card_metrica("Margem de Lucro", "0%", "📊", "primary")
        with col4:
            card_metrica("Ticket Médio", "R$ 0,00", "🛒", "primary")
    else:
        # Tratamento de datas
        df_vendas['data_venda'] = pd.to_datetime(df_vendas['data_venda'])
        df_vendas['data_only'] = df_vendas['data_venda'].dt.date

        # --- FILTROS NO SIDEBAR ---
        st.sidebar.markdown("---")
        st.sidebar.subheader("Filtros do Dashboard")
        data_inicio = st.sidebar.date_input("Data Início", df_vendas['data_only'].min())
        data_fim = st.sidebar.date_input("Data Fim", df_vendas['data_only'].max())

        # Filtrando o dataframe
        df_filtrado = df_vendas[
            (df_vendas['data_only'] >= data_inicio) & 
            (df_vendas['data_only'] <= data_fim)
        ]

        # --- KPIs PRINCIPAIS COM CARDS ESTILIZADOS ---
        fat_total = df_filtrado['faturamento'].sum()
        lucro_total = df_filtrado['lucro'].sum()
        margem_total = (lucro_total / fat_total * 100) if fat_total > 0 else 0
        ticket_medio = df_filtrado['faturamento'].mean() if not df_filtrado.empty else 0

        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            card_metrica(
                label="Faturamento Total",
                value=f"R$ {fat_total:,.2f}",
                icon="💰",
                tipo="success"
            )
        
        with col2:
            card_metrica(
                label="Lucro Líquido",
                value=f"R$ {lucro_total:,.2f}",
                icon="📈",
                tipo="success"
            )
        
        with col3:
            card_metrica(
                label="Margem de Lucro",
                value=f"{margem_total:.1f}%",
                icon="📊",
                tipo="primary"
            )
        
        with col4:
            card_metrica(
                label="Ticket Médio",
                value=f"R$ {ticket_medio:,.2f}",
                icon="🛒",
                tipo="primary"
            )

        st.markdown("<br>", unsafe_allow_html=True)

        # --- GRÁFICO: EVOLUÇÃO E ACÚMULO ---
        st.subheader("📈 Evolução e Acúmulo de Vendas")
        
        vendas_dia = df_vendas.groupby(
            df_vendas['data_venda'].dt.date
        )['faturamento'].sum().reset_index()
        vendas_dia = vendas_dia.sort_values('data_venda')
        vendas_dia['faturamento_acumulado'] = vendas_dia['faturamento'].cumsum()
        vendas_dia['data_br'] = pd.to_datetime(vendas_dia['data_venda']).dt.strftime('%d/%m/%Y')

        fig_evolucao = px.line(
            vendas_dia, 
            x='data_br', 
            y=['faturamento', 'faturamento_acumulado'],
            markers=True, 
            title="Vendas Diárias vs. Faturamento Acumulado",
            labels={'value': 'Valor (R$)', 'data_br': 'Data', 'variable': 'Indicador'}
        )
        fig_evolucao.update_traces(
            line_width=3,
            line=dict(color='#3B82F6'),
            selector=dict(name='faturamento')
        )
        fig_evolucao.update_traces(
            line=dict(color='#10B981'),
            selector=dict(name='faturamento_acumulado')
        )
        fig_evolucao.update_xaxes(type='category')
        fig_evolucao.update_layout(
            template='plotly_white',
            hovermode='x unified',
            plot_bgcolor='white',
            paper_bgcolor='white',
            font=dict(color='#374151')
        )
        st.plotly_chart(fig_evolucao, use_container_width=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # --- GRÁFICOS DE PERFORMANCE E ESTOQUE ---
        col_esq, col_dir = st.columns(2)

        with col_esq:
            st.subheader("🏆 Top Produtos (Qtd Vendida)")
            top_qtd = df_vendas.groupby('produto')['quantidade'].sum().sort_values(
                ascending=True
            ).reset_index()
            fig_top_qtd = px.bar(
                top_qtd, 
                x='quantidade', 
                y='produto', 
                orientation='h',
                title="Produtos Mais Vendidos (Volume)"
            )
            fig_top_qtd.update_traces(marker_color='#10B981')
            fig_top_qtd.update_layout(
                template='plotly_white',
                plot_bgcolor='white',
                paper_bgcolor='white',
                font=dict(color='#374151')
            )
            st.plotly_chart(fig_top_qtd, use_container_width=True)

        with col_dir:
            st.subheader("📦 Composição do Estoque")
            df_estoque_atual = listar_produtos()
            
            if not df_estoque_atual.empty:
                fig_pizza_est = px.pie(
                    df_estoque_atual, 
                    values='quantidade', 
                    names='nome', 
                    hole=0.4, 
                    title="Distribuição de Itens em Estoque"
                )
                fig_pizza_est.update_layout(
                    template='plotly_white',
                    plot_bgcolor='white',
                    paper_bgcolor='white',
                    font=dict(color='#374151')
                )
                st.plotly_chart(fig_pizza_est, use_container_width=True)
            else:
                st.info("Cadastre produtos no estoque primeiro.")
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.divider()

        # --- HISTÓRICO E ESTORNO DE VENDAS ---
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
            st.info("💡 Clique em uma linha para selecionar e estornar a venda.")
            
            event = st.dataframe(
                df_hist,
                use_container_width=True,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row", 
                column_config={
                    "venda_id": None, 
                    "produto_id": None,
                    "data_venda": st.column_config.DatetimeColumn(
                        "Data", 
                        format="DD/MM/YYYY HH:mm"
                    ),
                    "Total": st.column_config.NumberColumn(
                        "Total", 
                        format="R$ %.2f"
                    )
                }
            )

            selecionado = event.selection.rows
            if selecionado:
                venda_sel = df_hist.iloc[selecionado[0]]
                st.warning(
                    f"⚠️ Confirmar estorno de {venda_sel['Qtd']}x {venda_sel['Produto']}?"
                )
                
                if st.button("Confirmar e Devolver ao Estoque", type="primary"):
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
        else:
            st.info("Nenhuma venda registrada ainda.")

# ============================================
# TAB 2: PONTO DE VENDA
# ============================================

with tab2:
    criar_header("Ponto de Venda", "Realize vendas de forma rápida e profissional")
    
    df_p = listar_produtos()
    
    if df_p.empty:
        st.warning("⚠️ Cadastre produtos no estoque primeiro.")
    else:
        # --- PARTE 1: SELEÇÃO DE PRODUTO ---
        col_selecao, col_feedback = st.columns([2, 1])
        
        with col_selecao:
            prod_nome = st.selectbox(
                "🔍 Selecione o Produto", 
                options=df_p['nome'].unique()
            )
            info = df_p[df_p['nome'] == prod_nome].iloc[0]
            
        with col_feedback:
            estoque_real = int(info['quantidade'])
            estoque_exibicao = estoque_real if estoque_real > 0 else 0
            
            # Cards de feedback visual
            st.markdown(f"""
            <div class="metric-card primary">
                <div class="metric-label">📦 Disponível</div>
                <div class="metric-value">{estoque_real}</div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class="metric-card success">
                <div class="metric-label">💵 Preço Unit.</div>
                <div class="metric-value">R$ {info['preco_venda']:,.2f}</div>
            </div>
            """, unsafe_allow_html=True)

        col_qtd, col_btn = st.columns([2, 1])
        
        with col_qtd:
            max_permitido = max(1, estoque_real)
            qtd_item = st.number_input(
                "Quantidade a vender", 
                min_value=1, 
                max_value=max_permitido, 
                step=1,
                disabled=(estoque_real <= 0)
            )
            if estoque_real <= 0:
                alerta_estoque(prod_nome, estoque_real)
        
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

        # --- PARTE 2: CARRINHO ---
        if st.session_state.carrinho:
            st.subheader("🛒 Itens no Pedido")
            
            df_cart_base = pd.DataFrame(st.session_state.carrinho).dropna()
            
            if not df_cart_base.empty:
                df_cart_base['Qtd'] = df_cart_base['Qtd'].fillna(0).astype(int)
                df_cart_base['Unitário'] = df_cart_base['Unitário'].fillna(0.0).astype(float)

                editado_df = st.data_editor(
                    df_cart_base,
                    use_container_width=True,
                    num_rows="fixed",
                    column_config={
                        "ID": st.column_config.NumberColumn("ID", disabled=True),
                        "Produto": st.column_config.TextColumn("Produto", disabled=True),
                        "Unitário": st.column_config.NumberColumn(
                            "Preço Unit.", 
                            format="R$ %.2f", 
                            disabled=True
                        ),
                        "Qtd": st.column_config.NumberColumn(
                            "Qtd", 
                            min_value=1, 
                            step=1, 
                            disabled=False
                        ),
                        "Subtotal": st.column_config.NumberColumn(
                            "Subtotal", 
                            format="R$ %.2f", 
                            disabled=True
                        ),
                    },
                    hide_index=True
                )

                # Recálculo automático
                editado_df["Subtotal"] = editado_df["Qtd"] * editado_df["Unitário"]
                
                if not editado_df.equals(df_cart_base):
                    st.session_state.carrinho = editado_df.to_dict('records')
                    st.rerun()

                total_venda = editado_df['Subtotal'].sum()
                
                # Total destacado
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #10B981 0%, #059669 100%);
                            color: white; padding: 1.5rem; border-radius: 1rem;
                            text-align: center; margin: 1rem 0;">
                    <p style="margin: 0; font-size: 0.875rem; opacity: 0.9;">
                        TOTAL DO PEDIDO
                    </p>
                    <h2 style="margin: 0.5rem 0 0 0; font-size: 2.5rem; font-weight: 800;">
                        R$ {total_venda:,.2f}
                    </h2>
                </div>
                """, unsafe_allow_html=True)
                
                c_vaz, c_limpar, c_vender = st.columns([1, 1, 1])
                
                if c_limpar.button("🗑️ Esvaziar Carrinho", use_container_width=True):
                    st.session_state.carrinho = []
                    st.rerun()

                if c_vender.button(
                    "✅ Fechar Venda", 
                    type="primary", 
                    use_container_width=True
                ):
                    erros = []
                    for _, linha in editado_df.iterrows():
                        sucesso, msg = registrar_venda(
                            int(linha['ID']), 
                            int(linha['Qtd']), 
                            float(linha['Subtotal'])
                        )
                        if not sucesso:
                            erros.append(msg)
                    
                    if erros:
                        for erro in erros:
                            st.error(erro)
                    else:
                        st.session_state.carrinho = []
                        st.success("✅ Venda processada com sucesso!")
                        st.balloons()
                        st.rerun()
        else:
            st.info("🛒 Carrinho vazio. Adicione produtos para iniciar uma venda.")

# ============================================
# TAB 3: ESTOQUE
# ============================================

with tab3:
    criar_header("Gestão de Inventário", "Controle completo dos seus produtos")
    
    # --- FORMULÁRIO DE NOVO PRODUTO ---
    with st.expander("➕ Cadastrar Novo Produto", expanded=False):
        with st.form("novo_produto", clear_on_submit=True):
            nome_n = st.text_input("Nome do Produto *")
            marca_n = st.text_input("Marca")
            
            c1, c2, c3 = st.columns(3)
            qtd_n = c1.number_input("Qtd Inicial", min_value=0, step=1)
            custo_n = c2.number_input("Custo (R$)", min_value=0.0, format="%.2f")
            venda_n = c3.number_input("Venda (R$)", min_value=0.0, format="%.2f")
            
            if st.form_submit_button("💾 Salvar Novo Produto", use_container_width=True):
                if nome_n:
                    conn = conectar()
                    cursor = conn.cursor()
                    cursor.execute(
                        """INSERT INTO produtos 
                           (nome, marca, quantidade, preco_custo, preco_venda) 
                           VALUES (?,?,?,?,?)""",
                        (nome_n, marca_n, qtd_n, custo_n, venda_n)
                    )
                    novo_id = cursor.lastrowid
                    conn.commit()
                    conn.close()
                    
                    if qtd_n > 0:
                        registrar_movimento_db(novo_id, 'COMPRA', qtd_n, custo_n)
                        
                    st.success(f"✅ Produto '{nome_n}' cadastrado com sucesso!")
                    st.rerun()
                else:
                    st.error("❌ Nome do produto é obrigatório!")

    st.divider()

    # --- TABELA DE EDIÇÃO ---
    st.subheader("📝 Produtos Cadastrados")
    st.info("💡 Edite os valores diretamente na tabela e clique em 'Salvar Alterações'.")
    
    df_estoque_atual = listar_produtos()
    
    if not df_estoque_atual.empty:
        estoque_editado = st.data_editor(
            df_estoque_atual,
            use_container_width=True,
            column_config={
                "id": st.column_config.NumberColumn("ID", disabled=True),
                "nome": st.column_config.TextColumn("Produto"),
                "marca": st.column_config.TextColumn("Marca"),
                "quantidade": st.column_config.NumberColumn("Estoque", step=1),
                "preco_custo": st.column_config.NumberColumn(
                    "Custo", 
                    format="R$ %.2f"
                ),
                "preco_venda": st.column_config.NumberColumn(
                    "Venda", 
                    format="R$ %.2f"
                ),
            },
            hide_index=True,
            key="editor_estoque"
        )

        if st.button("💾 Salvar Alterações", type="primary", use_container_width=True):
            alteracoes = 0
            entradas = 0
            
            for index, row in estoque_editado.iterrows():
                dados_atuais = df_estoque_atual[
                    df_estoque_atual['id'] == row['id']
                ].iloc[0]
                qtd_anterior = int(dados_atuais['quantidade'])
                custo_atual = float(dados_atuais['preco_custo'])
                qtd_nova = int(row['quantidade'])
                
                if qtd_nova > qtd_anterior:
                    diferenca = qtd_nova - qtd_anterior
                    valor_compra = diferenca * custo_atual
                    registrar_movimento_db(row['id'], 'COMPRA', diferenca, custo_atual)
                    entradas += diferenca
                    st.toast(
                        f"📦 Entrada: +{diferenca} un. de {row['nome']}", 
                        icon="✅"
                    )
                
                atualizar_produto_db(
                    row['id'], row['nome'], row.get('marca', ''), 
                    row['quantidade'], row['preco_custo'], row['preco_venda']
                )
                alteracoes += 1
            
            st.success(
                f"✅ {alteracoes} produto(s) atualizado(s)! " + 
                (f"{entradas} entrada(s) registrada(s)." if entradas > 0 else "")
            )
            st.rerun()
    else:
        st.info("📦 Nenhum produto cadastrado ainda. Use o formulário acima para começar.")

# ============================================
# RODAPÉ
# ============================================

st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("""
<div style="text-align: center; padding: 2rem 0; color: #6B7280; 
            font-size: 0.875rem; border-top: 1px solid #E5E7EB; margin-top: 2rem;">
    <p style="margin: 0;">
        SmartCommerce v1.0 | Gestão Inteligente para Pequenos Negócios
    </p>
    <p style="margin: 0.5rem 0 0 0; font-size: 0.75rem;">
        Feito com ❤️ para empreendedores que querem crescer
    </p>
</div>
""", unsafe_allow_html=True)