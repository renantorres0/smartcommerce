import sqlite3

def conectar():
    return sqlite3.connect('gestao.db')

def criar_tabelas():
    conn = conectar()
    cursor = conn.cursor()

    # Tabela de Produtos (Estoque)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            marca TEXT,
            quantidade INTEGER NOT NULL,
            preco_custo REAL NOT NULL,
            preco_venda REAL NOT NULL
        )
    ''')

    # Tabela de Vendas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vendas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produto_id INTEGER NOT NULL,
            quantidade INTEGER NOT NULL,
            valor_total REAL NOT NULL,
            data_venda DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (produto_id) REFERENCES produtos(id)
        )
    ''')
    
    try:
        cursor.execute("ALTER TABLE produtos ADD COLUMN marca TEXT")
    except sqlite3.OperationalError:
        pass  # Coluna já existe
    
    # Tabela de Movimentações
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS movimentacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produto_id INTEGER,
            tipo TEXT, -- 'COMPRA' ou 'VENDA'
            quantidade INTEGER,
            preco_custo_na_epoca REAL,
            data_movimento DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (produto_id) REFERENCES produtos (id)
        )
    ''')

    conn.commit()
    conn.close()

if __name__ == '__main__':
    criar_tabelas()
    print("Banco de dados e tabelas criadas com sucesso.")

def registrar_venda(produto_id, qtd_venda, valor_total): 
    conn = conectar()
    cursor = conn.cursor()
    
    # Busca estoque atual
    cursor.execute("SELECT quantidade FROM produtos WHERE id = ?", (produto_id,))
    estoque_atual = cursor.fetchone()[0]
    
    if estoque_atual >= qtd_venda:
        # Registra a venda com o valor total
        cursor.execute("""
            INSERT INTO vendas (produto_id, quantidade, valor_total) 
            VALUES (?, ?, ?)
        """, (produto_id, qtd_venda, valor_total))
        
        # Baixa no estoque
        cursor.execute("UPDATE produtos SET quantidade = quantidade - ? WHERE id = ?", 
                       (qtd_venda, produto_id))
        
        conn.commit()
        conn.close()
        return True, "Venda realizada!"
    
    conn.close()
    return False, "Estoque insuficiente!"

def  atualizar_coluna_marca():
    conn = conectar()
    cursor = conn.cursor()
    
    # Atualiza a coluna 'marca' com um valor padrão se estiver vazia
    cursor.execute("UPDATE produtos SET marca = 'Marca Padrão' WHERE marca IS NULL OR marca = ''")
    
    conn.commit()
    conn.close()
    
def atualizar_produto_db(id_prod, nome, marca, qtd, custo, venda):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE produtos
        SET nome = ?, marca = ?, quantidade = ?, preco_custo = ?, preco_venda = ?
        WHERE id = ?
    ''', (nome, marca, qtd, custo, venda, id_prod))
    conn.commit()
    conn.close()
    
def criar_tabela_movimentacao():
    conn = conectar()
    cursor = conn.cursor()
    # Registra entradas (compras/ajustes) e saídas (vendas)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS movimentacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produto_id INTEGER,
            tipo TEXT, -- 'COMPRA' ou 'VENDA'
            quantidade INTEGER,
            preco_custo_na_epoca REAL,
            data_movimento DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (produto_id) REFERENCES produtos (id)
        )
    ''')
    conn.commit()
    conn.close()
    
def registrar_movimento_db(produto_id, tipo, quantidade, preco_custo):
    """
    Registra uma entrada (COMPRA) ou saída no histórico de movimentações.
    """
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO movimentacoes (produto_id, tipo, quantidade, preco_custo_na_epoca)
        VALUES (?, ?, ?, ?)
    ''', (produto_id, tipo, quantidade, preco_custo))
    conn.commit()
    conn.close()

def estornar_venda_db(venda_id, produto_id, quantidade):
    conn = conectar()
    cursor = conn.cursor()
    try:
        # 1. Devolve a quantidade ao estoque
        cursor.execute("UPDATE produtos SET quantidade = quantidade + ? WHERE id = ?", 
                       (quantidade, produto_id))
        
        # 2. Deleta o registro da venda
        cursor.execute("DELETE FROM vendas WHERE id = ?", (venda_id,))
        
        conn.commit()
        return True, "Venda estornada com sucesso! Estoque atualizado."
    except Exception as e:
        conn.rollback()
        return False, f"Erro ao estornar: {e}"
    finally:
        conn.close()