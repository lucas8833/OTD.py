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
    metas = pd.read_excel('OTD_Metas.xlsx')

    df['ABERTURA'] = pd.to_datetime(df['ABERTURA'])
    df['ANO'] = df['ABERTURA'].dt.year
    df['MÊS_ANO'] = df['ABERTURA'].dt.to_period('M').astype(str)

    return df, metas


def calcular_otd(df, autorizado, contrato):
    df_filtrado = df[(df['ANO'] == 2025)]

    if autorizado != 'Todos':
        df_filtrado = df_filtrado[
            df_filtrado['SAW'].str.upper().str.contains(autorizado.upper(), na=False)
        ]

    if contrato != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['CONTRATO'] == contrato]

    agrupado = df_filtrado.groupby(['MÊS_ANO', 'CONTRATO']).agg(
        total_chamados=('NOTA', 'count'),
        chamados_no_prazo=('STATUS', lambda x: (x == 'NO PRAZO').sum())
    ).reset_index()

    agrupado['OTD (%)'] = (agrupado['chamados_no_prazo'] / agrupado['total_chamados']) * 100

    return agrupado, df_filtrado


def plot_otd_mensal(agrupado, meta_otd):
    fig = px.line(
        agrupado, x='MÊS_ANO', y='OTD (%)', color='CONTRATO',
        markers=True, title='📈 OTD Mensal por Contrato'
    )
    fig.update_layout(
        xaxis_title='Mês/Ano',
        yaxis_title='OTD (%)',
        yaxis_range=[0, 105],
        hovermode="x unified"
    )

    if meta_otd is not None:
        fig.add_hline(
            y=meta_otd, line_dash="dot", line_color="red",
            annotation_text=f"Meta {meta_otd}%", 
            annotation_position="bottom right"
        )

    return fig


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
        fig.add_hline(
            y=meta_otd, line_dash="dot", line_color="red",
            annotation_text=f"Meta {meta_otd}%", 
            annotation_position="bottom right"
        )

    return fig


# ========== APP ========== #
df, metas = carregar_dados()

# Sidebar - Filtros
autorizados = sorted(df['SAW'].unique())
autorizado = st.sidebar.selectbox('Selecione o Autorizado (SAW):', ['Todos'] + autorizados)

# Filtro dinâmico de contratos
contratos_disponiveis = sorted(df['CONTRATO'].unique())
contrato = st.sidebar.selectbox('Selecione o Contrato:', ['Todos'] + contratos_disponiveis)

# Calcular dados
agrupado, df_filtrado = calcular_otd(df, autorizado, contrato)

# Obter meta se contrato específico estiver selecionado
meta_otd = None
if contrato != 'Todos':
    meta_info = metas[metas['CONTRATO'] == contrato]
    if not meta_info.empty:
        meta_otd = meta_info['META OTD (%)'].values[0]

# KPIs
titulo = f"🔧 Análise "
if autorizado != 'Todos':
    titulo += f"do autorizado: **{autorizado}**"
else:
    titulo += "**de todos os autorizados**"

if contrato != 'Todos':
    titulo += f" | Contrato: **{contrato}**"
else:
    titulo += " | **Todos os contratos**"

st.title('📊 Dashboard de OTD - Contratos')
st.markdown(f"### {titulo}")

col1, col2, col3, col4 = st.columns(4)

# Cálculo correto do OTD ponderado
total_chamados = df_filtrado.shape[0]
chamados_no_prazo = (df_filtrado['STATUS'] == 'NO PRAZO').sum()
chamados_atraso = (df_filtrado['STATUS'] == 'ATRASO').sum()

if total_chamados > 0:
    otd_ponderado = (chamados_no_prazo / total_chamados) * 100
else:
    otd_ponderado = 0

# Mostrar KPI com ou sem meta
if contrato != 'Todos' and meta_otd is not None:
    kpi_otd = f"{otd_ponderado:.2f}% (Meta: {meta_otd}%)"
else:
    kpi_otd = f"{otd_ponderado:.2f}%"

col1.metric("OTD (%) no período", kpi_otd)
col2.metric("Total de Chamados", int(total_chamados))
col3.metric("✅ No Prazo", int(chamados_no_prazo))
col4.metric("⏰ Atraso", int(chamados_atraso))

# Gráficos
if not agrupado.empty:
    col1, col2 = st.columns(2)

    with col1:
        st.plotly_chart(plot_otd_mensal(agrupado, meta_otd), use_container_width=True)

    with col2:
        st.plotly_chart(plot_evolucao_anual(agrupado, meta_otd), use_container_width=True)

else:
    st.warning("⚠️ Não há dados para o filtro selecionado.")








