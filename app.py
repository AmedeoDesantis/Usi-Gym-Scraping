import pandas as pd
from datetime import datetime
import streamlit as st
import plotly.graph_objects as go

df = pd.read_csv('occupancy_log.csv')

months = {
    "Gennaio": 0,
    "Febbraio": 1,
    "Marzo": 2,
    "Aprile": 3,
    "Maggio": 4,
    "Giugno": 5,
    "Luglio": 6,
    "Agosto": 7,
    "Settembre": 8,
    "Ottobre": 9,
    "Novembre": 10,
    "Dicembre": 11
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


# Sidebar per i controlli
with st.sidebar:
    st.header("Configurazione")

    month_sel = st.selectbox("Media mese",
                            ("Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"),
                            index = (datetime.today().month-1))
    show_month = st.checkbox(f"Media di {month_sel}", value = False)
    
    #----------------------------------------------------------------
    #st.divider()

    weekday_sel = st.selectbox("Media giorno della settimana", 
                               ("Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"),
                               index = datetime.today().weekday())
    show_weekday = st.checkbox(f"Media dei {weekday_sel}", value=True)

    show_month_weekday = st.checkbox(f"Media dei {weekday_sel} in {month_sel}", value= True)

    #----------------------------------------------------------------
    #st.divider()


    data_sel = st.date_input("Occupazione in data:", value=datetime.today())
    show_specific = st.checkbox("Occupazione del giorno", value=False)

    #----------------------------------------------------------------
    #st.divider()
    
    show_general = st.checkbox("Media generale storica", value=False)



# Creazione del grafico con Plotly (per avere etichette Y personalizzate)
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
    add_to_plot(v, i, f"Media {month_sel}", "#3066BE")


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