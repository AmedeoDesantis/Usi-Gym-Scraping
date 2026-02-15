import pandas as pd
from datetime import datetime
import streamlit as st
import plotly.graph_objects as go

df = pd.read_csv('occupancy_log.csv')

months = {
    "Gennaio": 1,
    "Febbraio": 2,
    "Marzo": 3,
    "Aprile": 4,
    "Maggio": 5,
    "Giugno": 6,
    "Luglio": 7,
    "Agosto": 8,
    "Settembre": 9,
    "Ottobre": 10,
    "Novembre": 11,
    "Dicembre": 12
    }

weekdays = {
    "Lunedì" : 0, 
    "Martedì" : 1, 
    "Mercoledì" : 2, 
    "Giovedì" : 3, 
    "Venerdì" : 4, 
    "Sabato" : 5, 
    "Domenica" : 6
    }

inv_weekdays = {v : k for k, v in weekdays.items()}

mapping = {"Bassa" : 0, "Media": 1, "Alta" : 2, "Massima" : 3}
inv_mapping = {v : k for k, v in mapping.items()}

df['value'] = [mapping[v] for v in df['value']]
format = "%Y-%m-%d%H:%M"
df['timestamp'] = [datetime.strptime(d+t, format) for d,t in zip(df['day'], df['hour'])]

df = df[['timestamp', 'value']].set_index("timestamp").resample("1min").interpolate()
df = df[df.index.minute == 0]
df = df[df.index.hour >= 6]

# Calcoliamo il primo e l'ultimo scrape
primo_scrape = df.index.min()
ultimo_scrape = df.index.max()

# Formattiamo le date per una lettura più piacevole
fmt_display = "%d/%m/%Y alle %H:%M"

def extract_day(df: pd.DataFrame, day: datetime) -> tuple[pd.Series, pd.DatetimeIndex]:

    target_date = day if isinstance(day, datetime) else day
    
    day_df = df[df.index.date == target_date]
    day_df = day_df.resample("1min").interpolate()
    
    if day_df.empty:
        return pd.Series(dtype='float64'), day_df.index
        
    return day_df['value'].rolling(window=50, center=True).mean(), day_df.index

def extract_general_mean(df, day):
    # Gestisci il caso di DataFrame vuoto
    if df.empty:
        return pd.Series(dtype='float64'), pd.DatetimeIndex([])
    
    hours_mean = df['value'].groupby(df.index.time).mean()
    hours_mean.index = [datetime.combine(day, time) for time in hours_mean.index]
    
    # Assicurati che l'indice sia DatetimeIndex
    if not isinstance(hours_mean.index, pd.DatetimeIndex):
        hours_mean.index = pd.DatetimeIndex(hours_mean.index)
    
    hours_mean = hours_mean.resample("1min").interpolate()
    hours_mean = hours_mean.rolling(window=50, center=True).mean()
    
    return hours_mean.values, hours_mean.index

def extract_weekday_mean(df: pd.DataFrame, day: datetime.date, weekday: int) -> tuple[pd.Series, pd.DatetimeIndex]:
    
    weekday_df = df[df.index.dayofweek == weekday]
    return extract_general_mean(weekday_df, day)

def extract_month_mean(df, day: datetime.date, month: int) -> tuple[pd.Series, pd.DatetimeIndex]:
    month_df = df[df.index.month == month]
    return extract_general_mean(month_df, day)

def extract_month_weekday_mean(df, day: datetime.date, month: int, weekday: int) -> tuple[pd.Series, pd.DatetimeIndex]:
    month_weekday_df = df[(df.index.dayofweek == weekday) & (df.index.month == month)]
    return extract_general_mean(month_weekday_df, day)


st.set_page_config(page_title="Monitor Palestra", layout="wide")
st.title("Monitor Occupazione Palestra")
st.caption(f"**Intervallo dati**: dal {primo_scrape.strftime(fmt_display)} al {ultimo_scrape.strftime(fmt_display)}")


with st.sidebar:
    st.header("Configurazione")
    
    # Selettori sempre visibili
    data_sel = st.date_input("Data", value=datetime.today())
    
    col1, col2 = st.columns(2)
    with col1:
        weekday_sel = st.selectbox("Giorno", list(weekdays.keys()), 
                                  index=datetime.today().weekday())
    with col2:
        month_sel = st.selectbox("Mese", list(months.keys()),
                                index=datetime.today().month-1)
    
    st.divider()

    if 'selected_options' not in st.session_state:
        st.session_state.selected_options = [
            "storico data",
            "media mese giorno"
        ]

    option_formatting = {
        "media generale": "Media generale",
        "media giorno" : "Media del giorno",
        "media mese" : "Media del mese",
        "media mese giorno" : "Media del giorno nel mese",
        "storico data" : "Occupazione del giorno"
        }
    
    available_options = [
        "media generale", 
        "media giorno", 
        "media mese", 
        "media mese giorno", 
        "storico data"
    ]


    options = st.multiselect(
        "Da visualizzare:",
        placeholder = "Scegli...",
        options=available_options,
        format_func = lambda x: option_formatting[x],
        key= "selected_options"
        )
     
    
    show_specific =         "storico data"      in options
    show_general =          "media generale"    in options
    show_weekday =          "media giorno"      in options
    show_month =            "media mese"        in options
    show_month_weekday =    "media mese giorno" in options
    
fig = go.Figure()

def add_to_plot(values, index, name, color=None):
    if values is not None:
        # Convertiamo l'indice in ore decimali per l'asse X
        x_hours = [t.hour + t.minute/60.0 for t in index]
        fig.add_trace(go.Scatter(x=x_hours, y=values, name=name, mode='lines', line=dict(color=color)))

# Logica di popolamento grafico
if show_specific:
    v, i = extract_day(df, data_sel)
    add_to_plot(v, i, f"Occupazione {data_sel.strftime('%d/%m/%Y')}", "#D0CFD1")

if show_general:
    v, i = extract_general_mean(df, data_sel)
    add_to_plot(v, i, "Media Generale", "#626369")

if show_weekday:
    v, i = extract_weekday_mean(df, data_sel, weekdays[weekday_sel])
    add_to_plot(v, i, f"Media {weekday_sel}", "#FF4B4B")

if show_month:
    v, i = extract_month_mean(df, data_sel, months[month_sel])
    add_to_plot(v, i, f"Media {month_sel}", "#995FA3")

if show_month_weekday:
    v, i = extract_month_weekday_mean(df, data_sel, months[month_sel], weekdays[weekday_sel])
    add_to_plot(v, i, f"Media {weekday_sel} in {month_sel}", "#3066BE")


# Formattazione Assi
fig.update_layout(
    xaxis_title="Orario",
    yaxis_title="Livello Occupazione",
    xaxis=dict(tickmode='linear', tick0=6, dtick=1, range=[6, 23]),
    yaxis=dict(
        tickvals=[0, 1, 2, 3],
        ticktext=["Bassa", "Media", "Alta", "Massima"],
        range=[-0.2, 3.2]
    ),
    legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
    margin=dict(l=20, r=20, t=20, b=20),
    height=600
)

st.plotly_chart(fig, use_container_width=True)