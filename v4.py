import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import branca
import plotly.express as px
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
import openpyxl

# Data inladen en opschonen
df_airports = pd.read_csv('./vluchten/airports-extended-clean.csv', sep=';')




# Converteer Latitude en Longitude kolommen naar correcte numerieke waarden
df_airports['Latitude'] = df_airports['Latitude'].str.replace(',', '.').astype(float)
df_airports['Longitude'] = df_airports['Longitude'].str.replace(',', '.').astype(float)

# Sidebar voor navigatie tussen pagina's
st.sidebar.title("Navigatie")
pagina = st.sidebar.selectbox(
    "Selecteer de pagina",
    ["Kaart van Vliegvelden", "Vlucht Route Weergave", "Vertraging Voorspelling per Bestemming", "Aantal Vliegtuigen per Maand"]
)

# Kaart van Vliegvelden
if pagina == "Kaart van Vliegvelden":
    st.title("Kaart van Vliegvelden")

    # Gebruik landen als filter
    countries = df_airports['Country'].unique()
    selected_country = st.selectbox("Selecteer een land", countries)

    # Filter vliegvelden op basis van selectie
    filtered_airports = df_airports[df_airports['Country'] == selected_country]

    # Als er vliegvelden in het land zijn, toon de kaart
    if not filtered_airports.empty:
        st.subheader(f"Vliegvelden in {selected_country}")

        # Maak een Folium kaart
        m = folium.Map(location=[filtered_airports['Latitude'].mean(), filtered_airports['Longitude'].mean()], zoom_start=6)

        # Voeg rode rechthoekige gebieden toe voor elk vliegveld
        for _, airport in filtered_airports.iterrows():
            # Definieer een bounding box rond de locatie om het vliegveld als een vierkant weer te geven
            bounds = [
                [airport['Latitude'] - 0.01, airport['Longitude'] - 0.01],  # Onder linkerhoek
                [airport['Latitude'] + 0.01, airport['Longitude'] + 0.01]   # Boven rechterhoek
            ]
            folium.Rectangle(
                bounds,
                color='red',  # Rode kleur
                fill=True,
                fill_color='red',
                fill_opacity=0.6,
                popup=f"{airport['Name']} ({airport['IATA']})",
                tooltip=airport['Name']
            ).add_to(m)

        # Voeg de legenda toe
        legend_html = """
        <div style="position: fixed; 
                    bottom: 50px; left: 50px; width: 150px; height: 90px; 
                    background-color: white; border:2px solid grey; z-index:9999; font-size:14px;
                    ">
        <b>Legenda:</b><br>
        <i style="background:red"></i> Vliegvelden
        </div>
        """
        m.get_root().html.add_child(folium.Element(legend_html))

        # Folium kaart tonen
        folium_static(m)
    else:
        st.write(f"Geen vliegvelden gevonden in {selected_country}.")

# Vlucht Route Weergave
elif pagina == "Vlucht Route Weergave":
    st.title("Vlucht Route Weergave")

    # Data inladen
    df1 = pd.read_csv('./vluchten/airports-extended-clean.csv', sep=';')
    df2 = pd.read_csv("./schedule_airport.csv")

    # Dataset merge, op luchthaven/code
    df3 = df2.merge(df1[['ICAO', 'Name']], left_on='Org/Des', right_on='ICAO', how='left')

    vluchten = {}

    for i in range(1, 8):  # Aantal vluchten dat je verwacht
        try:
            vluchten[f"Vlucht {i}"] = pd.read_excel(f"./vluchten/30Flight {i}.xlsx")
            
        except Exception as e:
            st.error(f"Error loading flight data for Vlucht {i}: {e}")

    if not vluchten:
        st.error("Er zijn geen vluchten om te selecteren.")
    else:
        selected_flight = st.selectbox("Selecteer een vlucht", list(vluchten.keys()))
        df = vluchten[selected_flight]

        # Check if df is empty after flight selection
        if df.empty:
            st.error("Geen geldige gegevens beschikbaar voor de geselecteerde vlucht.")
        else:
            df = df.dropna(subset=['[3d Latitude]', '[3d Longitude]', '[3d Altitude M]', 'Time (secs)'])
            # Hier kan je verder gaan met het verwerken van df
            
            # Definieer de coördinaten voor de banen
            banen = {
                "Polderbaan": (52.348250, 4.711250),
                "Kaagbaan": (52.289852, 4.742564),
                "Aalsmeerbaan": (52.296685, 4.778077),
                "Oostbaan": (52.308029, 4.794181),
                "Zwanenburgbaan": (52.316599, 4.738689),
                "Buitenveldertbaan": (52.317653, 4.769317),
            }

            # Bereken de vluchtduur in een leesbaar formaat
            max_time_secs = df['Time (secs)'].max()
            flight_duration = f"{max_time_secs // 60} minuten en {max_time_secs % 60} seconden"

            # Creëer de folium kaart
            map_center = [df['[3d Latitude]'].mean(), df['[3d Longitude]'].mean()]
            flight_map = folium.Map(location=map_center, zoom_start=6)

            # Voeg markers toe voor de banen
            for baan, coord in banen.items():
                folium.Marker(location=coord, popup=baan, icon=folium.Icon(color='blue')).add_to(flight_map)

            # Definieer de hoogtes en kleuren
            altitude_bins = [-10, 1000, 3000, 7500, 12000]  # Definieer de hoogte-intervallen
            altitude_colors = ['blue', 'green', 'orange', 'red', 'yellow']  # Kleuren voor elke klasse

            # Voeg de route met verschillende kleuren toe
            coords = list(zip(df['[3d Latitude]'], df['[3d Longitude]'], df['[3d Altitude M]']))

            # Voeg de gekleurde lijn toe aan de kaart
            for i in range(len(coords) - 1):
                start = coords[i]
                end = coords[i + 1]
                
                # Bepaal de kleur op basis van de hoogte
                for j in range(len(altitude_bins) - 1):
                    if altitude_bins[j] < start[2] <= altitude_bins[j + 1]:
                        color = altitude_colors[j]
                        break

                # Voeg alleen toe als de coördinaten geldig zijn
                if pd.notna(start[0]) and pd.notna(start[1]) and pd.notna(end[0]) and pd.notna(end[1]):
                    folium.PolyLine(locations=[[start[0], start[1]], [end[0], end[1]]], color=color, weight=5).add_to(flight_map)

            # Voeg een legenda toe
            colormap = branca.colormap.LinearColormap(colors=altitude_colors, vmin=min(altitude_bins), vmax=max(altitude_bins))
            colormap.caption = 'Altitude (M)'
            colormap.add_to(flight_map)

            # Render de kaart in Streamlit met vluchtduur
            st.write(f"Vluchtduur: {flight_duration}")  # Voeg de vluchtduur toe
            folium_static(flight_map)  # Render the flight_map instead of m
elif pagina == "Vertraging Voorspelling per Bestemming":
    st.title("Vertraging Voorspelling per Bestemming")

    # Data inladen
    df1 = pd.read_csv('./vluchten/airports-extended-clean.csv', sep=';')
    df2 = pd.read_csv("./schedule_airport.csv")

    # Kolomnaam veranderen 
    df2 = df2.rename(columns={'STD': 'date', 'STA_STD_ltc': 'gepl_aank', 'ATA_ATD_ltc': 'werk_aank'})
    
    # Dataset merge, op luchthaven/code
    df3 = df2.merge(df1[['ICAO', 'Name']], left_on='Org/Des', right_on='ICAO', how='left')

    # Zet de datum- en tijdstempels om naar datetime-formaat
    df3['gepl_aank'] = pd.to_datetime(df3['date'] + ' ' + df3['gepl_aank'], format='%d/%m/%Y %H:%M:%S')
    df3['werk_aank'] = pd.to_datetime(df3['date'] + ' ' + df3['werk_aank'], format='%d/%m/%Y %H:%M:%S')

    # Bereken de vertraging (in minuten)
    df3['vertraging'] = (df3['werk_aank'] - df3['gepl_aank']).dt.total_seconds() / 60

    # Definieer features en target
    X = pd.get_dummies(df3['Name'], drop_first=True)  # One-hot encoding van bestemmingen
    y = df3['vertraging']

    # Splits de data in training en test sets
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Train het model
    model = LinearRegression()
    model.fit(X_train, y_train)

    # Selecteer de bestemming
    bestemmingen = df3['Name'].unique()
    keuze = st.selectbox("Kies een bestemming:", bestemmingen)

    # Voorspel vertraging voor de gekozen bestemming
    if keuze:
        # Maak een input vector voor de voorspelling
        input_data = pd.DataFrame(columns=X.columns)
        input_data.loc[0] = 0  # Start met een rij van nullen
        input_data[keuze] = 1  # Zet de gekozen bestemming op 1

        # Voorspel de vertraging
        voorspelling = model.predict(input_data)[0]
        st.write(f"Verwachte vertraging voor {keuze}: {voorspelling:.2f} minuten")
elif pagina == "Aantal Vliegtuigen per Maand":
    st.title('Aantal Vliegtuigen op de Luchthaven per Maand')

    # CSV-bestand inlezen
    # 
    df = pd.read_csv("./schedule_airport.csv")

    # Kolommen hernoemen
    df.rename(columns={
        'STD': 'Datum',
        'FLT': 'Vlucht nummer',
        'STA_STD_ltc': 'Geplande aankomst',
        'ATA_ATD_ltc': 'Werkelijke aankomst',
        'LSV': '(L=inbound, S=outbound)',
        'TAR': 'Geplande gate',
        'GAT': 'Werkelijke gate',
        'ACT': 'Vliegtuig type',
        'RWY': 'Landing/startbaan',
        'Org/Des': 'Bestemming / afkomst'
    }, inplace=True)

    # Controleer of de 'Datum' kolom ook tijd bevat
    df['Datum'] = pd.to_datetime(df['Datum'], format='%d/%m/%Y', dayfirst=True)

    # Voeg een kolom toe voor het jaar
    df['Jaar'] = df['Datum'].dt.year

    # Maak een dropdown menu voor het selecteren van het jaar
    selected_year = st.selectbox('Selecteer een jaar:', options=[2019, 2020])

    # Filter de dataframe op basis van het geselecteerde jaar
    filtered_df = df[df['Jaar'] == selected_year]

    # Voeg een kolom toe voor de maand; hier stel ik de tijd in op 00:00:00
    filtered_df['maand'] = filtered_df['Datum'].dt.floor('H')

    # Tel het aantal vliegtuigen per maand
    vliegtuigen_per_maand = filtered_df.groupby('maand').size().reset_index(name='Aantal Vliegtuigen')

    # Maak een interactief lijndiagram met range slider
    fig = px.line(vliegtuigen_per_maand, x='maand', y='Aantal Vliegtuigen',
                  title=f'Aantal Vliegtuigen op de Luchthaven per maand ({selected_year})',
                  labels={'maand': 'Tijd ', 'Aantal Vliegtuigen': 'Aantal Vliegtuigen'})

    # Voeg range slider en selector toe
    fig.update_layout(
        xaxis=dict(
            rangeslider=dict(visible=True),  # Voeg de range slider toe
            type="date"  # Zorg ervoor dat de x-as als datumtype wordt behandeld
        )
    )

    # Toont de figuur in de Streamlit-app
    st.plotly_chart(fig)