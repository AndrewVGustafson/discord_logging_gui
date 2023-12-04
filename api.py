import json
from flask import Flask, jsonify, request
from flask_restful import Api, Resource
import time
from datetime import datetime
import requests
import secrets
import random
import threading
from dotenv import load_dotenv
import os

app = Flask(__name__)
api = Api(app)

discord_api_token = os.getenv('discord_api_token')
server_log_path = 'client_user_logs.txt'
blacklisted_users = [""]
approved_clients = ["v3.0", "v3.1", "v3.5", "v4.0"]
newest_client = "v4.0"
appRun = True


# String injection vulnerability patched  o(｀ω´ )o
def check_strings(args):
    forbiden_string = "\n"
    if forbiden_string in args:
        cleared_string = args.replace(forbiden_string, "") # maybe replace with something else but for now just space
        return cleared_string
    else:
        return args


def server_log(args):
    now = datetime.now()
    log_date = now.strftime("%m/%d/%Y")
    log_time = now.strftime("%I:%M:%S %p")
    # Make error handling
    with open(server_log_path, "a") as writeFile: # Remember to change path when uploading to server
        data = f"[{log_date} : {log_time}] - [{args}]\n"
        writeFile.write(data) # Remember to account for invalid or strange chars
        writeFile.close()


def verify_client(runReq, client_ver, userID, username, discriminator, appRun):
    if appRun:
        if runReq == "clientRun":
            if userID not in blacklisted_users:
                if client_ver in approved_clients:
                    return operable_payload
                else:
                    return "Invalid or outdated client version."
            else:
                return f"Requested user has been blacklisted: {username}#{discriminator} ({userID})"
        else:
            return "Invalid Client POST JSON."
    else:
        return inop_payload


def rotate_key():

    global generate_key
    def generate_key():
            global key
            key = secrets.token_urlsafe(random.randint(65, 70))
            log_key(key)

    def log_key(key):
        server_log_path = "session_key_logs.txt"
        now = datetime.now()
        log_date = now.strftime("%m/%d/%Y")
        log_time = now.strftime("%I:%M:%S %p")

        with open(server_log_path, 'a') as w:
            data = f"[{log_date}] : [{log_time}] - [KEY GENERATED] [KEY: {key}]\n"
            # print(key)
            # print("=========================================")
            # print("Key Generated")
            w.write(data)
            w.close()

    generate_key()

    while True:

        global refresh_iteration
        refresh_iteration = 300 # (5 min)

        while refresh_iteration:
            time.sleep(1)
            refresh_iteration -= 1

        generate_key()


class appState(Resource):
    def post(self):
        client_data = request.get_json()

        # print(client_data)

        global operable_payload, inop_payload
        operable_payload = {"appState": "enabled",
                            "sessionKey": key,
                            "sessionKeyExpire": refresh_iteration }
        inop_payload = {"appState": "disabled"}
        unknown_error = {"data": "An error has occurred when handling the client request and has rendered the app unable to run at this time."}

        runReq = check_strings(client_data['runRequest'])
        client_ver = check_strings(client_data['client'])
        userID = check_strings(client_data['userID'])
        username = check_strings(client_data['username'])
        discriminator = check_strings(client_data['discriminator'])
        timestamp = check_strings(client_data['timestamp'])

        server_log(f"Incoming Verify Request: Client Version: {client_ver} User: {username}#{discriminator} ({userID})")

        client_operable = verify_client(runReq, client_ver, userID, username, discriminator, appRun)
        if "appState" in client_operable:
            if operable_payload == client_operable:
                # print(client_operable)
                server_log(f"Verify Request Approved: Client Version: {client_ver} User: {username}#{discriminator} ({userID})")
                return jsonify(client_operable)

            elif inop_payload == client_operable:
                server_log(f"Verify Request Rejected - App Disabled - Client Version: {client_ver} User: {username}#{discriminator} ({userID})")
                return jsonify(client_operable)

            else:
                pass

        else:
            # All errors returned to client
            client_return = {"data": client_operable}
            if client_operable == "Invalid Client POST JSON.":
                server_log(f"Verify Request Rejected - Invalid JSON - Remote address: {request.remote_addr}")
                return jsonify(client_return)
            elif client_operable == f"Requested user has been blacklisted: {username}#{discriminator} ({userID})":
                server_log(f"Verify Request Rejected - Requested user has been Blacklisted - User: {username}#{discriminator} ({userID})")
                return jsonify(client_return)
            elif client_operable == "Invalid or outdated client version.":
                server_log(f"Verify Request Rejected - Invalid Client Version - Requested Client version: {client_ver}")
                return jsonify(client_return)
            else:
                server_log(f"FATAL ERROR WHEN HANDLING CLIENT ERROR RESPONSES")
                return jsonify(unknown_error)

api.add_resource(appState, "/verifyApp")



class FeedbackRecipients:
    def __init__(self, channel, user):
        self.channel = channel
        self.user = user

    def send_message(self, discord_api_token, success_payload, error_payload, timestamp, client_version, username, discriminator, userID, user_inquiry, remoteHostTZ):
        message = f"\n**INCOMING HELP REQUEST - {timestamp} ({remoteHostTZ}) **\nCLIENT VERSION: {client_version}\nUSER: {username}#{discriminator}\nUSER ID: {userID}\n\nINQUIRY: {user_inquiry}\n"
        headers = { "Authorization":"{}".format(discord_api_token),
                    "User-Agent":"myBotThing (http://some.url, v0.1)",
                    "Content-Type":"application/json", }
        payload = json.dumps ( {"content":message} )

        sent_to_dev_1 = False
        sent_to_dev_2 = False

        r = requests.post(f"https://discord.com/api/v7/channels/{Dev1.channel}/messages", headers=headers, data=payload)
        if str(Dev1.channel) in r.text:
            sent_to_dev_1 = True
            server_log(f"Help Request to Dev1 sent from User: {username}#{discriminator} ({userID})")
        else:
            server_log(f"Help Request to Dev1 could not be sent from User: {username}#{discriminator} ({userID})")
            return False

        r2 = requests.post(f"https://discord.com/api/v7/channels/{Dev2.channel}/messages", headers=headers, data=payload)
        if str(Dev2.channel) in r2.text:
            sent_to_dev_2 = True
            server_log(f"Help Request to Dev2 sent from User: {username}#{discriminator} ({userID})")
        else:
            server_log(f"Help Request to Dev2 could not be sent from User: {username}#{discriminator} ({userID})")
            return False

        if sent_to_dev_1 and sent_to_dev_2:
            return True
        else:
            return False

Dev1 = FeedbackRecipients(channel=os.getenv("dev1_channel"), user="Dev1")
Dev2 = FeedbackRecipients(channel=os.getenv("dev2_channel"), user="Dev2")


def verify_request(client_key):
    if client_key == key:
        return True
    else:
        return False


class submitHelp(Resource):
    def post(self):

        # REMEMBER TO LOG ALL ACTIONS TO SERVER LOGS

        success_payload = {"data": "Payload sent successfully"}
        error_payload = {"data": "Error sending help payload"} # *To one or more devs
        wrong_key = {"data": "Incorrect client key"}

        client_help_payload = request.get_json()

        # print(client_help_payload)

        # Need to clear all strinsg before using them
        client_key = check_strings(client_help_payload['Client Authorization'])
        timestamp = check_strings(client_help_payload['clientTimestampLocal'])
        client_version = check_strings(client_help_payload['clientVersion'])
        username = check_strings(client_help_payload['username'])
        discriminator = check_strings(client_help_payload['discriminator'])
        userID = check_strings(client_help_payload['userID'])
        user_inquiry = check_strings(client_help_payload['inquiry'])
        remoteHostTZ = check_strings(client_help_payload['hostTimeZone'])

        key_correct = verify_request(client_key)


        server_log(f"Incoming Help Request: Client Version: {client_version} User: {username}#{discriminator} ({userID})")

        if key_correct:
            message_sent = FeedbackRecipients.send_message(self, discord_api_token, success_payload, error_payload, timestamp, client_version, username, discriminator, userID, user_inquiry, remoteHostTZ)
            if message_sent:
                server_log(f"Help Request Sent - Client Version: {client_version} User: {username}#{discriminator} ({userID})")
                return jsonify(success_payload)
            else:
                return jsonify(error_payload)
        else:
            server_log(f"Help Request Rejected - Invalid Client Key - Client Version: {client_version} User: {username}#{discriminator} ({userID})")
            return jsonify(wrong_key)



api.add_resource(submitHelp, "/postHelp")


class getUpdate(Resource):
    def get(self):
        request_payload = request.get_json()
        needToUpdate = {"status": "update available",
                        "newestClient": newest_client}

        upToDate = {"status": "client up to date"}

        clientVersion = check_strings(request_payload['ClientVersion'])
        server_log(f"Incoming Update Request: Client Version {clientVersion}")
        # remember to log events to server
        if clientVersion:
            if clientVersion != newest_client:
                return jsonify(needToUpdate)
            elif clientVersion == newest_client:
                return jsonify(upToDate)
            else:
                return jsonify( {"data": "A server side error has occured"} )
        else:
            return jsonify( {"data": "Invalid request payload"} )


api.add_resource(getUpdate, "/update")


class clientTokenRefresh(Resource):
    def get(self):
        request_payload = request.get_json()

        request_clientVer = check_strings(request_payload['clientVersion'])

        # LOG INTERACTIONS

        if request_clientVer:
            return jsonify ( {"token": key,
                            "keyExperation": refresh_iteration} )


        else:
            return jsonify ( {"data": "ERROR: Invalid request payload"} )


api.add_resource(clientTokenRefresh, "/tokenRefresh")


class backendStatus(Resource):
    def get(self):
        return jsonify ( { "message": "Flask server operable",
                        "key": key} )

        # Remember to log return other stats as well


api.add_resource(backendStatus, "/backendStatus")


def configure():
    load_dotenv()

if __name__ == "__main__":
    configure()
    key_thread = threading.Thread(target=rotate_key)
    key_thread.start()
    generate_key()
    apptherad = threading.Thread(target=app.run(debug=True))
    apptherad.start()
