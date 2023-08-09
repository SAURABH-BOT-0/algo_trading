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

##login_function_start_from_here

APP_ID =  "0YW29QZVF0" # App ID from myapi dashboard is in the form appId-appType. Example - EGNI8CE27Q-100, In this code EGNI8CE27Q will be APP_ID and 100 will be the APP_TYPE
APP_TYPE = "100"
SECRET_KEY = 'R4FV65PN0V'
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



session.set_token(auth_code)
response = session.generate_token()
access_token= response["access_token"]
# print(access_token)

fyers = fyersModel.FyersModel(client_id=client_id, token=access_token, log_path=os.getcwd())
print(fyers.get_profile())
traded_stocks = []


watchlist = ['ABB', 'ABBOTINDIA', 'ABCAPITAL', 'ABFRL', 'ACC', 'ADANIENT', 'ADANIGREEN', 'ADANIPORTS', 'ADANITRANS', 'ALKEM', 'AMBUJACEM', 'APOLLOHOSP', 'ASHOKLEY', 'ASIANPAINT', 'ASTRAL', 'AUBANK', 'AUROPHARMA', 'AWL', 'AXISBANK', 'BAJAJ-AUTO', 'BAJAJFINSV', 'BAJAJHLDNG', 'BAJFINANCE', 'BALKRISIND', 'BANDHANBNK', 'BANKBARODA', 'BANKINDIA', 'BATAINDIA', 'BEL', 'BERGEPAINT', 'BHARATFORG', 'BHARTIARTL', 'BHEL', 'BIOCON', 'BPCL', 'BRITANNIA', 'CANBK', 'CHOLAFIN', 'CIPLA', 'CLEAN', 'COALINDIA', 'COFORGE', 'COLPAL', 'CONCOR', 'COROMANDEL', 'CROMPTON', 'CUMMINSIND', 'DALBHARAT', 'DEEPAKNTR', 'DELHIVERY', 'DIVISLAB', 'DIXON', 'DLF', 'DMART', 'DRREDDY', 'EICHERMOT', 'EMAMILTD', 'ESCORTS', 'FEDERALBNK', 'FORTIS', 'GAIL', 'GLAND', 'GODREJCP', 'GODREJPROP', 'GRASIM', 'GSPL', 'GUJGASLTD', 'HAL', 'HAVELLS', 'HCLTECH', 'HDFC', 'HDFCAMC', 'HDFCBANK', 'HDFCLIFE', 'HEROMOTOCO', 'HINDALCO', 'HINDPETRO', 'HINDUNILVR', 'HINDZINC', 'HONAUT', 'ICICIBANK', 'ICICIGI', 'ICICIPRULI', 'IDEA', 'IDFCFIRSTB', 'IEX', 'IGL', 'INDHOTEL', 'INDIAMART', 'INDIANB', 'INDIGO', 'INDUSINDBK', 'INDUSTOWER', 'INFY', 'IOC', 'IPCALAB', 'ISEC', 'ITC', 'JINDALSTEL', 'JSWENERGY', 'JSWSTEEL', 'JUBLFOOD', 'KOTAKBANK', 'L&TFH', 'LALPATHLAB', 'LAURUSLABS', 'LICHSGFIN', 'LICI', 'LT', 'LTIM', 'LTTS', 'LUPIN', 'M&M', 'M&MFIN', 'MARICO', 'MARUTI', 'MAXHEALTH', 'MFSL', 'MOTHERSON', 'MPHASIS', 'MRF', 'MSUMI', 'MUTHOOTFIN', 'NAM-INDIA', 'NATIONALUM', 'NAUKRI', 'NAVINFLUOR', 'NESTLEIND', 'NTPC', 'NYKAA', 'OBEROIRLTY', 'OFSS', 'OIL', 'ONGC', 'PAGEIND',  'PERSISTENT', 'PETRONET', 'PFC', 'PGHH', 'PIDILITIND', 'PIIND', 'PNB', 'POLICYBZR', 'POLYCAB', 'POONAWALLA', 'POWERGRID', 'PRESTIGE', 'RAMCOCEM', 'RECLTD', 'RELIANCE', 'SAIL', 'SBICARD', 'SBILIFE', 'SBIN', 'SHREECEM', 'SIEMENS', 'SONACOMS', 'SRF', 'SUNPHARMA', 'SUNTV', 'SYNGENE', 'TATACHEM', 'TATACOMM', 'TATACONSUM', 'TATAELXSI', 'TATAMOTORS', 'TATAPOWER', 'TATASTEEL', 'TCS', 'TECHM', 'TITAN', 'TORNTPHARM', 'TORNTPOWER', 'TRENT', 'TRIDENT', 'TTML', 'UBL', 'ULTRACEMCO', 'UNIONBANK', 'UPL', 'VBL', 'VEDL', 'VOLTAS', 'WHIRLPOOL', 'WIPRO', 'YESBANK', 'ZEEL', 'ZOMATO', 'ZYDUSLIFE']

exchange = "NSE"
eq = "EQ"

order_placed = "no"

while True:
	now = datetime.now()
	current_time = now.strftime("%H:%M:%S")

	if(current_time >= "09:16:05"):
		# print("lopp scan start !!")
	
		for name in watchlist:

			# symbol = 'NSE:NIFTY50-INDEX'
			# print(fyers.quotes({"symbols":f"{exchange}:{name}-{eq}"}))
			data = {"symbols":f"{exchange}:{name}-{eq}"}#,"ohlcv_flag":"1"}
			Ltp = fyers.quotes(data) ['d'] [0] ['v'] ['lp']

			from_datetime = datetime.now() - timedelta(minutes=20) ##this is for minutes
			from_datetimeday = datetime.now() - timedelta(days=4)   ##this is for days
			to_datetime = datetime.now().strftime('%Y-%m-%d')
			# data = {"symbol":f"{exchange}:{name}-{eq}","resolution":"5","date_format":"1","range_from":"2022-12-15", "range_to":to_datetime,"cont_flag":"1"}
			# nx = fyers.history(data)	
			# cols = ['datetime','open','high','low','close','volume']
			# df = pd.DataFrame.from_dict(nx['candles'])
			# df.columns = cols
			# df['datetime'] = pd.to_datetime(df['datetime'],unit = "s")
			# df['datetime'] = df['datetime'].dt.tz_localize('utc').dt.tz_convert('Asia/Kolkata')
			# df['datetime'] = df['datetime'].dt.tz_localize(None)
			# df = df.set_index('datetime')
			# print(df)
			## calclulating_days_high_low_here!!!
			try :
				dataday = {"symbol":f"{exchange}:{name}-{eq}","resolution":"240","date_format":"1","range_from":from_datetimeday.strftime('%Y-%m-%d'), "range_to":to_datetime,"cont_flag":"1"}
				nxday = fyers.history(dataday)	
				cols = ['datetime','open','high','low','close','volume']
				dfday = pd.DataFrame.from_dict(nxday['candles'])
				dfday.columns = cols
				dfday['datetime'] = pd.to_datetime(dfday['datetime'],unit = "s")
				dfday['datetime'] = dfday['datetime'].dt.tz_localize('utc').dt.tz_convert('Asia/Kolkata')
				dfday['datetime'] = dfday['datetime'].dt.tz_localize(None)
				dfday = dfday.set_index('datetime')
				# print(dfday)
			except Exception as e:
 
				print("error in data fecting")

			##calculating_for_1_min_data
			try:
				datamin = {"symbol":f"{exchange}:{name}-{eq}","resolution":"1","date_format":"1","range_from":from_datetime.strftime('%Y-%m-%d'), "range_to":to_datetime,"cont_flag":"1"}
				nxmin = fyers.history(datamin)	
				cols = ['datetime','open','high','low','close','volume']
				dfmin = pd.DataFrame.from_dict(nxmin['candles'])
				dfmin.columns = cols
				dfmin['datetime'] = pd.to_datetime(dfmin['datetime'],unit = "s")
				dfmin['datetime'] = dfmin['datetime'].dt.tz_localize('utc').dt.tz_convert('Asia/Kolkata')
				dfmin['datetime'] = dfmin['datetime'].dt.tz_localize(None)
				dfmin = dfmin.set_index('datetime')
			except Exception as e:
				print("error in data fecting")
 
			# print(dfmin)
			print(f"scanning in: {name}")
			#startagy strat from here!!
			##below_only_calculate_5min!!!
			# openx = df['open']
			# high = df['high']
			# low = df['low']
			# prev_close = df['close']
			##below_only_calculate_1min!!!
			openxmin = dfmin['open']
			highmin = dfmin['high']
			lowmin = dfmin['low']
			prev_closemin = dfmin['close']
			##below_only_calculate_240min
			openxday = dfday['open']
			highday = dfday['high']
			lowday = dfday['low']
			prev_close_day = dfday['close']
			# df['close'] = df.close.shift(1)
			# print(Ltp)
			def compare(a, b):
				if (a < b):
					# print(a)
					return (a) #- (a < b)
				else: 
					return(b)
			##calculating_diff
			num1_sell = Ltp
			num2_sell = dfmin['high'].iloc[0]
			if num1_sell > num2_sell:
				diff_sell = (num1_sell - num2_sell).round(1)
			else:
				diff_sell = (num2_sell - num1_sell).round(1)
			num1_buy = Ltp
			num2_buy = dfmin['low'].iloc[0]
			if num1_buy > num2_buy:
				diff_buy = (num1_buy - num2_buy).round(1)
			else:
				diff_buy = (num2_buy - num1_buy).round(1)
		
			# gap = round((openx/df.close-1)*100, 2)
			buy_target = round(Ltp*0.01, 1)#.iloc[-1]
			buy_stoploss_stop = round(Ltp*0.01, 1)#.iloc[-1]
			sell_target = round(Ltp*0.01, 1)#.iloc[-1]
			sell_stoploss_stop = round(Ltp*0.01, 1)#.iloc[-1]
			capital = 5000
			qty = int(capital/Ltp)#.iloc[-1]
			# print(qty)
			buy_stoploss = compare(a=buy_stoploss_stop, b=diff_buy)
			sell_stoploss = compare(a=sell_stoploss_stop, b=diff_sell)
			# print(buy_stoploss)
			# print(diff)

			# # #condition start from here!!!
			if (highday[-3] <= openxday[-1]) and (highday[-2] <= openxday[-1]) and (openxmin[0] == lowmin[0]) and (highmin[0] <= Ltp) and (name not in traded_stocks):
				data = {
						"symbol":f"{exchange}:{name}-{eq}",
						"qty":qty,
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
				traded_stocks.append(name)
				print(f"buy in up side: {name}")
				order_placed = "yes"
			if (highday[-3] <= openxday[-1]) and (highday[-2] <= openxday[-1]) and (openxmin[0] == highmin[0]) and (lowmin[0] >= Ltp) and (name not in traded_stocks):
				data = {
						"symbol":f"{exchange}:{name}-{eq}",
						"qty":qty,
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
				print(f"sell in up side {name}")
				traded_stocks.append(name)
				order_placed = "yes"

			if (lowday[-3] >= openxday[-1]) and (lowday[-2] >= openxday[-1]) and (openxmin[0] == lowmin[0]) and (highmin[0] <= Ltp) and (name not in traded_stocks):
				data = {
						"symbol":f"{exchange}:{name}-{eq}",
						"qty":qty,
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
				traded_stocks.append(name)
				print(f"buy in down side {name}")
				order_placed = "yes"
			if (lowday[-3] >= openxday[-1]) and (lowday[-2] >= openxday[-1]) and (openxmin[0] == highmin[0]) and (lowmin[0] >= Ltp) and (name not in traded_stocks):
				data = {
						"symbol":f"{exchange}:{name}-{eq}",
						"qty":qty,
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
				print(f"sell in down side {name}")
				traded_stocks.append(name)
				order_placed = "yes"
			# time.sleep(0.60)
				##condition_exit_here!!!
