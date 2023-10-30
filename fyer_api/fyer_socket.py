from fyers_api import fyersModel,accessToken
import os, datetime
from fyers_api.Websocket import ws
import threading
from flask import Flask, request
import webbrowser
# from fyerscred import *
from nsepython import *
import calendar
from datetime import timedelta
import pyotp
from urllib.parse import parse_qs,urlparse


app = Flask(__name__)

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

	
	return access_token


#### Generate an authcode and then make a request to generate an accessToken (Login Flow)
APP_ID =  "T6QAO808F1-100"## app_secret key which you got after creating the app
grant_type = "authorization_code"  ## The grant_type always has to be "authorization_code"
response_type = "code"  ## The response_type always has to be "code"
state = "sample"  ##  The state field here acts as a session manager. you will be sent with the state field after successfull generation of auth_code


stocklist = []  # BANKNIFTY OR NIFTY
strikeList = []
ltpDict = {}

data_type = "symbolData"
run_background = False
live_data = {}

clock = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
rundate = datetime.datetime.now().strftime("%Y-%m-%d")
logpath = os.getcwd()
logfilename = logpath + "websocketsubscribe" + clock + ".csv"


@app.route('/')
def hello_world():
    return 'Hello World-BankNifty'


@app.route('/ltp')
def WSgetLtp():
    # global ltpDict
    # print(live_data)
    ltp = -1
    # instrumet = request.args.get('NSE:SBIN-EQ')
    try:
        # ltp = ltpDict[instrumet]
        ltp = live_data
    except Exception as e:
        print("EXCEPTION occured while getting ltpDict()")
        print(e)
    return str(ltp)


def startServer():
    print("Inside startServer()")
    # app.run()


def findStrikePriceATM():
    print("\n Creating scrip list to stream LTP ======> \n")
    global kc 
    global clients
    global SL_percentage
    print("\tStock names:", stocklist)

    # strikeList.append("NSE:NIFTY50-INDEX")
    # strikeList.append("NSE:BAJFINANCE-EQ")
    # strikeList.append("NSE:NIFTY23JANFUT")
    watchlist = ["ADANIENT", "ADANIPORTS", "ASIANPAINT", "AXISBANK", "BAJAJ-AUTO", "BAJFINANCE", "BAJAJFINSV", "BPCL", "BHARTIARTL", "BRITANNIA", "CIPLA", "COALINDIA", "DRREDDY", "EICHERMOT", "GRASIM", "HCLTECH", "HDFCBANK", "HDFCLIFE", "HEROMOTOCO", "HINDALCO", "HINDUNILVR", "ICICIBANK", "IOC", "INDUSINDBK", "INFY", "ITC", "JSWSTEEL", "KOTAKBANK", "LT", "MARUTI", "NESTLEIND", "NTPC", "ONGC", "POWERGRID", "RELIANCE", "SHREECEM", "SBIN", "SUNPHARMA", "TCS", "TATAMOTORS", "TATASTEEL", "TATACONSUM", "TECHM", "TITAN", "ULTRACEMCO", "UPL", "WIPRO", "ZEEL"]
    # # ######################################################
    # # # FINDING ATM
    for stock in watchlist:
        strikeList.append(f"NSE:{stock}-EQ")
		
    print(strikeList)

symbol = strikeList


def custom_message(msg):
    # print("new msg..")
    global live_data
    for symbol_data in msg:
        live_data[symbol_data['symbol']] = {"LTP": symbol_data['ltp']}

def subscribe_new_symbol(symbol_list):
    global niftyfyersSocket, data_type
    niftyfyersSocket.subscribe(symbol=symbol_list, data_type=data_type)

print("\nGood Morning,Begin with Login Process===>>>>")
print("\nTime:", clock)

accesstoken = login()
global fyers,niftyfyersSocket
fyers = fyersModel.FyersModel(client_id=APP_ID, token=accesstoken, log_path=logpath)
print(fyers.get_profile())

ws_access_token = f"{APP_ID}:{accesstoken}"
niftyfyersSocket = ws.FyersSocket(access_token=ws_access_token, run_background=False, log_path=logpath)

findStrikePriceATM()

niftyfyersSocket.websocket_data = custom_message

threading.Thread(target=subscribe_new_symbol, args=(symbol,)).start()
app.run(host='127.0.0.1', port=5050)


