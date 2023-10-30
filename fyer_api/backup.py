from urllib.parse import parse_qs,urlparse
from fyers_api import accessToken
from fyers_api import fyersModel
import pandas as pd
import requests
import datetime
import pyotp
import json
import time
import sys
import pdb
import os
from datetime import datetime as dt, timedelta
import logging
import talib as ta
import pytz
import multiprocessing
import saur_config

loss_per_trade=50

def setup_logger(logger_name):
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:  # Check if handlers already exist to avoid duplication
        file_handler = logging.FileHandler(os.getcwd()+logger_name+'.log')
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)

        logger.addHandler(file_handler)

    logger.propagate = False  # Disable propagation from the root logger

    return logger
##login_function_start_from_here
main_file=os.path.basename(__file__)
logger=setup_logger(main_file[:len(main_file)-3])

def login():
	APP_ID =  "T6QAO808F1"#"0YW29QZVF0" # App ID from myapi dashboard is in the form appId-appType. Example - EGNI8CE27Q-100, In this code EGNI8CE27Q will be APP_ID and 100 will be the APP_TYPE
	APP_TYPE = "100"
	SECRET_KEY = '2PTNKPAX8W'#'R4FV65PN0V'
	client_id= f'{APP_ID}-{APP_TYPE}'

	FY_ID = "XS00790"  # Your fyers ID
	APP_ID_TYPE = "2"  # Keep default as 2, It denotes web login
	TOTP_KEY = "ASURHDP3G4VJXITDALAKMZZZVIE5L5YU"  # TOTP secret is generated when we enable 2Factor TOTP from myaccount portal
	PIN = "1236"  # User pin for fyers account

	REDIRECT_URI = "https://127.0.0.1/"  # Redirect url from the app.
	factor2 = pyotp.TOTP(TOTP_KEY).now()
	# print(factor2)

	# pdb.set_trace()

	# API endpoints

	BASE_URL = "https://api-t2.fyers.in/vagator/v2"
	BASE_URL_2 = "https://api.fyers.in/api/v2"
	URL_SEND_LOGIN_OTP = BASE_URL + "/send_login_otp"   #/send_login_otp_v2
	URL_VERIFY_TOTP = BASE_URL + "/verify_otp"
	URL_VERIFY_PIN = BASE_URL + "/verify_pin"
	URL_TOKEN = BASE_URL_2 + "/token"
	URL_VALIDATE_AUTH_CODE = BASE_URL_2 + "/validate-authcode"
	SUCCESS = 1
	ERROR = -1

	##login_request_start_from_here!!!

	def send_login_otp(fy_id, app_id):
		try:
			result_string = requests.post(url=URL_SEND_LOGIN_OTP, json= {"fy_id": fy_id, "app_id": app_id })
			if result_string.status_code != 200:
				return [ERROR, result_string.text]
			result = json.loads(result_string.text)
			request_key = result["request_key"]
			return [SUCCESS, request_key]
		except Exception as e:
			return [ERROR, e]

	def verify_totp(request_key, totp):
		try:
			result_string = requests.post(url=URL_VERIFY_TOTP, json={"request_key": request_key,"otp": totp})
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
	# print(f'URL to activate APP:  {urlToActivate}')

	# Step 1 - Retrieve request_key from send_login_otp API

	send_otp_result = send_login_otp(fy_id=FY_ID, app_id=APP_ID_TYPE)

	if send_otp_result[0] != SUCCESS:
		print(f"send_login_otp failure - {send_otp_result[1]}")
		sys.exit()
	else:
		print("send_login_otp success")


	# Step 2 - Verify totp and get request key from verify_otp API
	for i in range(1,3):
		request_key=send_otp_result[1]
		verify_totp_result=verify_totp(request_key=request_key, totp=pyotp.TOTP(TOTP_KEY).now())
		if verify_totp_result[0]!=SUCCESS:
			print(f"verify_totp_result failure - {verify_totp_result[1]}")
			time.sleep(1)
		else:
			break

	request_key_2 = verify_totp_result[1]

	# Step 3 - Verify pin and send back access token
	ses = requests.Session()
	payload_pin = {"request_key":f"{request_key_2}","identity_type":"pin","identifier":f"{PIN}","recaptcha_token":""}
	res_pin = ses.post('https://api-t2.fyers.in/vagator/v2/verify_pin', json=payload_pin).json()
	# print(res_pin['data'])
	ses.headers.update({
		'authorization': f"Bearer {res_pin['data']['access_token']}"
	})



	authParam = {"fyers_id":FY_ID,"app_id":APP_ID,"redirect_uri":REDIRECT_URI,"appType":APP_TYPE,"code_challenge":"","state":"None","scope":"","nonce":"","response_type":"code","create_cookie":True}
	authres = ses.post('https://api.fyers.in/api/v2/token', json=authParam).json()
	# print(authres)
	url = authres['Url']
	# print(url)
	parsed = urlparse(url)
	auth_code = parse_qs(parsed.query)['auth_code'][0]



	session.set_token(auth_code)
	response = session.generate_token()
	access_token= response["access_token"]
	# print(access_token)

	fyers = fyersModel.FyersModel(client_id=client_id, token=access_token, log_path=os.getcwd())
	print(fyers.get_profile())

if __name__=="__main__":
	fyers=login()

def get_hist_data(fyers,symbol,time_frame,date_from,date_to):
    
    data = {
    "symbol":"NSE:"+symbol+"-EQ",
    "resolution":str(time_frame),
    "date_format":"1",
    "range_from":date_from,
    "range_to":date_to,
    "cont_flag":"1"
}
    while True:
        try:
            hist_data=fyers.history(data=data)['candles']
            break
        # print(hist_data)

        except Exception as e:
            print(str(e),"\n")
            time.sleep(5)

    for data in hist_data:
        date_obj= dt.fromtimestamp(data[0])
        dist = pytz.timezone('Asia/Kolkata')
        data[0] = date_obj.astimezone(dist)

    df = pd.DataFrame(hist_data, columns=['date', 'open', 'high', 'low', 'close', 'volume'])
    df.set_index('date', inplace=True)
    return df

traded_stocks = []
max_no_of_trades = 5 #1kam ke rakhna hai 

exchange = "NSE"
eq = "EQ"

def apply_orb_strategy(stock_symbol):
    # Your ORB strategy implementation here
	from_time=(dt.today().date() - timedelta(days=5)).strftime("%Y-%m-%d")
	to_time=dt.today().date().strftime("%Y-%m-%d")

	print(f"stock_symbol :{stock_symbol}")

	intra_data=get_hist_data(fyers,stock_symbol,"15",from_time,to_time)
	print(intra_data)


def main():
	watchlist = ['ABB', 'ABBOTINDIA', 'ABCAPITAL', 'ABFRL', 'ACC', 'ADANIENT', 'ADANIGREEN', 'ADANIPORTS', 'ADANITRANS', 'ALKEM', 'AMBUJACEM', 'APOLLOHOSP', 'ASHOKLEY', 'ASIANPAINT', 'ASTRAL', 'AUBANK', 'AUROPHARMA', 'AWL', 'AXISBANK', 'BAJAJ-AUTO', 'BAJAJFINSV', 'BAJAJHLDNG', 'BAJFINANCE', 'BALKRISIND', 'BANDHANBNK', 'BANKBARODA', 'BANKINDIA', 'BATAINDIA', 'BEL', 'BERGEPAINT', 'BHARATFORG', 'BHARTIARTL', 'BHEL', 'BIOCON', 'BPCL', 'BRITANNIA', 'CANBK', 'CHOLAFIN', 'CIPLA', 'CLEAN', 'COALINDIA', 'COFORGE', 'COLPAL', 'CONCOR', 'COROMANDEL', 'CROMPTON', 'CUMMINSIND', 'DALBHARAT', 'DEEPAKNTR', 'DELHIVERY', 'DIVISLAB', 'DIXON', 'DLF', 'DMART', 'DRREDDY', 'EICHERMOT', 'EMAMILTD', 'ESCORTS', 'FEDERALBNK', 'FORTIS', 'GAIL', 'GLAND', 'GODREJCP', 'GODREJPROP', 'GRASIM', 'GSPL', 'GUJGASLTD', 'HAL', 'HAVELLS', 'HCLTECH', 'HDFC', 'HDFCAMC', 'HDFCBANK', 'HDFCLIFE', 'HEROMOTOCO', 'HINDALCO', 'HINDPETRO', 'HINDUNILVR', 'HINDZINC', 'HONAUT', 'ICICIBANK', 'ICICIGI', 'ICICIPRULI', 'IDEA', 'IDFCFIRSTB', 'IEX', 'IGL', 'INDHOTEL', 'INDIAMART', 'INDIANB', 'INDIGO', 'INDUSINDBK', 'INDUSTOWER', 'INFY', 'IOC', 'IPCALAB', 'ISEC', 'ITC', 'JINDALSTEL', 'JSWENERGY', 'JSWSTEEL', 'JUBLFOOD', 'KOTAKBANK', 'L&TFH', 'LALPATHLAB', 'LAURUSLABS', 'LICHSGFIN', 'LICI', 'LT', 'LTIM', 'LTTS', 'LUPIN', 'M&M', 'M&MFIN', 'MARICO', 'MARUTI', 'MAXHEALTH', 'MFSL', 'MOTHERSON', 'MPHASIS', 'MRF', 'MSUMI', 'MUTHOOTFIN', 'NAM-INDIA', 'NATIONALUM', 'NAUKRI', 'NAVINFLUOR', 'NESTLEIND', 'NTPC', 'NYKAA', 'OBEROIRLTY', 'OFSS', 'OIL', 'ONGC', 'PAGEIND',  'PERSISTENT', 'PETRONET', 'PFC', 'PGHH', 'PIDILITIND', 'PIIND', 'PNB', 'POLICYBZR', 'POLYCAB', 'POONAWALLA', 'POWERGRID', 'PRESTIGE', 'RAMCOCEM', 'RECLTD', 'RELIANCE', 'SAIL', 'SBICARD', 'SBILIFE', 'SBIN', 'SHREECEM', 'SIEMENS', 'SONACOMS', 'SRF', 'SUNPHARMA', 'SUNTV', 'SYNGENE', 'TATACHEM', 'TATACOMM', 'TATACONSUM', 'TATAELXSI', 'TATAMOTORS', 'TATAPOWER', 'TATASTEEL', 'TCS', 'TECHM', 'TITAN', 'TORNTPHARM', 'TORNTPOWER', 'TRENT', 'TRIDENT', 'TTML', 'UBL', 'ULTRACEMCO', 'UNIONBANK', 'UPL', 'VBL', 'VEDL', 'VOLTAS', 'WHIRLPOOL', 'WIPRO', 'YESBANK', 'ZEEL', 'ZOMATO', 'ZYDUSLIFE']
    
	pool = multiprocessing.Pool(processes=multiprocessing.cpu_count())
    
    # Apply ORB strategy to all stocks using the Pool.map function
	pool.map(apply_orb_strategy, watchlist)
    
    # Close and join the Pool
	pool.close()
	pool.join()

if __name__ == "__main__":
	main()


# def check_signal(stocks_list):
# 	for name in stocks_list:
# 		try:			
# 			intra_data=get_hist_data(name,"15",from_date,to_date)

# 		except Exception as e:
# 			print(e)
			


# while True:
# 	watchlist=[]
# 	now = datetime.now()
# 	current_time = now.strftime("%H:%M:%S")
# 	logger.info(f"{current_time}")
# 	if(current_time >= "10:01:05"):    

# 		for name in watchlist:
# 			try:			
# 				datal = {"symbols":f"{exchange}:{name}-{eq}"}#,"ohlcv_flag":"1"}
# 				logger.info({"symbols":f"{exchange}:{name}-{eq}"})

# 				Ltp = fyers.quotes(datal) ['d'] [0] ['v'] ['lp']
# 				logger.info(f" LTP: {Ltp}")
# 				# print(Ltp)

# 				from_datetime =(datetime.now() - timedelta(days=1))   # From last & days
# 				to_datetime = datetime.now().strftime('%Y-%m-%d')

# 				while True:
# 					print(from_datetime,to_datetime)
# 					data = {"symbol":f"{exchange}:{name}-{eq}","resolution":"15","date_format":"1","range_from":from_datetime.strftime('%Y-%m-%d'), "range_to":to_datetime,"cont_flag":"1"}

# 					try:
# 						nx = fyers.history(data)
# 						cols = ['datetime','open','high','low','close','volume']
# 						df = pd.DataFrame.from_dict(nx['candles'])
# 						# df = pd.DataFrame(nx)
# 						df.columns = cols
# 						df['datetime'] = pd.to_datetime(df['datetime'],unit = "s")
# 						df['datetime'] = df['datetime'].dt.tz_localize('utc').dt.tz_convert('Asia/Kolkata')
# 						df['datetime'] = df['datetime'].dt.tz_localize(None)

# 						df = df.set_index('datetime')
						
# 						if len(df)<=25:
# 							from_datetime-=timedelta(days=1)
# 							print("one day back")
						
# 						if(len(df)>25):
# 							print(df)
# 							break
# 					except Exception as e:
# 						logger.info(f"Error : {e}")
# 				# logger.info(f" Data : {nx}")
# 				# print(nx)

# 				logger.info(f"DF : {df}")

# 				print(f"scanning in",name)
# 				logger.info(f"scanning in {name}")

# 			except Exception as e:
# 				print("error in data fetching")
# 				logger.info("error in data fetching")

# 			df['upperband'], df['middleband'], df['lowerband'] = ta.BBANDS(df['close'], timeperiod=20, nbdevup=2, nbdevdn=2, matype=0)
# 			# logger.info(f"Upper band{df['upperband']} Middleband: {df['middleband']} Lower band : {df['lowerband']} ")

# 			positive_crossover = (df['open'][25] >= df['close'][25]) and (df['open'][26] >= df['close'][26]) and (df['lowerband'][25] >= df['close'][25]) and (df['lowerband'][26] >= df['close'][26]) and (df['lowerband'][27] <= df['close'][27]) #and (df['high'][27] <= Ltp)  
# 			negative_crossover =  (df['open'][25] <= df['close'][25]) and (df['open'][26] <= df['close'][26]) and (df['upperband'][25] <= df['close'][25]) and (df['upperband'][26] <= df['close'][26]) and (df['upperband'][27] >= df['close'][27]) #and (df['low'][27] >= Ltp)
# 			# pdb.set_trace()
# 			# print(df['upperband'][27],df['close'][27])
# 			high_27=df['high'].iloc[27]
# 			low_27=df['low'].iloc[27]
# 			print(high_27,low_27)
# 			def compare(a, b):
# 				if (a < b):
# 					# print(a)
# 					return (a) #- (a < b)
# 				else: 
# 					return(b)
# 			##calculating_diff
# 			num1_sell = Ltp
# 			num2_sell = df['high'].iloc[27]
# 			if num1_sell > num2_sell:
# 				diff_sell = (num1_sell - num2_sell).round(1)
# 			else:
# 				diff_sell = (num2_sell - num1_sell).round(1)
# 			num1_buy = Ltp
# 			num2_buy = df['low'].iloc[27]
# 			if num1_buy > num2_buy:
# 				diff_buy = (num1_buy - num2_buy).round(1)
# 			else:
# 				diff_buy = (num2_buy - num1_buy).round(1)
# 			# gap = round((openx/df.close-1)*100, 2)
# 			buy_target = round(Ltp*0.1,1)#.iloc[-1]
# 			buy_stoploss_stop = low_27
# 			sell_target = round(Ltp*0.1,1)#.iloc[-1]
# 			sell_stoploss_stop = high_27#.iloc[-1]
# 			buy_stoploss = compare(a=buy_stoploss_stop, b=diff_buy)
# 			sell_stoploss = compare(a=sell_stoploss_stop, b=diff_sell)
# 			capital = 5000

# 			if (positive_crossover) and (name not in traded_stocks) and (len(traded_stocks) <= max_no_of_trades):

# 				data = {
# 						"symbol":f"{exchange}:{name}-{eq}",
# 						"qty":round(loss_per_trade/(high_27-low_27)),
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
# 						}                              ## This is a sample example to place a limit order you can make the further changes based on your requriements 
# 				print(fyers.place_order(data))
# 				#logger.info(f"{fyers.place_order(data)}")

# 				print("buy in ......................", name)
# 				logger.info(f"buy in ......................, {name}")
# 				traded_stocks.append(name)
# 			if (negative_crossover) and (name not in traded_stocks) and (len(traded_stocks) <= max_no_of_trades):
# 				# traded_stocks.append(name)
# 				data = {
# 						"symbol":f"{exchange}:{name}-{eq}",
# 						"qty":round(loss_per_trade/(high_27-low_27)),
# 						"type":2,
# 						"side":-1,
# 						"productType":"BO",
# 						"limitPrice":0,
# 						"stopPrice":0,
# 						"validity":"DAY",
# 						"disclosedQty":0,
# 						"offlineOrder":"False",
# 						"stopLoss":sell_stoploss,
# 						"takeProfit":sell_target
# 						}                              ## This is a sample example to place a limit order you can make the further changes based on your requriements 
# 				print(fyers.place_order(data))
# 				#logger.info(fyers.place_order(data))

# 				print("sell in ......................", name)
# 				logger.info(f"sell in ...................... {name}")

# 				traded_stocks.append(name)
# 			time.sleep(1)
# #strategy_end_here!!!!!
