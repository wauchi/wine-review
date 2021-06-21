import sqlite3

import folium
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import streamlit as st
from folium.plugins import MarkerCluster
from streamlit_folium import folium_static


class Model:

    def __init__(self, path: str) -> None:
        self._con = sqlite3.connect(path)
        self._cur = self._con.cursor()

    def get_price_rating(self) -> pd.DataFrame:
        df = pd.DataFrame(self._cur.execute(
            "select rating, price from review join wine on review.wine_id = wine.wine_id where price != '';").fetchall())
        df.rename(columns={0: "rating", 1: "price"}, inplace=True)
        return df

    def get_avg_price_per_winery(self) -> pd.DataFrame:
        df = pd.DataFrame(self._cur.execute(
            "select avg(price), winery from wine join winery on winery.winery_id = wine.winery_id group by wine.winery_id order by avg(price) desc;").fetchall())
        df.rename(columns={0: "avg_price", 1: "winery"}, inplace=True)
        return df

    def get_avg_rating_per_wine(self) -> pd.DataFrame:
        df = pd.DataFrame(self._cur.execute(
            """select avg(rating), designation.name || ' ' || winery || ' ' || grape.name
                from review 
                 join wine on wine.wine_id = review.wine_id  
                 join designation on designation.designation_id = wine.designation_id
                 join winery on winery.winery_id = wine.winery_id 
                 join grape on grape.grape_id = wine.grape_id 
                group by review.wine_id order by avg(rating) desc;""").fetchall())
        df.rename(columns={0: "avg_rating", 1: "wine"}, inplace=True)
        return df

    def get_location_information_of_best_wine(self) -> pd.DataFrame:
        df = pd.DataFrame(self._cur.execute("""
            select temp.name, temp.region1_name, temp.region2_name, temp.province_name, temp.country_name, temp.winery
                FROM
                    (
                        select avg(rating) as rating
                             , designation.name || ' ' || winery || ' ' || grape.name AS name
                             , r1.region as region1_name
                             , r2.region as region2_name
                             , province.province as province_name
                             , country.name as country_name
                             , winery.winery
                        from review 
                         join wine on wine.wine_id = review.wine_id  
                         join designation on designation.designation_id = wine.designation_id
                         join winery on winery.winery_id = wine.winery_id 
                         join grape on grape.grape_id = wine.grape_id
                         join region as r1 on wine.region_1_id = r1.region_id
                         join region as r2 on wine.region_2_id = r2.region_id
                         join province on wine.province_id = province.province_id
                         join country on province.country_id = country.country_id
                        group by review.wine_id 
                        order by avg(rating) desc
                    ) as temp
                limit 1;
        """).fetchall())
        df.rename(columns={0: "wine", 1: "region1", 2: "region2", 3: "province", 4: "country", 5: "winery"},
                  inplace=True)
        return df

    def get_avg_price_per_province(self) -> pd.DataFrame:
        df = pd.DataFrame(self._cur.execute("""
            SELECT avg(Price)
                 , p.Province
            from wine
             join province p on wine.Province_ID = p.Province_ID
            group by p.Province_ID
            order by avg(Price) desc;
        """).fetchall())
        df.rename(columns={0: "price", 1: "province"}, inplace=True)
        return df

    def get_avg_price_per_country(self) -> pd.DataFrame:
        df = pd.DataFrame(self._cur.execute("""
            SELECT avg(Price)
                 , c.Name
            from wine
             join province p on wine.Province_ID = p.Province_ID
             join country c on p.Country_ID = c.Country_ID
            group by c.Country_ID
            order by avg(Price) desc;
        """).fetchall())
        df.rename(columns={0: "price", 1: "country"}, inplace=True)
        return df

    def get_number_of_wines_per_country(self) -> pd.DataFrame:
        df = pd.DataFrame(self._cur.execute("""
            select count(*)
                 , c.name
            from wine
             join province p on p.Province_ID = wine.Province_ID
             join country c on c.Country_ID = p.Country_ID
            group by c.name
            order by count(*) desc;
           """).fetchall())
        df.rename(columns={0: "number", 1: "country"}, inplace=True)
        return df

    def get_number_of_wines_per_grape(self) -> pd.DataFrame:
        df = pd.DataFrame(self._cur.execute("""
            select count(*)
                 , g.name
            from wine
             join grape g on g.Grape_ID = wine.Grape_ID
            group by g.name
            order by count(*) desc;
           """).fetchall())
        df.rename(columns={0: "number", 1: "grape"}, inplace=True)
        return df


class MapCreator():
    def get_long(self, row):
        if row["country"] == "Switzerland":
            return 46.94809, 7.44744
        if row["country"] == "England":
            return 51.509865, -0.118092
        if row["country"] == "Germany":
            return 48.137154, 11.576124
        if row["country"] == "Hungary":
            return 47.497913, 19.040236
        if row["country"] == "Canada":
            return 50.000000, -85.000000
        if row["country"] == "US":
            return 40.730610, -73.935242
        if row["country"] == "Italy":
            return 41.902782, 12.496366
        if row["country"] == "Australia":
            return -33.865143, 151.209900
        if row["country"] == "Israel":
            return 31.771959, 35.217018
        if row["country"] == "France":
            return 48.864716, 2.349014
        else:
            return 0, 0

    def process(self, df: pd.DataFrame):
        df[["Latitude", "Longitude"]] = df.apply(lambda row: self.get_long(row), axis=1, result_type="expand")

        df = df[df["Latitude"] != 0]

        world_map = folium.Map(tiles="cartodbpositron")
        marker_cluster = MarkerCluster().add_to(world_map)
        # for each coordinate, create circlemarker of user percent
        for i in range(len(df)):
            lat = df.iloc[i]['Latitude']
            long = df.iloc[i]['Longitude']
            popup_text = """Land : {}<br>
                            Durchschnittlicher Preis : {} USD<br>"""
            popup_text = popup_text.format(df.iloc[i]['country'],
                                           int(df.iloc[i]['price'])
                                           )
            folium.CircleMarker(location=(lat, long), radius=20, popup=popup_text, fill=True, fillOpacity=0).add_to(
                marker_cluster)

        return world_map


model = Model('wine_database.db')
creator = MapCreator()

sns.set_palette(sns.color_palette("husl", 9))

st.title("Analyse der Weinbewertungen")
st.write("Auf dieser Seite wird eine kurze Analyse über 130'000 Weinbewertungen gemacht")
st.image("img/header.jpg")

# Bewertung in Korellation mit Preis
st.subheader('Bewertung in Korellation mit Preis')
st.write(
    "Im untenstehenden Streudiagramm kann die Korrelation zwischen dem Preis und der Bewertung des Weines eingesehen "
    "werden. Eine bessere Bewertung bedeutet nicht, dass ein Wein teurer ist.")

price_rating = model.get_price_rating()
fig, ax = plt.subplots()

sns.scatterplot(data=price_rating, x="rating", y="price", ax=ax)
ax.set(ylim=(1, 1000))
ax.set(xlabel="Bewertung", ylabel="Preis in USD")

st.pyplot(fig)

# Durchschnittspreis pro Weingut
st.subheader('Durchschnittspreis pro Weingut')
st.write(
    "Im untenstehenden Balkendiagramm ist ersichtlich, wie viel der durchschnittliche Wein eines Weingutes kostet. "
    "Das Diagramm enthält die teuersten 10 Weingüter.")

price_winery = model.get_avg_price_per_winery()
fig, ax = plt.subplots()

sns.barplot(x="avg_price", y="winery", data=price_winery[:10], ax=ax)
ax.set(xlabel="Durchschnittspreis in USD", ylabel="")

st.pyplot(fig)

# Durchschnittspreis pro Land, Province
st.subheader('Durchschnittspreis pro Land und Provinz')
st.write("In der untenstehenden Karte kann der Durchschnittspreis der zehn teuersten Weinländer angeschaut werden.")

price_country = model.get_avg_price_per_country()
price_province = model.get_avg_price_per_province()

folium_static(creator.process(price_country))

st.write(
    "In den untenstehenden Säulendiagrammen kann der Durchschnittspreis der zehn teuersten Weinländer (rechts) und "
    "der zehn teuersten Provinzen (links) angeschaut werden.")

fig, axs = plt.subplots(ncols=2, figsize=(9, 6))

sns.barplot(x="country", y="price", data=price_country[:10], ax=axs[0])
axs[0].set_xticklabels(axs[0].get_xticklabels(), rotation=90)
axs[0].set(xlabel="", ylabel="Durchschnittspreis in USD")

sns.barplot(x="province", y="price", data=price_province[:10], ax=axs[1])
axs[1].set_xticklabels(axs[1].get_xticklabels(), rotation=90)
axs[1].set(xlabel="", ylabel="")

st.pyplot(fig)

# Anzahl Weine pro Land und Trauben
st.subheader('Anzahl Weine pro Land und Trauben')
st.write(
    "In den Grafiken kann die Anzahl verschiedener Weine pro Land (links) und pro Traube (rechts) entnommen werden.")

wines_country = model.get_number_of_wines_per_country()
wines_grape = model.get_number_of_wines_per_grape()

fig, axs = plt.subplots(ncols=2, figsize=(9, 6))

sns.barplot(x="country", y="number", data=wines_country[:10], ax=axs[0])
axs[0].set_xticklabels(axs[0].get_xticklabels(), rotation=90)
axs[0].set(xlabel="", ylabel="Anzahl Weine")

sns.barplot(x="grape", y="number", data=wines_grape[:10], ax=axs[1])
axs[1].set_xticklabels(axs[1].get_xticklabels(), rotation=90)
axs[1].set(xlabel="", ylabel="")

st.pyplot(fig)

st.subheader('Der beste Wein')
text = "Der beste Wein laut unseren Bewertungen ist der Reserve Trefethen Cabernet Sauvignon. Dieser kommt aus " \
       "Kalifornien in den Vereinigten Staaten. Genauer aus dem Oak Knoll Distrikt in Napa. Er wird von der Winzerei " \
       "Trefethen hergestellt und kostet genau 100 USD. Sein durchschnittliches Rating über 23 Bewertungen ist 99 von " \
       "100 Punkten. "
st.write(text)
st.image("img/wineyard.jpg", caption="Weingut der Familie Trefethen")
