
import requests
import configparser
from localization import t
# url = "http://localhost:8000/v1/chat/completions"

parser=configparser.ConfigParser()
parser.read('config.ini',encoding='utf8')
url=parser['general']['server_url']
model=parser['general']['modelname']
print(url)
print(model)

messages=[{"role": "user", "content": input(t("test.input_prompt"))}]
while True:
    payload = {
        "model": model,
        "messages": messages
    }
    

    response = requests.post(url, json=payload)


    if response.status_code == 200:
        data = response.json()
        reply = data["choices"][0]["message"]["content"]
        print(t("test.model_reply"))
        print(reply)
        messages.append({"role": "assistant", "content": reply})
        messages.append({"role": "user", "content": input(t("test.input_prompt"))})
    else:
        print(f'{t("test.request_failed")}: {response.status_code}')
        print(response.text)
