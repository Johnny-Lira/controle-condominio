import os
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import io
import locale

locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')

# Configuração da página
st.set_page_config(
    page_title="Balancete Financeiro",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

def formatar_moeda_locale(valor):
    return locale.currency(valor, grouping=True, symbol=False)

# Função para formatar valores monetários
def formatar_moeda(valor):
    """Formata valores para moeda brasileira"""
    if pd.isna(valor) or valor == 0:
        return "R$ 0,00"

    if valor < 0:
        return (
            f"R$ {valor:,.2f}".replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )
    else:
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def converter_valor_moeda(texto):
    """Converte string de moeda para float"""
    if pd.isna(texto) or texto == "":
        return 0.0

    # Remove R$, espaços e converte vírgula para ponto
    valor_limpo = str(texto).replace("R$", "").replace(" ", "").strip()

    # Trata valores negativos
    negativo = valor_limpo.startswith("-")
    if negativo:
        valor_limpo = valor_limpo[1:]

    # Converte pontos de milhares e vírgula decimal
    if "," in valor_limpo and "." in valor_limpo:
        # Formato brasileiro: 1.234.567,89
        valor_limpo = valor_limpo.replace(".", "").replace(",", ".")
    elif "," in valor_limpo:
        # Apenas vírgula decimal: 1234,89
        valor_limpo = valor_limpo.replace(",", ".")

    try:
        valor = float(valor_limpo)
        return -valor if negativo else valor
    except:
        return 0.0


def processar_balancete_txt(conteudo):
    """Processa arquivo TXT de balancete"""
    try:
        linhas = conteudo.strip().split("\n")

        # Encontra o período do balancete
        periodo = ""
        for linha in linhas[:5]:
            if "até" in linha.lower() or "período" in linha.lower():
                periodo = linha.strip()
                break

        # Encontra os dados do balancete
        header = []
        dados_balancete = []
        header_encontrado = False

        for linha in linhas:
            linha = linha.strip()

            # Pula linhas vazias e cabeçalhos
            if not linha or "GRUPO SALDO" in linha or "SALDO ANTERIOR" in linha:
                if "GRUPO" in linha:
                    header_encontrado = True
                
            # Processa linhas de dados após encontrar header
            if header_encontrado and linha:
                if linha.startswith(("GRUPO SALDO", "SALDO ANTERIOR", "CRÉDITOS", "DÉBITOS", "SALDO ATUAL")):
                    header.append(linha)
            
            # Para no Condomínio
            if linha.startswith("Condomínio"):
                linhas_transformadas = [linha.rstrip('\r') for linha in linhas[8:13]]
                dados_balancete.append(linhas_transformadas)

            if linha.startswith("Fundo de Reserva"):
                linhas_transformadas = [linha.rstrip('\r') for linha in linhas[13:18]]
                dados_balancete.append(linhas_transformadas)

            if linha.startswith("Fundo de Obras"):
                linhas_transformadas = [linha.rstrip('\r') for linha in linhas[18:23]]
                dados_balancete.append(linhas_transformadas)

            if linha.startswith("Retenção de Tributos e Impost"):
                linhas_transformadas = [linha.rstrip('\r') for linha in linhas[23:28]]
                dados_balancete.append(linhas_transformadas)

            if linha.startswith("Conta Op - 13 Salario com Encargos"):
                linhas_transformadas = [linha.rstrip('\r') for linha in linhas[28:33]]
                dados_balancete.append(linhas_transformadas)

            if linha.startswith("Total"):
                linhas_transformadas = [linha.rstrip('\r') for linha in linhas[33:38]]
                dados_balancete.append(linhas_transformadas)

        if not dados_balancete:
            return None, None

        # Cria DataFrame
        df = pd.DataFrame(
            dados_balancete,
            columns=header
        )

        # Converte valores monetários
        for col in ["SALDO ANTERIOR", "CRÉDITOS", "DÉBITOS", "SALDO ATUAL"]:
            df[col] = df[col].apply(converter_valor_moeda)

        return df, periodo

    except Exception as e:
        st.error(f"Erro ao processar arquivo: {str(e)}")
        return None, None


def criar_metricas_financeiras(df):
    """Cria métricas financeiras principais"""
    if df is None or df.empty:
        return

    # Remove linha total se existir
    df_sem_total = df[~df["GRUPO SALDO"].str.contains("Total", case=False, na=False)]

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_creditos = df_sem_total["CRÉDITOS"].sum()
        st.metric("💰 Total Créditos", formatar_moeda(total_creditos), delta=None)

    with col2:
        total_debitos = df_sem_total["DÉBITOS"].sum()
        st.metric("💸 Total Débitos", formatar_moeda(total_debitos), delta=None)

    with col3:
        saldo_atual = df_sem_total["SALDO ATUAL"].sum()
        delta_saldo = saldo_atual - df_sem_total["SALDO ANTERIOR"].sum()
        st.metric(
            "📊 Saldo Atual",
            formatar_moeda(saldo_atual),
            delta=formatar_moeda_locale(delta_saldo)
            #delta=round(delta_saldo,2),
        )

    with col4:
        movimento_total = total_creditos + total_debitos
        st.metric("🔄 Movimento Total", formatar_moeda(movimento_total), delta=None)


def criar_graficos_balancete(df):
    """Cria gráficos específicos para o balancete"""
    if df is None or df.empty:
        return

    # Remove linha total para os gráficos
    df_grafico = df[~df["GRUPO SALDO"].str.contains("Total", case=False, na=False)].copy()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 Saldo Atual por Grupo")

        # Cria cores baseadas em valores positivos/negativos
        cores = ["red" if x < 0 else "green" for x in df_grafico["SALDO ATUAL"]]

        fig_saldo = go.Figure(
            data=[
                go.Bar(
                    x=df_grafico["GRUPO SALDO"],
                    y=df_grafico["SALDO ATUAL"],
                    marker_color=cores,
                    text=[formatar_moeda(x) for x in df_grafico["SALDO ATUAL"]],
                    textposition="outside",
                )
            ]
        )

        fig_saldo.update_layout(
            title="Saldo Atual por Grupo",
            xaxis_title="Grupos",
            yaxis_title="Valor (R$)",
            xaxis_tickangle=-45,
            height=400,
        )

        st.plotly_chart(fig_saldo, use_container_width=True)

    with col2:
        st.subheader("🔄 Movimentação Financeira")

        # Agrupa créditos e débitos
        movimentacao = pd.DataFrame(
            {
                "Tipo": ["CRÉDITOS", "DÉBITOS"],
                "Valor": [df_grafico["CRÉDITOS"].sum(), df_grafico["DÉBITOS"].sum()],
            }
        )

        fig_mov = px.pie(
            movimentacao,
            values="Valor",
            names="Tipo",
            title="Distribuição Créditos vs Débitos",
            color_discrete_map={"CRÉDITOS": "green", "DÉBITOS": "red"},
        )

        st.plotly_chart(fig_mov, use_container_width=True)

    # Segunda linha de gráficos
    col3, col4 = st.columns(2)

    with col3:
        st.subheader("📈 Evolução dos Saldos")

        # Cria gráfico comparativo saldo anterior vs atual
        df_evolucao = df_grafico.melt(
            id_vars=["GRUPO SALDO"],
            value_vars=["SALDO ANTERIOR", "SALDO ATUAL"],
            var_name="Período",
            value_name="Valor",
        )

        fig_evolucao = px.bar(
            df_evolucao,
            x="GRUPO SALDO",
            y="Valor",
            color="Período",
            barmode="group",
            title="Comparação Saldo Anterior vs Atual",
        )

        fig_evolucao.update_layout(xaxis_tickangle=-45, height=400)
        st.plotly_chart(fig_evolucao, use_container_width=True)

    with col4:
        st.subheader("💹 Variação por Grupo")

        # Calcula variação
        df_grafico["Variacao"] = (
            df_grafico["SALDO ATUAL"] - df_grafico["SALDO ANTERIOR"]
        )

        cores_var = ["red" if x < 0 else "green" for x in df_grafico["Variacao"]]

        fig_var = go.Figure(
            data=[
                go.Bar(
                    x=df_grafico["GRUPO SALDO"],
                    y=df_grafico["Variacao"],
                    marker_color=cores_var,
                    text=[formatar_moeda(x) for x in df_grafico["Variacao"]],
                    textposition="outside",
                )
            ]
        )

        fig_var.update_layout(
            title="Variação do Período",
            xaxis_title="Grupos",
            yaxis_title="Variação (R$)",
            xaxis_tickangle=-45,
            height=400,
        )

        st.plotly_chart(fig_var, use_container_width=True)


def criar_tabela_balancete(df):
    """Cria tabela formatada do balancete"""
    if df is None or df.empty:
        return

    # Cria cópia para formatação
    df_formatado = df.copy()

    # Formata valores monetários
    for col in ["SALDO ANTERIOR", "CRÉDITOS", "DÉBITOS", "SALDO ATUAL"]:
        df_formatado[col] = df_formatado[col].apply(formatar_moeda)

    # Destaca linha total
    def destacar_total(row):
        if "Total" in str(row["GRUPO SALDO"]):
            return ["background-color: #f0f0f0; font-weight: bold"] * len(row)
        return [""] * len(row)

    st.dataframe(
        df_formatado.style.apply(destacar_total, axis=1),
        use_container_width=True,
        hide_index=True,
    )


def ler_arquivo_e_separar_por_blocos(caminho_do_arquivo):
    """
    Lê um arquivo de texto e o divide em blocos de texto,
    onde cada bloco é separado por uma ou mais linhas em branco.

    Args:
        caminho_do_arquivo (Path ou str): O caminho para o arquivo de texto.

    Returns:
        list: Uma lista de strings, onde cada string é um bloco de texto.
              Linhas vazias dentro dos blocos são mantidas, mas linhas
              em branco que separam os blocos são usadas como delimitadores.
    """
    blocos = []
    bloco_atual = []

    try:
        with open(caminho_do_arquivo, 'r', encoding='utf-8') as f:
            for linha in f:
                # Remove espaços e quebras de linha no final para verificar se a linha está vazia
                linha_limpa = linha.strip()

                if linha_limpa:
                    # Se a linha não está em branco, adicione-a ao bloco atual
                    bloco_atual.append(linha) # Adiciona a linha original com sua quebra de linha
                else:
                    # Se a linha está em branco e temos um bloco acumulado
                    if bloco_atual:
                        # Junte as linhas do bloco atual em uma única string e adicione à lista de blocos
                        blocos.append("".join(bloco_atual).strip()) # .strip() final para remover quebras de linha extras no final do bloco
                        bloco_atual = [] # Reinicia o bloco atual
            
            # Após o loop, adicione o último bloco se houver
            if bloco_atual:
                blocos.append("".join(bloco_atual).strip())

    except FileNotFoundError:
        print(f"Erro: O arquivo '{caminho_do_arquivo}' não foi encontrado.")
        return []
    except Exception as e:
        print(f"Ocorreu um erro ao ler o arquivo '{caminho_do_arquivo}': {e}")
        return []
    
    return blocos

def formatar_periodo( inicial , final):
    periodo_inicial_str = inicial.split(' até ')
    periodo_final_str = final.split(' até ')

    return f"{periodo_inicial_str[0]} até {periodo_final_str[1]}"

def consolidar_blocos(blocos):
    df_balancetes = []
    periodos = []

    for bloco in blocos:
        df_balancete, periodo = processar_balancete_txt(bloco)

        df_balancetes.append(df_balancete)
        periodos.append(periodo)


    df_concat_balancetes = pd.concat(df_balancetes, ignore_index=True)
    print("DataFrame consolidado (antes do agrupamento e limpeza):")
    print(df_concat_balancetes)
    print("\nTipos de dados antes da conversão:")
    print(df_concat_balancetes.dtypes)
    print("-" * 50)
    
    colunas_numericas = ["SALDO ANTERIOR", "CRÉDITOS", "DÉBITOS", "SALDO ATUAL"]

    for col in colunas_numericas:
        df_concat_balancetes[col] = pd.to_numeric(df_concat_balancetes[col], errors='coerce')

    df_concat_balancetes = df_concat_balancetes.fillna(0)

    print("\nDataFrame consolidado (após conversão e fillna):")
    print(df_concat_balancetes)
    print("\nTipos de dados após conversão:")
    print(df_concat_balancetes.dtypes)
    print("-" * 50)

    df_balancete_consolidado = df_concat_balancetes.groupby("GRUPO SALDO")[colunas_numericas].sum().reset_index()

    print("\nDataFrame Final Consolidado (df_balancete_sum):")
    print(df_balancete_consolidado)
    
    periodo_consolidado = formatar_periodo( periodos[0] , periodos[-1])

    return df_balancete_consolidado, periodo_consolidado





# Interface principal
st.title("💰 Dashboard Balancete Financeiro")
st.markdown("---")


arquivo = 'dados/dados.txt'

blocos = ler_arquivo_e_separar_por_blocos(arquivo)

df_balancete, periodo = consolidar_blocos(blocos)




if df_balancete is not None:
    # Cabeçalho com período
    if periodo:
        st.subheader(f"📅 {periodo}")
    else:
        st.subheader("📅 Balancete Analítico")

    # Métricas principais
    st.subheader("📊 Resumo Financeiro")
    criar_metricas_financeiras(df_balancete)

    st.markdown("---")

    # Tabela do balancete
    st.subheader("📋 Balancete Detalhado")
    criar_tabela_balancete(df_balancete)

    st.markdown("---")

    # Gráficos
    st.subheader("📈 Análises Visuais")
    criar_graficos_balancete(df_balancete)

    # Análise adicional
    st.markdown("---")
    st.subheader("🔍 Análise Detalhada")

    # Remove total para análise
    df_analise = df_balancete[
        ~df_balancete["GRUPO SALDO"].str.contains("Total", case=False, na=False)
    ]

    col1, col2 = st.columns(2)

    with col1:
        st.write("**📈 Grupos com Saldo Positivo:**")
        positivos = df_analise[df_analise["SALDO ATUAL"] > 0]
        if not positivos.empty:
            for _, row in positivos.iterrows():
                st.write(f"• {row['GRUPO SALDO']}: {formatar_moeda(row['SALDO ATUAL'])}")
        else:
            st.write("Nenhum grupo com saldo positivo")

    with col2:
        st.write("**📉 Grupos com Saldo Negativo:**")
        negativos = df_analise[df_analise["SALDO ATUAL"] < 0]
        if not negativos.empty:
            for _, row in negativos.iterrows():
                st.write(f"• {row['GRUPO SALDO']}: {formatar_moeda(row['SALDO ATUAL'])}")
        else:
            st.write("Nenhum grupo com saldo negativo")
