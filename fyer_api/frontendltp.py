import ast
import urllib,requests

def WSgetLtp(name):
    key=name
    try:
        #threading.Timer(1, printit).start()
        feed = urllib.request.urlopen('http://127.0.0.1:5050/ltp')
        # print(feed)
    except Exception as e:
        print(e)
    else:
        feeddata=str(feed.read())
        ltp=feeddata.strip('"b')
        x=ast.literal_eval(ltp)
    #print(x)
    #print(type(x))
        data=x.get(key)['LTP']
        return data

# print(WSgetLtp('NSE:ADANIENT-EQ'))