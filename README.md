# 🛒 SmartCommerce Manager

O **SmartCommerce** é um sistema de Gestão Comercial e Ponto de Venda (PDV) desenvolvido em Python. A aplicação oferece uma solução completa para pequenos comércios, unindo controlo de stock, operações de venda e inteligência de negócio (BI) numa interface intuitiva.

## 🚀 Funcionalidades

- **Gestão de Stock:** Registo de produtos com preço de custo/venda e atualização em massa via tabela interativa.
- **Ponto de Venda (PDV):** Carrinho de compras dinâmico com validação de stock em tempo real.
- **Histórico de Movimentações:** Registo automático de entradas (compras) e saídas (vendas).
- **Dashboards de BI:**
  - Faturamento Total, Lucro Líquido e Margem de Lucro.
  - Curva de Faturamento Diário vs. Acumulado.
  - Ranking de produtos mais vendidos e composição de stock.
- **Sistema de Estorno:** Capacidade de cancelar vendas, removendo o registo financeiro e devolvendo os itens ao stock automaticamente.

## 🛠️ Tecnologias Utilizadas

- **Linguagem:** Python 3.10+
- **Interface:** [Streamlit](https://streamlit.io/)
- **Banco de Dados:** SQLite (Relacional)
- **Gráficos:** Plotly Express
- **Manipulação de Dados:** Pandas

## 📦 Como Instalar e Rodar

1. Clone o repositório:

```bash
git clone https://github.com/renantorres0/smartcommerce.git
```

2. Instale as dependencias:

```bash
pip install -r requirements.txt
```

3. Execute a aplicação:

```bash
screamlit run app.py
```
