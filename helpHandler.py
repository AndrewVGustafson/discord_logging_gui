import requests, json


post_endpoint = "http://127.0.0.1:5000/postHelp"


def send_feedback(message):
    headers = {"Content-Type":"application/json"}
                
    r = requests.post(post_endpoint, data=message, headers=headers)
    response2 = json.loads(r.text)
    server_reply = response2['data']
    # print(server_reply)
    if server_reply == "Incorrect client key":
        return "Incorrect client key"
    elif server_reply == "Payload sent successfully":
        return "Feedback Sent"
    elif server_reply == "Error sending help payload":
        return "Error2"
    else:
        return "Error"
