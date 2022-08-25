from functools import wraps
from flask import request, jsonify,current_app
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from wsh_models import sess, Users
from wsh_config import ConfigDev
import json

config = ConfigDev()

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        print('* In decorator *')

        token = None

        if 'x-access-token' in request.headers:
            token = request.headers['x-access-token']
            print('x-access-token exists')
        
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        
        print('Still shoiwing a token *** ')
        s = Serializer(config.SECRET_KEY)
        decrypted_token_dict = s.loads(token)
        current_user = sess.query(Users).filter_by(id = decrypted_token_dict['user_id']).first()

        print('Almost exiting decorater **')
        
        if not current_user:
            return jsonify({'message': 'Token is invalid'}), 401
        
        print('exiting decorater **')
        return f(current_user, *args, **kwargs)
    return decorated