from urllib.parse import parse_qs,urlparse
from fyers_api import accessToken
from fyers_api import fyersModel
from datetime import datetime as dt
import pandas as pd
import requests
import datetime
import pyotp
import json
import time
import sys
import pdb
import os
from datetime import datetime, timedelta
import pandas_ta as ta
import logging
import frontendltp
import threading

loss_per_trade = 50

def setup_logger(logger_name):
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:  # Check if handlers already exist to avoid duplication
        file_handler = logging.FileHandler(os.getcwd() + logger_name + '.log')
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)

        logger.addHandler(file_handler)

    logger.propagate = False  # Disable propagation from the root logger

    return logger

main_file = os.path.basename(__file__)
logger = setup_logger(main_file[:len(main_file) - 3])

def print_and_log(msg):
    print(msg)
    logger.info(msg)

def login():
    APP_ID = "T6QAO808F1"  # App ID from myapi dashboard is in the form appId-appType.
    APP_TYPE = "100"
    SECRET_KEY = '2PTNKPAX8W'
    client_id = f'{APP_ID}-{APP_TYPE}'

    FY_ID = "XS00790"  # Your fyers ID
    APP_ID_TYPE = "2"  # Keep default as 2, It denotes web login
    TOTP_KEY = "ASURHDP3G4VJXITDALAKMZZZVIE5L5YU"
    PIN = "1236"

    REDIRECT_URI = "https://127.0.0.1/"

    BASE_URL = "https://api-t2.fyers.in/vagator/v2"
    BASE_URL_2 = "https://api.fyers.in/api/v2"
    URL_SEND_LOGIN_OTP = BASE_URL + "/send_login_otp"
    URL_VERIFY_TOTP = BASE_URL + "/verify_otp"
    URL_VERIFY_PIN = BASE_URL + "/verify_pin"
    URL_TOKEN = BASE_URL_2 + "/token"
    URL_VALIDATE_AUTH_CODE = BASE_URL_2 + "/validate-authcode"
    SUCCESS = 1
    ERROR = -1

    def send_login_otp(fy_id, app_id):
        try:
            result_string = requests.post(url=URL_SEND_LOGIN_OTP, json={"fy_id": fy_id, "app_id": app_id})
            if result_string.status_code != 200:
                return [ERROR, result_string.text]
            result = json.loads(result_string.text)
            request_key = result["request_key"]
            return [SUCCESS, request_key]
        except Exception as e:
            return [ERROR, e]

    def verify_totp(request_key, totp):
        try:
            result_string = requests.post(url=URL_VERIFY_TOTP, json={"request_key": request_key, "otp": totp})
            if result_string.status_code != 200:
                return [ERROR, result_string.text]
            result = json.loads(result_string.text)
            request_key = result["request_key"]
            return [SUCCESS, request_key]
        except Exception as e:
            return [ERROR, e]

    session = accessToken.SessionModel(client_id=client_id, secret_key=SECRET_KEY, redirect_uri=REDIRECT_URI,
                                       response_type='code', grant_type='authorization_code')

    urlToActivate = session.generate_authcode()

    send_otp_result = send_login_otp(fy_id=FY_ID, app_id=APP_ID_TYPE)

    if send_otp_result[0] != SUCCESS:
        print(f"send_login_otp failure - {send_otp_result[1]}")
        sys.exit()
    else:
        print("send_login_otp success")

    for i in range(1, 3):
        request_key = send_otp_result[1]
        verify_totp_result = verify_totp(request_key=request_key, totp=pyotp.TOTP(TOTP_KEY).now())
        if verify_totp_result[0] != SUCCESS:
            print(f"verify_totp_result failure - {verify_totp_result[1]}")
            time.sleep(1)
        else:
            break

    request_key_2 = verify_totp_result[1]

    ses = requests.Session()
    payload_pin = {"request_key": f"{request_key_2}", "identity_type": "pin", "identifier": f"{PIN}",
                   "recaptcha_token": ""}
    res_pin = ses.post('https://api-t2.fyers.in/vagator/v2/verify_pin', json=payload_pin).json()
    ses.headers.update({
        'authorization': f"Bearer {res_pin['data']['access_token']}"
    })

    authParam = {"fyers_id": FY_ID, "app_id": APP_ID, "redirect_uri": REDIRECT_URI, "appType": APP_TYPE,
                 "code_challenge": "", "state": "None", "scope": "", "nonce": "", "response_type": "code",
                 "create_cookie": True}
    authres = ses.post('https://api.fyers.in/api/v2/token', json=authParam).json()
    url = authres['Url']
    parsed = urlparse(url)
    auth_code = parse_qs(parsed.query)['auth_code'][0]

    session.set_token(auth_code)
    response = session.generate_token()
    access_token = response["access_token"]

    fyers = fyersModel.FyersModel(client_id=client_id, token=access_token, log_path=os.getcwd())
    print(fyers.get_profile())
    return fyers

fyers = login()
print(fyers)

# def get_hist_data(symbol, time_frame, date_from, date_to):
#     data = {
#         "symbol": "NSE:" + symbol + "-EQ",
#         "resolution": str(time_frame),
#         "date_format": "1",
#         "range_from": date_from,
#         "range_to": date_to,
#         "cont_flag": "1"
#     }
#     try:
#         print("mm")
#         hist_data = fyers.history(data=data)['candles']
#     except Exception as e:
#         print(str(e), "\n")

#     for data in hist_data:
#         date_obj = dt.fromtimestamp(data[0])
#         dist = pytz.timezone('Asia/Kolkata')
#         data[0] = date_obj.astimezone(dist)

#     df = pd.DataFrame(hist_data, columns=['date', 'open', 'high', 'low', 'close', 'volume'])
#     df.set_index('date', inplace=True)
#     return df

# def get_ltp(stock_symbol):
#     try:
#         symbol = "NSE:" + stock_symbol + "-EQ"
#         ltp = frontendltp.WSgetLtp(symbol)
#     except Exception as e:
#         print_and_log(f"{stock_symbol} :{e}")
#     return ltp

# def compare(a, b):
#     if (a < b):
#         return (a) #- (a < b)
#     else: 
#         return(b)

# def apply_orb_strategy(stock_symbol):
#     try:
#         current_time = dt.now().time()
#         from_time = datetime.now() - timedelta(hours=1)     # From last & days
#         to_time = datetime.now().strftime('%Y-%m-%d')

#         df = get_hist_data(stock_symbol, "5", from_time, to_time)
#         last_index = df.index[-1]

#         if last_index.strftime('%H:%M') == current_time.strftime('%H:%M'):
#             df = df.iloc[:-1]
#         df['vwap'] = ta.vwap(df['high'], df['low'], df['close'], df['volume']).round(2)#,anchor ='M')
#         df['percnt_buy'] = round((df['vwap']/df['low']-1)*100, 2)
#         df['percnt_sell'] = round((df['vwap']/df['high']-1)*100, 2)
#         positive_signal = (df['close'][0] >= df['vwap'][0]) and (df['percnt_buy'][1] <= -0.03) and (df['percnt_buy'][2] <= -0.03) and (df['percnt_buy'][3] <= -0.03) and (df['percnt_buy'][4] <= -0.03) and (df['percnt_buy'][5] <= -0.03)  		
#         negative_signal = (df['close'][0] <= df['vwap'][0]) and (df['percnt_sell'][1] >= 0.03) and (df['percnt_sell'][2] >= 0.03) and (df['percnt_sell'][3] >= 0.03) and (df['percnt_sell'][4] >= 0.03) and (df['percnt_sell'][5] >= 0.03) 		
#         final_buy = (df['low'][-1] <= df['vwap'][-1]) and (df['close'][-1] >= df['vwap'][-1]) and (df['high'][-1] >= Ltp) or (df['low'][-2] <= df['vwap'][-2]) and (df['close'][-2] >= df['vwap'][-2]) and (df['high'][-2] >= Ltp) or (df['low'][-3] <= df['vwap'][-3]) and (df['close'][-3] >= df['vwap'][-3]) and (df['high'][-3] >= Ltp) or (df['low'][-4] <= df['vwap'][-4]) and (df['close'][-4] >= df['vwap'][-4]) and (df['high'][-4] >= Ltp)

# 		final_sell = (df['high'][-1] >= df['vwap'][-1]) and (df['close'][-1] <= df['vwap'][-1]) and (df['low'][-1] >= Ltp) or (df['high'][-2] >= df['vwap'][-2]) and (df['close'][-2] <= df['vwap'][-2]) and (df['low'][-2] >= Ltp) or (df['high'][-3] >= df['vwap'][-3]) and (df['close'][-3] <= df['vwap'][-3]) and (df['low'][-3] >= Ltp) or (df['high'][-4] >= df['vwap'][-4]) and (df['close'][-4] <= df['vwap'][-4]) and (df['low'][-4] >= Ltp)

#         ltp=float(get_ltp(stock_symbol))
# 		high_signal_candle=df['high'].iloc[-1]
#         low_Signal_candle=df['low'].iloc[-1]
        
# 		if negative_signal and final_sell:
            
# 			num1_sell = ltp
# 			num2_sell = high_signal_candle
# 			if num1_sell > num2_sell:
# 				diff_sell = (num1_sell - num2_sell).round(1)
# 			else:
# 				diff_sell = (num2_sell - num1_sell).round(1)

# 			sell_target = round(ltp*0.01, 1)#.iloc[-1]
# 			sell_stoploss_stop = round(ltp*0.01, 1)#.iloc[-1]
#             sell_stoploss = compare(a=sell_stoploss_stop, b=diff_sell)
        
# 			while True:
#                 ltp = float(get_ltp(stock_symbol))
#                 print_and_log(f"LTP : {ltp} {stock_symbol}")
#                 if ltp <= low_signal_candle:
#                 	data = {
#                             	"symbol": f"NSE:{stock_symbol}-EQ",
#                                 "qty": round(loss_per_trade / (high_signal_candle - low_signal_candle)),
#                                 "type": 2,
#                                 "side": -1,
#                                 "productType": "BO",
#                                 "limitPrice": 0,
#                                 "stopPrice": 0,
#                                 "validity": "DAY",
#                                 "disclosedQty": 0,
#                                 "offlineOrder": "False",
#                                 "stopLoss": sell_stoploss,
#                                 "takeProfit": sell_target
#                             }   
#                     print_and_log(fyers.place_order(data))
          

# 		if positive_signal and final_buy:
#             num1_buy = ltp
# 			num2_buy = low_Signal_candle
# 			if num1_buy > num2_buy:
# 				diff_buy = (num1_buy - num2_buy).round(1)
# 			else:
# 				diff_buy = (num2_buy - num1_buy).round(1)
			
# 			# gap = round((openx/df.close-1)*100, 2)
# 			buy_target = round(ltp*0.01, 1)#.iloc[-1]
# 			buy_stoploss_stop = round(ltp*0.01, 1)#.iloc[-1]

# 			buy_stoploss = compare(a=buy_stoploss_stop, b=diff_buy)
        
# 			while True:
#                 ltp = float(get_ltp(stock_symbol))
#                 print_and_log(f"LTP : {ltp} {stock_symbol}")
#                 if ltp >= high_signal_candle:
# 					data = {
# 						"symbol":f"{exchange}:{name}-{eq}",
# 						"qty":1,#round(max_loss_per_trade/(high_candle-low_candle)),
# 						"type":2,
# 						"side":1,
# 						"productType":"BO",
# 						"limitPrice":0,
# 						"stopPrice":0,
# 						"validity":"DAY",
# 						"disclosedQty":0,
# 						"offlineOrder":"False",
# 						"stopLoss":buy_stoploss,
# 						"takeProfit":buy_target
# 						}       
#                     print_and_log(fyers.place_order(data))

             
#     finally:
#         # Make sure to release the semaphore even if an exception occurs
#         semaphore.release()

# semaphore = threading.Semaphore(9)
# def main():
#     watchlist = ["ADANIENT", "ADANIPORTS", "ASIANPAINT", "AXISBANK", "BAJAJ-AUTO", "BAJFINANCE", "BAJAJFINSV", "BPCL", "BHARTIARTL", "BRITANNIA", "CIPLA", "COALINDIA", "DRREDDY", "EICHERMOT", "GRASIM", "HCLTECH", "HDFCBANK", "HDFCLIFE", "HEROMOTOCO", "HINDALCO", "HINDUNILVR", "ICICIBANK", "IOC", "INDUSINDBK", "INFY", "ITC", "JSWSTEEL", "KOTAKBANK", "LT", "M&M", "MARUTI", "NESTLEIND", "NTPC", "ONGC", "POWERGRID", "RELIANCE", "SHREECEM", "SBIN", "SUNPHARMA", "TCS", "TATAMOTORS", "TATASTEEL", "TATACONSUM", "TECHM", "TITAN", "ULTRACEMCO", "UPL", "WIPRO", "ZEEL"]

#     # Create a list to hold thread objects
#     threads = []
    
#     for stock_symbol in watchlist:
#         # Acquire the semaphore to ensure a maximum of 10 threads are running concurrently
#         semaphore.acquire()
        
#         # Create a thread for each stock symbol and add it to the list
#         thread = threading.Thread(target=apply_orb_strategy, args=(stock_symbol,))
#         threads.append(thread)
#         thread.start()
#         time.sleep(1)
    
#     # Wait for all threads to finish
#     for thread in threads:
#         thread.join()

#         # Release the semaphore to allow another thread to start
#         semaphore.release()

# if __name__ == "__main__":
#     main()




# Initialize the FyersModel instance with your client_id, access_token, and enable async mode





