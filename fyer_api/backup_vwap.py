from urllib.parse import parse_qs,urlparse
from fyers_api import accessToken
from fyers_api import fyersModel
# from datetime import datetime
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
# import anurag_indicators as ai
# import talib as ta
import pandas_ta as ta
import frontendltp
##login_function_start_from_here

APP_ID =  "7GHMATK4L8" # App ID from myapi dashboard is in the form appId-appType. Example - EGNI8CE27Q-100, In this code EGNI8CE27Q will be APP_ID and 100 will be the APP_TYPE
APP_TYPE = "100"
SECRET_KEY = '6WDFSNTYXH'
client_id= f'{APP_ID}-{APP_TYPE}'

FY_ID = "XS00790"  # Your fyers ID
APP_ID_TYPE = "2"  # Keep default as 2, It denotes web login
TOTP_KEY = "ASURHDP3G4VJXITDALAKMZZZVIE5L5YU"  # TOTP secret is generated when we enable 2Factor TOTP from myaccount portal
PIN = "1236"  # User pin for fyers account

REDIRECT_URI = "https://127.0.0.1/"  # Redirect url from the app.
factor2 = pyotp.TOTP(TOTP_KEY).now()
# print(factor2)
max_loss_per_trade=50
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
	request_key = send_otp_result[1]
	verify_totp_result = verify_totp(request_key=request_key, totp=pyotp.TOTP(TOTP_KEY).now())
	if verify_totp_result[0] != SUCCESS:
		print(f"verify_totp_result failure - {verify_totp_result[1]}")
		time.sleep(1)
	else:
		# print(f"verify_totp_result success {verify_totp_result}")
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

def get_ltp(stock_symbol):
    try:
        symbol = "NSE:" + stock_symbol + "-EQ"
        ltp = frontendltp.WSgetLtp(symbol)
    except Exception as e:
        print(f"{stock_symbol} :{e}")
    return ltp


session.set_token(auth_code)
response = session.generate_token()
access_token= response["access_token"]
# print(access_token)

fyers = fyersModel.FyersModel(client_id=client_id, token=access_token, log_path=os.getcwd())
print(fyers.get_profile())
traded_stocks = []

watchlist = ["ADANIENT", "ADANIPORTS", "ASIANPAINT", "AXISBANK", "BAJAJ-AUTO", "BAJFINANCE", "BAJAJFINSV", "BPCL", "BHARTIARTL", "BRITANNIA", "CIPLA", "COALINDIA", "DRREDDY", "EICHERMOT", "GRASIM", "HCLTECH", "HDFCBANK", "HDFCLIFE", "HEROMOTOCO", "HINDALCO", "HINDUNILVR", "ICICIBANK", "IOC", "INDUSINDBK", "INFY", "ITC", "JSWSTEEL", "KOTAKBANK", "LT", "MARUTI", "NESTLEIND", "NTPC", "ONGC", "POWERGRID", "RELIANCE", "SHREECEM", "SBIN", "SUNPHARMA", "TCS", "TATAMOTORS", "TATASTEEL", "TATACONSUM", "TECHM", "TITAN", "ULTRACEMCO", "UPL", "WIPRO", "ZEEL"]


exchange = "NSE"
eq = "EQ"
max_no_of_trades=5
while True:
	curr_time=datetime.now().time().strftime("%H:%M:%S")
	if(curr_time>="09:45" and curr_time<="15:15"):
		for name in watchlist:

			datal = {"symbols":f"{exchange}:{name}-{eq}"}#,"ohlcv_flag":"1"}
			Ltp = float(get_ltp(name))
			# print(Ltp)
			try:
				from_datetime = datetime.now() - timedelta(hours=1)     # From last & days
				to_datetime = datetime.now().strftime('%Y-%m-%d')
				data = {"symbol":f"{exchange}:{name}-{eq}","resolution":"5","date_format":"1","range_from":from_datetime.strftime('%Y-%m-%d'), "range_to":to_datetime,"cont_flag":"1"}
				nx = fyers.history(data)
				# print(nx)
				cols = ['datetime','open','high','low','close','volume']
				df = pd.DataFrame.from_dict(nx['candles'])
				# df = pd.DataFrame(nx)
				df.columns = cols
				df['datetime'] = pd.to_datetime(df['datetime'],unit = "s")
				df['datetime'] = df['datetime'].dt.tz_localize('utc').dt.tz_convert('Asia/Kolkata')
				df['datetime'] = df['datetime'].dt.tz_localize(None)
				df = df.set_index('datetime')
				print(f"scanning in ",name)
			except Exception as e:
				print("error in data fetching")
			# print(df)
			# import pandas_ta as ta
			df['vwap'] = ta.vwap(df['high'], df['low'], df['close'], df['volume']).round(2)#,anchor ='M')

			df['percnt_buy'] = round((df['vwap']/df['low']-1)*100, 2)
			df['percnt_sell'] = round((df['vwap']/df['high']-1)*100, 2)
			# print(gap)

			positive_signal = (df['close'][0] >= df['vwap'][0]) and (df['percnt_buy'][1] <= -0.03) and (df['percnt_buy'][2] <= -0.03) and (df['percnt_buy'][3] <= -0.03) and (df['percnt_buy'][4] <= -0.03) and (df['percnt_buy'][5] <= -0.03)  		

			negative_signal = (df['close'][0] <= df['vwap'][0]) and (df['percnt_sell'][1] >= 0.03) and (df['percnt_sell'][2] >= 0.03) and (df['percnt_sell'][3] >= 0.03) and (df['percnt_sell'][4] >= 0.03) and (df['percnt_sell'][5] >= 0.03) 		

			final_buy = (df['low'][-1] <= df['vwap'][-1]) and (df['close'][-1] >= df['vwap'][-1]) and (df['high'][-1] >= Ltp) or (df['low'][-2] <= df['vwap'][-2]) and (df['close'][-2] >= df['vwap'][-2]) and (df['high'][-2] >= Ltp) or (df['low'][-3] <= df['vwap'][-3]) and (df['close'][-3] >= df['vwap'][-3]) and (df['high'][-3] >= Ltp) or (df['low'][-4] <= df['vwap'][-4]) and (df['close'][-4] >= df['vwap'][-4]) and (df['high'][-4] >= Ltp)

			final_sell = (df['high'][-1] >= df['vwap'][-1]) and (df['close'][-1] <= df['vwap'][-1]) and (df['low'][-1] >= Ltp) or (df['high'][-2] >= df['vwap'][-2]) and (df['close'][-2] <= df['vwap'][-2]) and (df['low'][-2] >= Ltp) or (df['high'][-3] >= df['vwap'][-3]) and (df['close'][-3] <= df['vwap'][-3]) and (df['low'][-3] >= Ltp) or (df['high'][-4] >= df['vwap'][-4]) and (df['close'][-4] <= df['vwap'][-4]) and (df['low'][-4] >= Ltp)

			#calulation_start_from_here!!
			def compare(a, b):
				if (a < b):
					# print(a)
					return (a) #- (a < b)
				else: 
					return(b)
				##calculating_diff
			high_candle=df['high'].iloc[-1]
			low_candle=df['low'].iloc[-1]

			num1_sell = Ltp
			num2_sell = df['high'].iloc[-1]
			if num1_sell > num2_sell:
				diff_sell = (num1_sell - num2_sell).round(1)
			else:
				diff_sell = (num2_sell - num1_sell).round(1)
			num1_buy = Ltp
			num2_buy = df['low'].iloc[-1]
			if num1_buy > num2_buy:
				diff_buy = (num1_buy - num2_buy).round(1)
			else:
				diff_buy = (num2_buy - num1_buy).round(1)
			
			# gap = round((openx/df.close-1)*100, 2)
			buy_target = round(Ltp*0.01, 1)#.iloc[-1]
			buy_stoploss_stop = round(Ltp*0.01, 1)#.iloc[-1]
			sell_target = round(Ltp*0.01, 1)#.iloc[-1]
			sell_stoploss_stop = round(Ltp*0.01, 1)#.iloc[-1]
			buy_stoploss = compare(a=buy_stoploss_stop, b=diff_buy)
			sell_stoploss = compare(a=sell_stoploss_stop, b=diff_sell)
			capital = 5000
			qty = int(capital/Ltp)



			#condition start from here!!!

			# if (df['close'][0] >= df['vwap'][0]) and (df['percnt_buy'][1] <= -0.03) and (df['percnt_buy'][2] <= -0.03) and (df['percnt_buy'][3] <= -0.03) and (df['percnt_buy'][4] <= -0.03) and (df['percnt_buy'][5] <= -0.03): #and (df['high'][-1] >= df['vwap'][-1]):
			# 	print(f"buy in.......................", name)

			# if (df['close'][0] <= df['vwap'][0]) and (df['percnt_sell'][1] >= 0.03) and (df['percnt_sell'][2] >= 0.03) and (df['percnt_sell'][3] >= 0.03) and (df['percnt_sell'][4] >= 0.03) and (df['percnt_sell'][5] >= 0.03): #and (df['high'][-55] >= df['vwap'][-55]) and (df['close'][-55] <= df['vwap'][-55]):
			# 	print(f"sell in......................", name)

			if (positive_signal) and (final_buy) and (name not in traded_stocks) and (len(traded_stocks) <= max_no_of_trades):

				data = {
						"symbol":f"{exchange}:{name}-{eq}",
						"qty":1,#round(max_loss_per_trade/(high_candle-low_candle)),
						"type":2,
						"side":1,
						"productType":"BO",
						"limitPrice":0,
						"stopPrice":0,
						"validity":"DAY",
						"disclosedQty":0,
						"offlineOrder":"False",
						"stopLoss":buy_stoploss,
						"takeProfit":buy_target
						}                              ## This is a sample example to place a limit order you can make the further changes based on your requriements 
				print(fyers.place_order(data))
				print(f"buy in.......................", name)

			if (negative_signal) and (final_sell) and (name not in traded_stocks) and (len(traded_stocks) <= max_no_of_trades):

				data = {
						"symbol":f"{exchange}:{name}-{eq}",
						"qty":1,#round(max_loss_per_trade/(high_candle-low_candle)),
						"type":2,
						"side":-1,
						"productType":"BO",
						"limitPrice":0,
						"stopPrice":0,
						"validity":"DAY",
						"disclosedQty":0,
						"offlineOrder":"False",
						"stopLoss":sell_stoploss,
						"takeProfit":sell_target
						}                              ## This is a sample example to place a limit order you can make the further changes based on your requriements 
				print(fyers.place_order(data))
				print(f"sell in......................", name)
			time.sleep(1)
		
	else:
		print(f"Waiting for timings")
		time.sleep(1)


		# df.to_csv("VWAP_CHECK.csv", index=True)
		# print(df)
		# pdb.set_trace()







###CHATGPT API KEY:- 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

# say LTP is 100 
# your buy SL is 80 
 
# then absSL is 20

# now if risk per trade is 10 then 

# stoploss_buy = lastclose - stoploss_buy  
# quantity = floor(max(1, (risk_per_trade/stoploss_buy))

# print(quantity)
