from apscheduler.schedulers.background import BackgroundScheduler
# from sqlalchemy import inspect
import json
import requests
from datetime import datetime
from wsh_models import sess, Users, Locations, Weather, Oura_token, Oura_sleep_descriptions
from wsh_config import ConfigDev

# with open(r'C:\Users\captian2020\Documents\config_files\config_whatSticks04.json') as config_file:
#     config = json.load(config_file)
config = ConfigDev()

def scheduler_funct():
    print('@In scheduler funct')
    scheduler = BackgroundScheduler()
    # job_call_weather = scheduler.add_job(call_weather, 'cron', hour = '*', minute = '*', second='*/15')
    job_call_weather_hourly = scheduler.add_job(call_weather, 'cron', hour = '*')
    # job_call_oura_sleep = scheduler.add_job(call_oura_sleep, 'cron', hour = '*', minute = '*', second = '*/15')
    job_call_oura_sleep = scheduler.add_job(call_oura_sleep, 'cron', day = '*', hour = '*', minute = '10')
    scheduler.start()

    while True:
        pass


def call_weather():
    print(f'@Calling weather {datetime.now()}')

    locations = sess.query(Locations).all()
    base_url = 'http://api.weatherapi.com/v1'
    current = '/current.json'
    astronomy = '/astronomy.json'

    payload = {}
    payload['key'] = config.WEATHER_API_KEY

    for location in locations:
        location_id = location.id
        payload['q'] = f'{location.lat}, {location.lon}'
        payload['aqi'] = 'yes'
        r_current = requests.get(base_url + current, params = payload)
        weather_dict = r_current.json()

        load_dict = {}
        if weather_dict.get('location'):
            w = weather_dict.get('location')
            load_dict['lat'] = w.get('lat')
            load_dict['lon'] = w.get('lon')
            load_dict['city_location_name'] = w.get('name')
            load_dict['region_name'] = w.get('region')
            load_dict['country_name'] = w.get('country')
            load_dict['tz_id'] = w.get('tz_id')
            load_dict['localtime_epoch'] = w.get('localtime_epoch')
            load_dict['localtime'] = w.get('localtime')

        if weather_dict.get('current'):
            c=weather_dict.get('current')
            load_dict['last_updated'] = c.get('last_updated')
            load_dict['last_updated_epoch'] = c.get('last_updated_epoch')
            load_dict['temp_c'] = c.get('temp_c')
            load_dict['temp_f'] = c.get('temp_f')
            load_dict['feelslike_c'] = c.get('feelslike_c')
            load_dict['feelslike_f'] = c.get('feelslike_f')
            load_dict['wind_mph'] = c.get('wind_mph')
            load_dict['wind_kph'] = c.get('wind_kph')
            load_dict['wind_degree'] = c.get('wind_degree')
            load_dict['wind_dir'] = c.get('wind_dir')
            load_dict['pressure_mb'] = c.get('pressure_mb')
            load_dict['pressure_in'] = c.get('pressure_in')
            load_dict['precip_mm'] = c.get('precip_mm')
            load_dict['precip_in'] = c.get('precip_in')
            load_dict['humidity'] = c.get('humidity')
            load_dict['cloud'] = c.get('cloud')
            load_dict['is_day'] = c.get('is_day')
            load_dict['uv'] = c.get('uv')
            load_dict['gust_mph'] = c.get('gust_mph')
            load_dict['gust_kph'] = c.get('gust_kph')
            if c.get('condition'):
                cond = c.get('condition')
                load_dict['condition_text'] = cond.get('text')
                load_dict['condition_icon'] = cond.get('icon')
                load_dict['condition_code'] = cond.get('code')

            if c.get('air_quality'):
                aq = c.get('air_quality')
                load_dict['co'] = aq.get('co')
                load_dict['o3'] = aq.get('o3')
                load_dict['no2'] = aq.get('no2')
                load_dict['so2'] = aq.get('so2')
                load_dict['pm2_5'] = aq.get('pm2_5')
                load_dict['pm10'] = aq.get('pm10')
                load_dict['us_epa_index'] = aq.get('us_epa_index')
                load_dict['gb_defra_index'] = aq.get('gb_defra_index')

        r_astronomy = requests.get(base_url + astronomy, params = payload)
        astronomy_dict = r_astronomy.json()

        print('r_astronomy status code: ', r_astronomy.status_code)

        if astronomy_dict.get('astronomy'):
            a_1 = astronomy_dict.get('astronomy')
            if a_1.get('astro'):
                a_2 =a_1.get('astro')
                load_dict['sunrise'] = a_2.get('sunrise')
                load_dict['sunset'] = a_2.get('sunset')        
                load_dict['moonrise'] = a_2.get('moonrise')        
                load_dict['moonset'] = a_2.get('moonset')        
                load_dict['moon_phase'] = a_2.get('moon_phase')        
                load_dict['moon_illumination'] = a_2.get('moon_illumination')       

        add_weather = Weather(**load_dict)
        sess.add(add_weather)
        sess.commit()

    # populate location name in Location table
        if location.city == None or location.city == '':
            location.city = w.get('name')
            location.region = w.get('region')
            location.country = w.get('country')
            sess.commit()


def call_oura_sleep():
    print('*** Getting OURA SLEEP data ***')
    # user_token_queries = sess.query(Oura_token).all()

    # Get all users with oura tokens
    users_oura = sess.query(Users).filter(Users.oura_token_id.isnot(None)).all()
    
    #Build user_oura_dict Keys= user_id, value = user's oura token
    users_oura_dict = {}
    for user in users_oura:
        temp_user = sess.query(Oura_token).filter_by(id = user.oura_token_id).first()
        users_oura_dict[user.id] = temp_user.token


    # Make Our API call for each user with a token
    for user_id, oura_token in users_oura_dict.items():

        url_sleep='https://api.ouraring.com/v1/sleep?start=2020-03-11&end=2020-03-21?'
        response_sleep = requests.get(url_sleep, headers={"Authorization": "Bearer " + oura_token})
        sleep_dict=response_sleep.json()

        print('response_sleep::', response_sleep.status_code)
        print('response count:::', len(sleep_dict['sleep']))

        # Add oura dictionary response to database
        for sleep_session in sleep_dict['sleep']:
            sleep_session_exists = sess.query(Oura_sleep_descriptions).filter_by(bedtime_end = sleep_session.get('bedtime_end')).first()
            if not sleep_session_exists:
                if sleep_session.get('hr_5min'):
                    del sleep_session['hr_5min']
                    del sleep_session['hypnogram_5min']
                    del sleep_session['rmssd_5min']
                if sleep_session.get('temperature_trend_deviation') or sleep_session.get('temperature_trend_deviation') ==0:
                    print('**** does this get fired ****')
                    del sleep_session['temperature_trend_deviation']
                sleep_session['user_id'] = user_id
                new_sleep = Oura_sleep_descriptions(**sleep_session)
                sess.add(new_sleep)
                sess.commit()
        
        print('*** Successfully added Oura Sleep data ****')



if __name__ == '__main__':  
    scheduler_funct()