import requests

def send_msg(text):

    token = '5385920968:AAEKZ8-POw43vPVnQ7D_DY4EKTT4fIniTro'
    chat_id = '1390610836'#'1390610836',5030495451
    send_text = 'https://api.telegram.org/bot' + token +"/sendMessage" + "?chat_id=" + chat_id + "&text=" + text
    results = requests.get(send_text)

    # print(results.json())

send_msg("send_msg_done")

