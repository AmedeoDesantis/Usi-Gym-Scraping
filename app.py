import pandas as pd
from datetime import datetime
import streamlit as st
import plotly.graph_objects as go

df = pd.read_csv('occupancy_log.csv')

weekdays = {"Lunedì" : 0, "Martedì" : 1, "Mercoledì" : 2, "Giovedì" : 3, "Venerdì" : 4, "Sabato" : 5, "Domenica" : 6}
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

def extract_day(df, day):
    # 'day' arriva da streamlit ed è già un oggetto date.
    # Non serve chiamare day.date()
    target_date = day if isinstance(day, datetime) else day
    
    day_df = df[df.index.date == target_date]
    day_df = day_df.resample("1min").interpolate()
    
    if day_df.empty:
        return pd.Series(dtype='float64'), day_df.index
        
    return day_df['value'].rolling(window=50, center=True).mean(), day_df.index

def extract_general_mean(df, day):
    hours_mean = df['value'].groupby(df.index.time).mean()
    #hours_mean = hours_mean.map(lambda x: round(x))
    hours_mean.index = [datetime.combine(day, time) for time in hours_mean.index]

    hours_mean = hours_mean.resample("1min").interpolate()
    hours_mean = hours_mean.rolling(window=50, center=True).mean()

    return hours_mean.values, hours_mean.index

def extract_weekday_mean(df, day, weekday):
    
    weekday_df = df[df.index.dayofweek == weekday]
    return extract_general_mean(weekday_df, day)


st.set_page_config(page_title="Monitor Palestra", layout="wide")
st.title("Monitor Occupazione Palestra")
st.caption(f"**Intervallo dati**: dal {primo_scrape.strftime(fmt_display)} al {ultimo_scrape.strftime(fmt_display)}")


# Sidebar per i controlli
with st.sidebar:
    st.header("Configurazione")
    
    weekday_sel = st.selectbox("Giorno della settimana", 
                               ("Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"),
                               index = datetime.today().weekday())
    # Selettore Data
    data_sel = st.date_input("Giorno specifico", value=datetime.today())

    st.divider()
    st.subheader("Visualizzazione")
    show_specific = st.checkbox("Occupazione del giorno", value=False)
    show_general = st.checkbox("Media generale storica", value=True)
    show_weekday = st.checkbox(f"Media dei {inv_weekdays[data_sel.weekday()]}", value=True)

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

# Formattazione Assi
fig.update_layout(
    xaxis_title="Orario",
    yaxis_title="Livello Occupazione",
    xaxis=dict(tickmode='linear', tick0=6, dtick=1, range=[6, 24]),
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