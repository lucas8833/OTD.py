import streamlit as st
import pandas as pd
import plotly.express as px
from PIL import Image

# ========== CONFIGURAÇÃO ========== #
st.set_page_config(page_title="Dashboard OTD", page_icon="📊", layout="wide")

# Logo na barra lateral
logo = Image.open('logo_DFS.png')
st.sidebar.image(logo, use_container_width=True)
st.sidebar.title("📑 Filtros")

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


def calcular_otd(df, autorizado, contrato):
    df_filtrado = df[(df['ANO'] == 2025)]

    if autorizado != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['SAW'].str.upper().str.contains(autorizado.upper(), na=False)]

    if contrato != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['CONTRATO'] == contrato]

    agrupado = df_filtrado.groupby(['MÊS_ANO', 'CONTRATO']).agg(
        total_chamados=('NOTA', 'count'),
        chamados_no_prazo=('STATUS', lambda x: (x == 'NO PRAZO').sum())
    ).reset_index()

    agrupado['OTD (%)'] = (agrupado['chamados_no_prazo'] / agrupado['total_chamados']) * 100

    return agrupado, df_filtrado


def plot_evolucao_anual(agrupado, meta_otd):
    evolucao = agrupado.groupby('MÊS_ANO').agg(
        OTD_medio=('OTD (%)', 'mean')
    ).reset_index()

    fig = px.bar(
        evolucao, x='MÊS_ANO', y='OTD_medio',
        title='📊 Evolução Anual do OTD (%)',
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


# ========== APP ========== #
df, metas = carregar_dados()

# Sidebar - Filtros
autorizados = sorted(df['SAW'].dropna().unique())
autorizado = st.sidebar.selectbox('Selecione o Autorizado (SAW):', ['Todos'] + autorizados)

contratos_disponiveis = sorted(df['CONTRATO'].dropna().unique())
contrato = st.sidebar.selectbox('Selecione o Contrato:', ['Todos'] + contratos_disponiveis)

# Calcular dados
agrupado, df_filtrado = calcular_otd(df, autorizado, contrato)

# Obter meta
meta_otd = None
if contrato != 'Todos':
    meta_info = metas[metas['CONTRATO'] == contrato]
    if not meta_info.empty:
        meta_otd = meta_info['META OTD (%)'].values[0]

# KPIs
titulo = f" Análise "
titulo += f"do autorizado: **{autorizado}**" if autorizado != 'Todos' else "**de todos os autorizados**"
titulo += f" | Contrato: **{contrato}**" if contrato != 'Todos' else " | **Todos os contratos**"

st.title('Dashboard de OTD - Contratos')
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

# Aviso se abaixo da meta
if meta_otd and otd_ponderado < meta_otd:
    st.error(f"⚠️ O OTD atual ({otd_ponderado:.2f}%) está abaixo da meta de {meta_otd}%")

# Gráfico de evolução anual
if not agrupado.empty:
    st.plotly_chart(plot_evolucao_anual(agrupado, meta_otd), use_container_width=True)
else:
    st.warning("⚠️ Não há dados para o filtro selecionado.")

# Desempenho por Especialista
st.markdown("## Desempenho por Especialista de Campo (EC)")
ec_resumo = desempenho_por_ec(df_filtrado)
st.dataframe(ec_resumo, use_container_width=True)

# Ranking - Piores Autorizados
st.markdown("## Autorizados com Pior OTD")
ranking_aut = df.groupby('SAW').agg(
    total_chamados=('NOTA', 'count'),
    chamados_no_prazo=('STATUS', lambda x: (x == 'NO PRAZO').sum())
).reset_index()
ranking_aut['OTD (%)'] = (ranking_aut['chamados_no_prazo'] / ranking_aut['total_chamados']) * 100
ranking_aut = ranking_aut.sort_values(by='OTD (%)').head(10)
st.dataframe(ranking_aut, use_container_width=True)

# Ranking - Piores Contratos
st.markdown("## Contratos com Pior OTD")
ranking_contratos = df.groupby('CONTRATO').agg(
    total_chamados=('NOTA', 'count'),
    chamados_no_prazo=('STATUS', lambda x: (x == 'NO PRAZO').sum())
).reset_index()
ranking_contratos['OTD (%)'] = (ranking_contratos['chamados_no_prazo'] / ranking_contratos['total_chamados']) * 100
ranking_contratos = ranking_contratos.sort_values(by='OTD (%)').head(10)
st.dataframe(ranking_contratos, use_container_width=True)














