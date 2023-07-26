from smartapi import SmartConnect
import requests
import pandas as pd
import yaml
import time
import warnings
import os
import pyotp
import pdb
from datetime import datetime,date
import math


token = 'CX523CSW6I5SX6P2RHW3R3N2Y4' 
factor2 = pyotp.TOTP(token).now()
obj=SmartConnect(api_key="SyWI0USj")     
data = obj.generateSession("R483803","1989", factor2)  
refreshToken= data['data']['refreshToken']
feedToken=obj.getfeedToken()
userProfile= obj.getProfile(refreshToken)
print(userProfile)
 

url = 'https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json'
data = requests.get(url).json()
token_df = pd.DataFrame.from_dict(data)
token_df['expiry'] = pd.to_datetime(token_df['expiry']).dt.date
token_df = token_df.astype({'strike': float})
token_df.to_csv('token_df.csv', index=False)
 

with open('angle_trade.yaml') as f:
	dataMap = yaml.safe_load(f)

parameters = dataMap["Parameters2"]
upper_level = parameters['upper_level']['level']
lower_level = parameters['lower_level']['level']
target_up_points = parameters['upper_target']
target_lo_points = parameters['lower_target']
sl_up_points = parameters['sl_upper']
sl_lo_points = parameters['sl_lower']
strike_ce = parameters['strike_ce']
strike_pe = parameters['strike_pe']
qty = parameters['Qty']
expiry = parameters['expiry']
 

sl_upper_n, sl_lower_n = 0, 0
target_upper_n, target_lower_n = 0, 0

sl_upper_b, sl_lower_b = 0, 0
target_upper_b, target_lower_b = 0, 0
bn_ltp, upper_ltp, lower_ltp = 0, 0, 0
order = 0
ce_order_placed = "no"
pe_order_placed = "no"

threshold = 1

traded_stocks = []
ce_nifty = []
pe_nifty = []
ce_banknifty = []
pe_banknifty = []
nifty_ce = []
banknifty_ce = []
nifty_pe = []
banknifty_pe = []
watchlist = ['NIFTY', 'BANKNIFTY']
watchlist1 = tuple(watchlist)
for_atm = {watchlist1: {'NIFTY': 50, 'BANKNIFTY': 100}}

 
while True:
	for name in watchlist:
		upper_limit = upper_level[name]
		lower_limit = lower_level[name]
		target_up = target_up_points[name]
		target_lo = target_lo_points[name]
		sl_up = sl_up_points[name]
		sl_lo = sl_lo_points[name]
		strike_c = strike_ce[name]
		strike_p = strike_pe[name]
		Qty = qty[name]
		atm = for_atm[watchlist1][name]

		# expiry_day = date(2023, 6, 8)
		expiry_day = datetime.strptime(expiry, '%Y-%m-%d').date()
		symbol = name#'NIFTY'

		filtered_df = token_df[
			(token_df['name'] == symbol) &
			(token_df['instrumenttype'] == 'OPTIDX') &
			(token_df['expiry'] == expiry_day)
		]

		instruments = pd.DataFrame.from_records(data)
		indexLtp = obj.ltpData('NSE', symbol, instruments[instruments.symbol == symbol].iloc[0]['token'])['data']['ltp']
		print(indexLtp)
		# print(filtered_df)
		def getTokenInfo (symbol, exch_seg ='NSE',instrumenttype='OPTIDX',strike_price = '',pe_ce = 'CE',expiry_day = None):
			df = filtered_df
			strike_price = strike_price*100
			if exch_seg == 'NSE':
				eq_df = df[(df['exch_seg'] == 'NSE') ]
				return eq_df[eq_df['name'] == symbol]
			elif exch_seg == 'NFO' and ((instrumenttype == 'FUTSTK') or (instrumenttype == 'FUTIDX')):
				return df[(df['exch_seg'] == 'NFO') & (df['instrumenttype'] == instrumenttype) & (df['name'] == symbol)].sort_values(by=['expiry'])
			elif exch_seg == 'NFO' and (instrumenttype == 'OPTSTK' or instrumenttype == 'OPTIDX'):
				return df[(df['exch_seg'] == 'NFO') & (df['expiry']==expiry_day) &  (df['instrumenttype'] == instrumenttype) & (df['name'] == symbol) & (df['strike'] == strike_price) & (df['symbol'].str.endswith(pe_ce))].sort_values(by=['expiry'])

		ATMStrike_ce = math.ceil(indexLtp/atm)*atm+strike_c*atm
		ATMStrike_pe = math.ceil(indexLtp/atm)*atm+strike_p*atm	

		ce_strike = getTokenInfo(symbol,'NFO','OPTIDX',ATMStrike_ce,'CE',expiry_day).iloc[0]		 
		pe_strike = getTokenInfo(symbol,'NFO','OPTIDX',ATMStrike_pe,'PE',expiry_day).iloc[0]

#condition_start_from_here!!

		if order == 0 and indexLtp >= upper_limit and name not in traded_stocks:     
			print(f"{name} Upper range reached.")
			orderparams = {
				"variety": "NORMAL",
				"tradingsymbol": ce_strike.symbol,
				"symboltoken": ce_strike.token,
				"transactiontype": "BUY",
				"exchange": "NFO",
				"ordertype": "MARKET",
				"producttype": "INTRADAY",
				"duration": "DAY",
				"quantity": Qty
			}
			orderId = obj.placeOrder(orderparams)
			print("The order id is: {}".format(orderId))
			ce_order_placed = "yes"
			traded_stocks.append(name)
			if (ce_strike.lotsize == '50'):
				ce_nifty.append(ce_strike)
			else:
				ce_banknifty.append(ce_strike)	 
			if (name == 'NIFTY'):		             
				target_upper_n = target_up
				sl_upper_n = sl_up
			else:
				target_upper_b = target_up
				sl_upper_b = sl_up
		if (name == 'NIFTY'):
			if (indexLtp - sl_upper_n) <= threshold or (indexLtp - target_upper_n) <= threshold and name not in nifty_pe:
				print("Nifty Upper range exit reached.")
				orderparams = {
					"variety": "NORMAL",
					"tradingsymbol": ce_nifty[0]['symbol'],
					"symboltoken": ce_nifty[0]['token'],
					"transactiontype": "SELL",
					"exchange": "NFO",
					"ordertype": "MARKET",
					"producttype": "INTRADAY",
					"duration": "DAY",
					"quantity": Qty
				}
				orderId = obj.placeOrder(orderparams)
				print("The order id is: {}".format(orderId))
				nifty_pe.append(name)
		else:
			if indexLtp - sl_upper_b <= threshold or indexLtp - target_upper_b <= threshold and name not in banknifty_pe:
					print("Bank Nifty Upper range exit reached.")
					orderparams = {
						"variety": "NORMAL",
						"tradingsymbol": ce_banknifty[0]['symbol'],
						"symboltoken": ce_banknifty[0]['token'],
						"transactiontype": "SELL",
						"exchange": "NFO",
						"ordertype": "MARKET",
						"producttype": "INTRADAY",
						"duration": "DAY",
						"quantity": Qty
					}
					orderId = obj.placeOrder(orderparams)
					print("The order id is: {}".format(orderId))
					banknifty_pe.append(name)            

		if order == 0 and indexLtp <= lower_limit and name not in traded_stocks:     
			print(f"{name} Lower range reached.")
			orderparams = {
				"variety": "NORMAL",
				"tradingsymbol": pe_strike.symbol,
				"symboltoken": pe_strike.token,
				"transactiontype": "BUY",
				"exchange": "NFO",
				"ordertype": "MARKET",
				"producttype": "INTRADAY",
				"duration": "DAY",
				"quantity": Qty
			}
			orderId = obj.placeOrder(orderparams)
			print("The order id is: {}".format(orderId))
			pe_order_placed = "yes" 
			traded_stocks.append(name)
			if (pe_strike.lotsize == '50'):
				pe_nifty.append(pe_strike)
			else:
				pe_banknifty.append(pe_strike)	 
			if (name == 'NIFTY'):		             
				target_lower_n = target_lo
				sl_lower_n = sl_lo
			else:
				target_lower_b = target_lo
				sl_lower_b = sl_lo
		if (name == 'NIFTY'):
			if indexLtp - sl_lower_n <= threshold or indexLtp - target_lower_n <= threshold and name not in nifty_pe:
				print("Nifty Upper range exit reached.")
				orderparams = {
					"variety": "NORMAL",
					"tradingsymbol": pe_nifty[0]['symbol'],
					"symboltoken": pe_nifty[0]['token'],
					"transactiontype": "SELL",
					"exchange": "NFO",
					"ordertype": "MARKET",
					"producttype": "INTRADAY",
					"duration": "DAY",
					"quantity": Qty
				}
				orderId = obj.placeOrder(orderparams)
				print("The order id is: {}".format(orderId))
				nifty_pe.append(name)
		else:
			if indexLtp - sl_lower_b <= threshold or indexLtp - target_lower_b <= threshold and name not in banknifty_pe:
					print("Bank Nifty Upper range exit reached.")
					orderparams = {
						"variety": "NORMAL",
						"tradingsymbol": pe_banknifty[0]['symbol'],
						"symboltoken": pe_banknifty[0]['token'],
						"transactiontype": "SELL",
						"exchange": "NFO",
						"ordertype": "MARKET",
						"producttype": "INTRADAY",
						"duration": "DAY",
						"quantity": Qty
					}
					orderId = obj.placeOrder(orderparams)
					print("The order id is: {}".format(orderId))
					banknifty_pe.append(name)
