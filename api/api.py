from flask import Flask, request, make_response, jsonify
import json
from wsh_models import sess, Users, Locations, Oura_token
from wsh_config import ConfigDev
import bcrypt
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from utilsDecorators import token_required

app = Flask(__name__)
salt = bcrypt.gensalt()

# with open(r'C:\Users\captian2020\Documents\config_files\config_whatSticks01.json') as config_file:
#     config = json.load(config_file)

# class ConfigDev:
#     DEBUG = True
#     SECRET_KEY = config.get('SECRET_KEY')
#     SQLALCHEMY_DATABASE_URI = config.get('SQL_URI')
#     SQLALCHEMY_TRACK_MODIFICATIONS = True
#     WEATHER_API_KEY = config.get('WEATHER_API_KEY')
config = ConfigDev()
app.config.from_object(config)

@app.route('/add_user', methods = ['GET', 'POST'])
def add_user():
    request_data = request.get_json()
    min_loc_distance_difference = 1000

    users = sess.query(Users).all()

    for user in users:
        if request_data.get('email') == user.email:
            return 'User already exists'
    
    try:
        add_user_dict = {}
        add_user_dict['email'] = request_data.get('email')
        #encode password
        hashed_pw = bcrypt.hashpw(request_data.get('password').encode('utf-8'), salt)
        add_user_dict['password'] = hashed_pw
        add_user_dict['lat'] = request_data.get('lat')
        add_user_dict['lon'] = request_data.get('lon')
        add_user_dict['location_id'] = ''
        new_user = Users(**add_user_dict)
        sess.add(new_user)
        sess.commit()

    except:
        return f"Something is wrong with the data you tried to add to the database."

    # Check Locations table to see if user's location already exists or close enough (.1 degree)
    locations_unique_list = sess.query(Locations).all()
    for loc in locations_unique_list:
        lat_diff = abs(float(request_data.get('lat')) - loc.lat)
        lon_diff = abs(float(request_data.get('lon')) - loc.lon)
        loc_dist_diff = lat_diff + lon_diff

        if loc_dist_diff < min_loc_distance_difference:
            min_loc_distance_difference = loc_dist_diff
            location_id = loc.id
        
    if min_loc_distance_difference < .1:
        new_user = sess.query(Users).filter_by(email = request_data.get('email')).first()
        new_user.location_id = location_id
        sess.commit()
        return f"{request_data.get('email')} added succesfully!"

    else:
    # coordinates not found in Location and add coordinates as new location
        new_loc_dict = {}
        new_loc_dict['city'] = request_data.get('city')
        new_loc_dict['region'] = request_data.get('region')
        new_loc_dict['country'] = request_data.get('country')
        new_loc_dict['lat'] = request_data.get('lat')
        new_loc_dict['lon'] = request_data.get('lon')

        new_location = Locations(**new_loc_dict)
        sess.add(new_location)
        sess.commit()

        just_added_location = sess.query(Locations).filter_by(lat = request_data.get('lat'),
            lon = request_data.get('lon')).first()

        new_user = sess.query(Users).filter_by(email = request_data.get('email')).first()
        new_user.location_id = just_added_location.id
        sess.commit()

        return f"{request_data.get('email')} and new location added succesfully!"


@app.route('/login', methods = ['GET'])
def login():

    auth = request.authorization
    print('auth.username::::', auth.username)

    # Checks to see if this request has an auth payload
    if not auth or not auth.username or not auth.password:
        return make_response('Could not verify', 401, {'WWW-Authenticate' : 'Basic realm="Login required!"'})

    user = sess.query(Users).filter_by(email= auth.username).first()

    # checks to see if auth payload has a user
    if not user:
        return make_response('Could note verify - user not found', 401, {'WWW-Authenticate' : 'Basic realm="Login required!"'})

    if bcrypt.checkpw(auth.password.encode('utf-8'), user.password):
        expires_sec=60*20#set to 20 minutes
        s=Serializer(config.SECRET_KEY, expires_sec)
        token = s.dumps({'user_id': user.id}).decode('utf-8')
        print('token::')
        print(token)

        return jsonify({'token': token})
    
    return make_response('Could not verify', 401, {'WWW-Authenticate' : 'Basic realm="Login required!"'})


@app.route('/user_logged_in_check', methods = ['GET'])
@token_required
def user_check(current_user):
    print(current_user)

    return f'{current_user.email} is logged in'


@app.route('/oura_token_upload', methods = ['GET', 'POST'])
@token_required
def oura_token_upload(current_user):
    print('in oura_token_upload')

    request_data = request.get_json()

    if request_data.get('oura_token') == '' or request_data.get('oura_token') == None:
        return jsonify({'message': 'No token found in request'})

    #not hasing token becasue this guy said its no big deal:
    # https://stackoverflow.com/questions/51855393/how-to-encrypt-tokens-in-database

    add_token = Oura_token(token = request_data.get('oura_token'))
    sess.add(add_token)
    sess.commit()

    current_user.oura_token_id = add_token.id
    sess.commit()

    return jsonify({'message':'Oura token successfully uploaded'})



if __name__ == '__main__':
    app.run()