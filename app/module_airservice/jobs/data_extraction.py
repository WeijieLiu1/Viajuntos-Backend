from cmath import e
from datetime import datetime
from datetime import timedelta
import requests
import os

from app.module_airservice.jobs.pollutants import contaminantes
from sqlalchemy import create_engine

from app.module_airservice.models import station_type, urban_area

hours = ['h01','h02','h03','h04','h05','h06',
         'h07','h08','h09','h10','h11','h12',
         'h13','h14','h15','h16','h17','h18',
         'h19','h20','h21','h22','h23','h24']

date_today = datetime.today()
date_anterior = date_today - timedelta(days = 1)
date_anterior = date_anterior.strftime('%Y-%m-%d')

def insert_air_station(eoi_code, name, station_t, urban_a, altitude, latitude, longitude, codi_comarca, engine) -> None:
    with engine.connect() as conn:
        conn.execute(
            'INSERT INTO air_quality_station VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
            (name, eoi_code, station_t, urban_a, altitude, latitude, longitude, 0.0, date_today, codi_comarca))

def normalizar(cont, valor) -> float:
    return valor/contaminantes[cont][0]

def insert_hour_data(hour_tag, codi_eoi, pollutant, value, engine) -> None:
    hour = hour_tag[-2:] #obtener los dos ultimos caracteres
    date_hora_final = date_anterior+' '+hour+':00:00'
    if hour == 24: date_hora_final = date_today.strftime('%Y-%m-%d')+' 00:00:00:000000'
    cont_scale = normalizar(pollutant,value)
    with engine.connect() as conn:
        conn.execute(
            'INSERT INTO air_quality_data VALUES(%s,%s,%s,%s,%s) on conflict do nothing',
            (date_hora_final, codi_eoi, pollutant, value, cont_scale))
            

def main(db_uri):
    engine = create_engine(db_uri)

    # Comprobar si los datos han cambiado des de la ultima actualización
    most_recent_remote_data_time = requests.get('https://analisi.transparenciacatalunya.cat/resource/tasf-thgu.json?$query=SELECT max(data)').json()[0]['max_data']
    most_recent_remote_data_time = datetime.strptime(most_recent_remote_data_time.split('T')[0], '%Y-%m-%d')
    with engine.connect() as conn:
        most_recent_db_data_time = conn.execute(
            'SELECT max(date_hour) FROM air_quality_data'
        ).fetchall()[0][0]
    if not most_recent_db_data_time < most_recent_remote_data_time:
        raise Exception('Remote has not updated its data since last extraction. Try again later.')
    
    # Borrar datos de hace más de un dia
    with engine.connect() as conn:
        conn.execute('DELETE FROM air_quality_data WHERE date_hour <= %s;', (date_anterior+' 00:00:00'))
    
    url = f"https://analisi.transparenciacatalunya.cat/resource/tasf-thgu.json?data={date_anterior}&$order=codi_eoi"

    #llamada a la API que contiene datos sobre la contaminación del aire del dia
    response = requests.get(url)
    response_json = response.json()

    with engine.connect() as conn:
        all_eoi_codes = conn.execute('SELECT DISTINCT eoi_code FROM air_quality_station').fetchall()
    estaciones_vistas = set(map(lambda r: r[0], all_eoi_codes))

    heroku_row_limit = 9000

    for medicion in response_json:
        if 'codi_eoi' not in medicion:
            raise Exception('Station has no eoi_code')
        if medicion['codi_eoi'] not in estaciones_vistas:
            # Insertar estación
            insert_air_station (
                medicion['codi_eoi'],
                medicion['nom_estacio'],
                station_type[medicion['tipus_estacio']].value,
                urban_area[medicion['area_urbana']].value,
                int(medicion['altitud']),
                float(medicion['latitud']),
                float(medicion['longitud']),
                float(medicion['codi_comarca']),
                engine)
            estaciones_vistas.add(medicion['codi_eoi'])
        
        # Insertar medición
        for hour in hours:
            #no todas las horas existen
            if hour in medicion:
                #insertar hora
                insert_hour_data(
                    hour,
                    medicion['codi_eoi'],
                    medicion['contaminant'],
                    float(medicion[hour]), 
                    engine)

        heroku_row_limit -= 1
        if heroku_row_limit == 0:
            return

if __name__ == '__main__':
    main(os.getenv("SQLALCHEMY_DATABASE_URL"))
