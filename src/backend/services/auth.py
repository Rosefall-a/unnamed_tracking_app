import jwt
from datetime import timedelta, datetime
import os

def generate_jwt_token(user_id):
    secret_key = os.getenv('JWT_SECRET_KEY')
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(hours=1)
    }
    return jwt.encode(payload, secret_key, algorithm='HS256')