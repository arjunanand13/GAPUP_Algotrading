from ks_api_client import ks_api
from arjun_api import cred as arjun
import arjun_otp
import time

class login:
    def author():
        det = arjun()
        client = ks_api.KSTradeApi(access_token = det.access_token, userid = det.user_id, \
        consumer_key = det.consumer_key, ip = det.ip, app_id = det.app_id)
        try:
            client.login(password=det.password)
            print('Logged in')
        except Exception as e:
            print("Exception when calling Session Api->login: %s\n" % e)
        
        try:
            client.positions(position_type='OPEN')
        except:
            time.sleep(60)
            otp = arjun_otp.get_otp()
            client.session_2fa(access_code = otp)
            print('Session initialized. OTP = ',otp)
        
        return client
