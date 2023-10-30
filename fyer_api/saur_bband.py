from concurrent.futures import ThreadPoolExecutor,as_completed
from urllib.parse import parse_qs, urlparse
from fyers_api import accessToken
from fyers_api import fyersModel
import pandas as pd
import requests
import pyotp
import json
import time
import sys
import os
from datetime import datetime as dt, timedelta
import logging
import talib as ta
import pytz
import threading
import frontendltp

loss_per_trade = 100

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
# print(fyers)

def get_hist_data(symbol, time_frame, date_from, date_to):
    data = {
        "symbol": "NSE:" + symbol + "-EQ",
        "resolution": str(time_frame),
        "date_format": "1",
        "range_from": date_from,
        "range_to": date_to,
        "cont_flag": "1"
    }
    try:
        print("mm")
        hist_data = fyers.history(data=data)['candles']
    except Exception as e:
        print(str(e), "\n")

    for data in hist_data:
        date_obj = dt.fromtimestamp(data[0])
        dist = pytz.timezone('Asia/Kolkata')
        data[0] = date_obj.astimezone(dist)

    df = pd.DataFrame(hist_data, columns=['date', 'open', 'high', 'low', 'close', 'volume'])
    df.set_index('date', inplace=True)
    return df

def get_ltp(stock_symbol):
    try:
        symbol = "NSE:" + stock_symbol + "-EQ"
        ltp = frontendltp.WSgetLtp(symbol)
    except Exception as e:
        print_and_log(f"{stock_symbol} :{e}")
    return ltp

def compare(a, b):
    if (a < b):
        return (a) #- (a < b)
    else: 
        return(b)
    
def apply_orb_strategy(stock_symbol):
    try:
        positive_crossover = False
        negative_crossover = False

        current_time = dt.now().time()
        from_time = (dt.today().date() - timedelta(days=5)).strftime("%Y-%m-%d")
        to_time = dt.today().date().strftime("%Y-%m-%d")

        intra_data = get_hist_data(stock_symbol, "15", from_time, to_time)
        last_index = intra_data.index[-1]

        if last_index.strftime('%H:%M') == current_time.strftime('%H:%M'):
            intra_data = intra_data.iloc[:-1]

        intra_data['upperband'], intra_data['middleband'], intra_data['lowerband'] = ta.BBANDS(intra_data['close'],
                                                                                                timeperiod=20, nbdevup=2,
                                                                                                nbdevdn=2, matype=0)
        intra_data.drop(columns=['middleband'], inplace=True)
        # print_and_log(f"{stock_symbol} :{intra_data}\n")

        today = dt.now()
        timezone = pytz.timezone('Asia/Kolkata')

        start_time = timezone.localize(today.replace(hour=9, minute=15, second=0, microsecond=0))
        end_time = timezone.localize(today.replace(hour=9, minute=30, second=0, microsecond=0))

        ohlc_data = intra_data[(intra_data.index >= start_time) & (intra_data.index <= end_time)]
        # print_and_log(f"{stock_symbol} : {ohlc_data}\n")

        negative_crossover = (ohlc_data['open'][0] >= ohlc_data['close'][0]) and (ohlc_data['open'][1] >= ohlc_data['close'][1]) and (ohlc_data['lowerband'][0] >= ohlc_data['close'][0]) and (ohlc_data['lowerband'][1] >= ohlc_data['close'][1])            
        if negative_crossover:
            print_and_log(f"{stock_symbol }lowerband conditions met")

        positive_crossover=(ohlc_data['open'][0] <= ohlc_data['close'][0]) and (ohlc_data['open'][1] <= ohlc_data['close'][1]) and (ohlc_data['upperband'][0] <= ohlc_data['close'][0]) and (ohlc_data['upperband'][1] <= ohlc_data['close'][1]) 
        if positive_crossover:
            print_and_log(f"{stock_symbol}upperband conditions met")
        
			##calculating_diff
        is_traded=False
        if positive_crossover:
            while True:
                current_time = dt.now().time()
                if current_time.minute % 15 == 0 and current_time.second == 0:
                    data = get_hist_data(stock_symbol, "15", (dt.today().date()-timedelta(days=5)).strftime("%Y-%m-%d"),
                                         dt.today().date().strftime("%Y-%m-%d"))
                    last_index = data.index[-1]

                    if last_index.strftime('%H:%M') == current_time.strftime('%H:%M'):
                        data = data.iloc[:-1]
                    data['upperband'], data['middleband'], data['lowerband'] = ta.BBANDS(data['close'],
                                                                                                 timeperiod=20, nbdevup=2,
                                                                                                 nbdevdn=2, matype=0)
                    data.drop(columns=['middleband'], inplace=True)
                    print_and_log(f"{stock_symbol} : {data}")
                    
                    if data['close'].iloc[-1] < data['upperband'].iloc[-1] :
                        print_and_log(f"{stock_symbol} Sell condition met")
                        high_signal_candle = data['high'].iloc[-1]
                        low_signal_candle = data['low'].iloc[-1]
                        print_and_log(f"{stock_symbol} high : {high_signal_candle} low : {low_signal_candle}")
                        
                        ltp=float(get_ltp(stock_symbol))
                        num1_sell = ltp
                        num2_sell = high_signal_candle
                        if num1_sell > num2_sell:
                            diff_sell = (num1_sell - num2_sell).round(1)
                        else:
                            diff_sell = (num2_sell - num1_sell).round(1)
                        sell_target = round(ltp*0.1,1)#.iloc[-1]
                        sell_stoploss_stop = high_signal_candle#.iloc[-1]
                        sell_stoploss = compare(a=sell_stoploss_stop, b=diff_sell)
                        

                        while True:
                            ltp = float(get_ltp(stock_symbol))
                            is_traded=True
                            print_and_log(f"LTP : {ltp} {stock_symbol}")
                            if ltp <= low_signal_candle:
                                data = {
                                    "symbol": f"NSE:{stock_symbol}-EQ",
                                    "qty": round(loss_per_trade / (high_signal_candle - low_signal_candle)),
                                    "type": 2,
                                    "side": -1,
                                    "productType": "BO",
                                    "limitPrice": 0,
                                    "stopPrice": 0,
                                    "validity": "DAY",
                                    "disclosedQty": 0,
                                    "offlineOrder": "False",
                                    "stopLoss": sell_stoploss,
                                    "takeProfit": sell_target
                                }
                                print_and_log(f"{stock_symbol} : {fyers.place_order(data)}\n")
                                return

                            elif ltp >= high_signal_candle:
                                return
                            time.sleep(1)
                else:
                    print_and_log(f"Waiting for candle close {stock_symbol} {current_time}\n")

                if is_traded:
                    break
                time.sleep(1)

        elif negative_crossover:
            while True:
                current_time = dt.now().time()
                if current_time.minute % 15 == 0 and current_time.second == 0:
                    data = get_hist_data(stock_symbol, 15, (dt.today().date()-timedelta(days=5)).strftime("%Y-%m-%d"),
                                         dt.today().date().strftime("%Y-%m-%d"))
                    last_index = data.index[-1]

                    if last_index.strftime('%H:%M') == current_time.strftime('%H:%M'):
                        data = data.iloc[:-1]
                    data['upperband'], data['middleband'], data['lowerband'] = ta.BBANDS(data['close'],
                                                                                         timeperiod=20, nbdevup=2,
                                                                                         nbdevdn=2, matype=0)
                    data.drop(columns=['middleband'], inplace=True)
                    print_and_log(f"{stock_symbol} : {data}")

                    if data['close'].iloc[-1] > data['lowerband'].iloc[-1]:
                        print_and_log(f"{stock_symbol} : Buy conditions met")
                        high_signal_candle = data['high'].iloc[-1]
                        low_signal_candle = data['low'].iloc[-1]

                        print_and_log(f"{stock_symbol} high : {high_signal_candle} low : {low_signal_candle}")
                        ltp=float(get_ltp(stock_symbol))
                        num1_buy=ltp
                        num2_buy = low_signal_candle
                        if num1_buy > num2_buy:
                            diff_buy = (num1_buy - num2_buy).round(1)
                        else:
                            diff_buy = (num2_buy - num1_buy).round(1)
                        buy_target = round(ltp*0.1,1)#.iloc[-1]
                        buy_stoploss_stop = low_signal_candle
                        buy_stoploss = compare(a=buy_stoploss_stop, b=diff_buy)

                        while True:
                            ltp = float(get_ltp(stock_symbol))

                            if ltp >= high_signal_candle:
                                data = {
                                    "symbol": f"NSE:{stock_symbol}-EQ",
                                    "qty": round(loss_per_trade / (high_signal_candle - low_signal_candle)),
                                    "type": 2,
                                    "side": 1,
                                    "productType": "BO",
                                    "limitPrice": 0,
                                    "stopPrice": 0,
                                    "validity": "DAY",
                                    "disclosedQty": 0,
                                    "offlineOrder": "False",
                                    "stopLoss": buy_stoploss,
                                    "takeProfit": buy_target
                                }
                                is_traded=True

                                print_and_log(f"{stock_symbol} : {fyers.place_order(data)}\n")
                                return

                            elif ltp <= low_signal_candle:
                                return
                            time.sleep(1)
                    
                else:
                    print_and_log(f"Waiting for candle close {stock_symbol} {current_time}")
                time.sleep(1)

                if is_traded:
                    break
    finally:
        # Make sure to release the semaphore even if an exception occurs
        semaphore.release()


semaphore = threading.Semaphore(9)
def main():
    watchlist = ["ADANIENT", "ADANIPORTS", "ASIANPAINT", "AXISBANK", "BAJAJ-AUTO", "BAJFINANCE", "BAJAJFINSV", "BPCL", "BHARTIARTL", "BRITANNIA", "CIPLA", "COALINDIA", "DRREDDY", "EICHERMOT", "GRASIM", "HCLTECH", "HDFCBANK", "HDFCLIFE", "HEROMOTOCO", "HINDALCO", "HINDUNILVR", "ICICIBANK", "IOC", "INDUSINDBK", "INFY", "ITC", "JSWSTEEL", "KOTAKBANK", "LT", "M&M", "MARUTI", "NESTLEIND", "NTPC", "ONGC", "POWERGRID", "RELIANCE", "SHREECEM", "SBIN", "SUNPHARMA", "TCS", "TATAMOTORS", "TATASTEEL", "TATACONSUM", "TECHM", "TITAN", "ULTRACEMCO", "UPL", "WIPRO", "ZEEL"]

    # Create a list to hold thread objects
    threads = []
    processed_symbols = set()  # Initialize an empty set to track processed symbols

    while True:
        current_time = dt.now().time()
        
        if current_time.strftime("%H:%M") >= "09:45" and current_time.strftime("%H:%M") <= "15:30":
            for stock_symbol in watchlist:
                if stock_symbol not in processed_symbols:
                    # Acquire the semaphore
                    semaphore.acquire()
                    
                    # Create a thread for the stock symbol
                    thread = threading.Thread(target=apply_orb_strategy, args=(stock_symbol,))
                    threads.append(thread)
                    thread.start()
                    
                    processed_symbols.add(stock_symbol)  # Mark the symbol as processed
                    time.sleep(1)
        
        # Rest of your logic for waiting and releasing semaphore
main()