import streamlit as st
import pandas as pd
import plotly.express as px
from PIL import Image

# ========== CONFIGURAÇÃO ========== #
st.set_page_config(page_title="Dashboard OTD", page_icon="📊", layout="wide")

# Logo na barra lateral
logo = Image.open('logo_DFS.png')
st.sidebar.image(logo, use_container_width=True)
st.sidebar.title("Filtros")

# ========== FUNÇÕES ========== #
@st.cache_data
def carregar_dados():
    df = pd.read_excel('TicketsContratos2025.xlsx', sheet_name='Tickets')
    metas = pd.read_excel('TicketsContratos2025.xlsx', sheet_name='Metas')

    df['ABERTURA'] = pd.to_datetime(df['ABERTURA'])
    df['ANO'] = df['ABERTURA'].dt.year
    df['MÊS_ANO'] = df['ABERTURA'].dt.to_period('M').astype(str)

    df['STATUS'] = df['STATUS'].astype(str).str.strip().str.upper()
    return df, metas


def plot_evolucao_anual(agrupado, meta_otd):
    evolucao = agrupado.groupby('MÊS_ANO').agg(
        OTD_medio=('OTD (%)', 'mean')
    ).reset_index()

    fig = px.bar(
        evolucao, x='MÊS_ANO', y='OTD_medio',
        title='Evolução Anual do OTD (%)',
        labels={'OTD_medio': 'OTD Médio (%)'}
    )
    fig.update_layout(
        xaxis_title='Mês/Ano',
        yaxis_title='OTD Médio (%)',
        yaxis_range=[0, 105]
    )
    if meta_otd is not None:
        fig.add_hline(y=meta_otd, line_dash="dot", line_color="red")
        fig.add_annotation(
            xref="paper", x=1.02, y=meta_otd,
            text=f"Meta {meta_otd}%",
            showarrow=False,
            font=dict(color="red", size=12),
            bgcolor="white",
            bordercolor="red",
            borderwidth=1
        )
    return fig


def desempenho_por_ec(df):
    resumo = df.groupby('EC').agg(
        total_chamados=('NOTA', 'count'),
        chamados_no_prazo=('STATUS', lambda x: (x == 'NO PRAZO').sum())
    ).reset_index()
    resumo['OTD (%)'] = (resumo['chamados_no_prazo'] / resumo['total_chamados']) * 100
    resumo = resumo.sort_values(by='OTD (%)', ascending=False)
    return resumo


# Função de estilo para a tabela
def destacar_abaixo_da_meta(row):
    """
    Destaca a linha inteira em vermelho se o OTD for menor que a meta.
    """
    otd = row['OTD (%)']
    meta = row['META OTD (%)']
    color = 'background-color: #ffe6e6' if otd < meta else ''
    return [color] * len(row)


# ========== APP ========== #
df, metas = carregar_dados()
df_filtrado_sidebar = df.copy()

# Sidebar - Filtros Interdependentes
# Ordem: Especialista -> Autorizado -> Contrato

# Filtro 1: Especialista de Campo (EC)
especialistas = sorted(df_filtrado_sidebar['EC'].dropna().unique())
ec_selecionado = st.sidebar.selectbox('Filtrar por Especialista de Campo (EC):', ['Todos'] + especialistas)

if ec_selecionado != 'Todos':
    df_filtrado_sidebar = df_filtrado_sidebar[df_filtrado_sidebar['EC'] == ec_selecionado]

# Filtro 2: Autorizado (SAW)
autorizados = sorted(df_filtrado_sidebar['SAW'].dropna().unique())
autorizado_selecionado = st.sidebar.selectbox('Selecione o Autorizado (SAW):', ['Todos'] + autorizados)

if autorizado_selecionado != 'Todos':
    df_filtrado_sidebar = df_filtrado_sidebar[df_filtrado_sidebar['SAW'] == autorizado_selecionado]

# Filtro 3: Contrato
contratos_disponiveis = sorted(df_filtrado_sidebar['CONTRATO'].dropna().unique())
contrato_selecionado = st.sidebar.selectbox('Selecione o Contrato:', ['Todos'] + contratos_disponiveis)

if contrato_selecionado != 'Todos':
    df_filtrado_sidebar = df_filtrado_sidebar[df_filtrado_sidebar['CONTRATO'] == contrato_selecionado]

# Usar o dataframe final filtrado (df_filtrado_sidebar) no restante do aplicativo
df_filtrado = df_filtrado_sidebar.copy()

# Filtro principal do dashboard (para o ano de 2025)
df_filtrado = df_filtrado[(df_filtrado['ANO'] == 2025)]

# KPIs
st.title("📊 Dashboard de OTD - Contratos")
titulo = "Análise "

if ec_selecionado != 'Todos':
    titulo += f"do especialista: **{ec_selecionado}**"
elif autorizado_selecionado != 'Todos':
    titulo += f"do autorizado: **{autorizado_selecionado}**"
else:
    titulo += "geral"

if contrato_selecionado != 'Todos':
    titulo += f" | Contrato: **{contrato_selecionado}**"

st.markdown(f"### {titulo}")

col1, col2, col3, col4 = st.columns(4)

total_chamados = df_filtrado.shape[0]
chamados_no_prazo = (df_filtrado['STATUS'] == 'NO PRAZO').sum()
chamados_atraso = (df_filtrado['STATUS'] == 'ATRASO').sum()
otd_ponderado = (chamados_no_prazo / total_chamados) * 100 if total_chamados > 0 else 0

col1.metric("OTD (%) no período", f"{otd_ponderado:.2f}%")
col2.metric("Total de Chamados", int(total_chamados))
col3.metric("✅ No Prazo", int(chamados_no_prazo))
col4.metric("⏰ Em Atraso", int(chamados_atraso))

# Meta OTD
meta_otd = None
if contrato_selecionado != 'Todos':
    meta_info = metas[metas['CONTRATO'] == contrato_selecionado]
    if not meta_info.empty:
        meta_otd = meta_info['META OTD (%)'].values[0]
elif ec_selecionado != 'Todos':
    contratos_do_ec = df_filtrado['CONTRATO'].unique()
    metas_filtradas = metas[metas['CONTRATO'].isin(contratos_do_ec)]
    meta_otd = metas_filtradas['META OTD (%)'].mean() if not metas_filtradas.empty else None

if meta_otd and otd_ponderado < meta_otd:
    st.error(f"O OTD atual ({otd_ponderado:.2f}%) está abaixo da meta de {meta_otd:.1f}%")

# Evolução mensal OTD
agrupado = df_filtrado.groupby(['MÊS_ANO']).agg(
    total_chamados=('NOTA', 'count'),
    chamados_no_prazo=('STATUS', lambda x: (x == 'NO PRAZO').sum())
).reset_index()
agrupado['OTD (%)'] = (agrupado['chamados_no_prazo'] / agrupado['total_chamados']) * 100

if not agrupado.empty:
    st.plotly_chart(plot_evolucao_anual(agrupado, meta_otd), use_container_width=True)
else:
    st.warning("Não há dados para os filtros selecionados.")


# Tabela de desempenho por Autorizado
st.markdown("## Desempenho por SAW")
ranking_aut = df_filtrado.groupby('SAW').agg(
    total_chamados=('NOTA', 'count'),
    chamados_no_prazo=('STATUS', lambda x: (x == 'NO PRAZO').sum())
).reset_index()
ranking_aut['OTD (%)'] = (ranking_aut['chamados_no_prazo'] / ranking_aut['total_chamados']) * 100
st.dataframe(ranking_aut.sort_values(by='OTD (%)', ascending=False), use_container_width=True)


# Tabela de desempenho por EC (somente se EC não for selecionado)
if ec_selecionado == 'Todos':
    st.markdown("## Desempenho por Especialista de Campo")
    ec_resumo = desempenho_por_ec(df_filtrado)
    st.dataframe(ec_resumo, use_container_width=True)

# Contratos do EC selecionado (ranking por OTD)
if ec_selecionado != 'Todos':
    st.markdown("## Contratos suportados pelo Especialista")
    ranking_contratos_ec = df_filtrado.groupby('CONTRATO').agg(
        total_chamados=('NOTA', 'count'),
        chamados_no_prazo=('STATUS', lambda x: (x == 'NO PRAZO').sum())
    ).reset_index()
    ranking_contratos_ec['OTD (%)'] = (ranking_contratos_ec['chamados_no_prazo'] / ranking_contratos_ec['total_chamados']) * 100
    
    # Adicionar a coluna de metas
    ranking_contratos_ec = pd.merge(ranking_contratos_ec, metas, on='CONTRATO', how='left')
    
    # Aplicar a estilização
    st.dataframe(ranking_contratos_ec.sort_values(by='OTD (%)').style.apply(destacar_abaixo_da_meta, axis=1), use_container_width=True)

# Ranking - Piores Autorizados (exibido apenas se EC não for selecionado)
if ec_selecionado == 'Todos':
    st.markdown("## Autorizados com pior OTD")
    ranking_aut = df_filtrado.groupby('SAW').agg(
        total_chamados=('NOTA', 'count'),
        chamados_no_prazo=('STATUS', lambda x: (x == 'NO PRAZO').sum())
    ).reset_index()
    ranking_aut['OTD (%)'] = (ranking_aut['chamados_no_prazo'] / ranking_aut['total_chamados']) * 100
    st.dataframe(ranking_aut.sort_values(by='OTD (%)').head(10), use_container_width=True)

# Ranking - Piores Contratos
st.markdown("## Contratos com pior OTD")
ranking_contratos = df_filtrado.groupby('CONTRATO').agg(
    total_chamados=('NOTA', 'count'),
    chamados_no_prazo=('STATUS', lambda x: (x == 'NO PRAZO').sum())
).reset_index()
ranking_contratos['OTD (%)'] = (ranking_contratos['chamados_no_prazo'] / ranking_contratos['total_chamados']) * 100

# Adicionar a coluna de metas
ranking_contratos = pd.merge(ranking_contratos, metas, on='CONTRATO', how='left')

# Aplicar a estilização
st.dataframe(ranking_contratos.sort_values(by='OTD (%)').head(10).style.apply(destacar_abaixo_da_meta, axis=1), use_container_width=True)













