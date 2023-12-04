'''

Source code written in full by Andrew Gustafson and Ian Culbert - June 2022

'''
from PyQt5 import QtCore, QtWidgets, QtGui
from datetime import datetime
from time import sleep
from emoji import demojize
from unidecode import unidecode
import threading, webbrowser
import websocket, requests, json
import os, sys
from dotenv import load_dotenv

TOKEN = ""
outputList = []
debugList = []
eventList = []
fileCount = 0
clientVersion = "v4.0"
connectionLostCount = 0
api_base = "http://127.0.0.1:5000/"

# TODO
# Make it so when the main app window is closed and the debug is up, it stops the entire program and closes the debug window
# Make a password for the api that you can enter through the admin panel to enable/disable the app
# Make a catch statement if the token is a bot token, right now the app just crashes due to an unrecognized server return code which is saying that the submited token is a bot instead of a user
# Make error handling for no internet connection on primary requests
# Add time elapsed counter when logger is active
# Make client key system that server sends 

class HyperLinkLabel(QtWidgets.QLabel):
    def __init__(self, parent=None):
        super().__init__()
        self.setOpenExternalLinks(True)
        self.setParent(parent)

class ScrollLabel(QtWidgets.QScrollArea):
    def __init__(self, *message, **kwmessage):
        QtWidgets.QScrollArea.__init__(self, *message, **kwmessage) 
        self.setWidgetResizable(True)
        content = QtWidgets.QWidget(self)
        self.setWidget(content)
        lay = QtWidgets.QVBoxLayout(content)

        self.label = QtWidgets.QLabel(content)
        self.label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        self.label.setWordWrap(True)
        lay.addWidget(self.label)

    def setText(self, text):
        self.label.setText(text)


class Ui_HelpWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        self.setFixedSize(640, 580)
        self.setWindowTitle("Application Support")

        self.helpMessageLabel = QtWidgets.QLabel(self)
        self.helpMessageLabel.setGeometry(QtCore.QRect(20, -140, 600, 400))
        self.helpMessageLabel.setText("Welcome to the application support panel. Here, you can send the developers feedback for any new features, or any bugs you've encountered. Note that when your feedback is recieved, we will contact you regarding your feedback via the discord account currently being used in the application.")
        self.helpMessageLabel.setFont(QtGui.QFont("Arial", 11))
        self.helpMessageLabel.setWordWrap(True)

        self.feedbackInput = QtWidgets.QTextEdit(self)
        self.feedbackInput.setGeometry(QtCore.QRect(20, 230, 600, 270))

        self.sendFeedbackButton = QtWidgets.QPushButton(self)
        self.sendFeedbackButton.setGeometry(QtCore.QRect(19, 510, 602, 40))
        self.sendFeedbackButton.setText("Submit Feedback")
        self.sendFeedbackButton.clicked.connect(self.submit_feedback)

        self.cooldownLabel = QtWidgets.QLabel(self)
        self.cooldownLabel.setGeometry(QtCore.QRect(20, 210, 600, 20))
        self.cooldownLabel.setText("You can only submit one feedback message every 60 seconds.")

    def submit_feedback(self):
        from helpHandler import send_feedback
        feedback = self.feedbackInput.toPlainText()
        if feedback:
            timestamp = f"{log_date}-{log_time}"
            feedback_payload = json.dumps( {f"Client Authorization": sessionKey, 
                                            "clientTimestampLocal": timestamp, 
                                            "clientVersion": clientVersion, 
                                            "username": username, 
                                            "discriminator": discriminator, 
                                            "userID": user_id, 
                                            "inquiry": feedback, 
                                            "hostTimeZone": localTimeZone} )


            message_sent = send_feedback(message=feedback_payload)
            if message_sent == "Feedback Sent":
                cooldown_thread = threading.Thread(target=self.feedback_button_cooldown)
                cooldown_thread.start()
                console_log("FEEDBACK SENT")
            elif message_sent == "Incorrect client key":
                console_log("FEEDBACK COULD NOT BE SENT - INCORRECT CLIENT KEY")
                self.cooldownLabel.setText("[ERROR]: Feedback could not be sent - Incorrect client key") 
            elif message_sent == "Error2":
                console_log("FEEDBACK COULD NOT BE SENT - BACKEND ERROR")
                self.cooldownLabel.setText("[ERROR]: Feedback could not be sent - A Backend error occured when sending the feedback payload")
            else:
                console_log("FEEDBACK COULD NOT BE SENT - UNKNOWN ERROR")
                self.cooldownLabel.setText("[ERROR]: Feedback could not be sent - An unknown error occured")
            
        else:
            pass

    def feedback_button_cooldown(self):
        try:
            self.sendFeedbackButton.setDisabled(True)
            for i in range(60):
                self.cooldownLabel.setText(f"You have {60-i} seconds remaining until you can send your next feedback message")
                sleep(1)
            self.sendFeedbackButton.setDisabled(False)
            self.cooldownLabel.setText("You can only submit one feedback message every 60 seconds.")
        except RuntimeError:
            pass


class Ui_AccountLookupWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        self.setFixedSize(640, 580)
        self.centralWidget = QtWidgets.QWidget(self)
        self.setWindowTitle("User Lookup")
        
        self.useridTextInput = QtWidgets.QLineEdit(self)
        self.useridTextInput.setGeometry(QtCore.QRect(20, 40, 300, 20))

        self.userHelpMessageLabel = QtWidgets.QLabel(self)
        self.userHelpMessageLabel.setGeometry(QtCore.QRect(20, 0, 600, 40))
        self.userHelpMessageLabel.setText("Look up a user and find basic account information using the respective user's User ID.")
        self.userHelpMessageLabel.setFont(QtGui.QFont("Arial", 10))
        self.userHelpMessageLabel.setWordWrap(True)

        self.userIdSubmitButton = QtWidgets.QPushButton(self)
        self.userIdSubmitButton.setGeometry(QtCore.QRect(200, 65, 200, 50)) # Tweak dimensions just a bit
        self.userIdSubmitButton.setText("Search User")
        # self.userIdSubmitButton.setDisabled(True)
        self.userIdSubmitButton.clicked.connect(self.search_user_id)

        self.userAvatarInfoLabel = HyperLinkLabel(self)
        self.userAvatarInfoLabel.setGeometry(QtCore.QRect(20, 140, 600, 30))
        self.userAvatarInfoLabel.setText("Profile Picture Link: ")

        self.userInfoLabel = ScrollLabel(self)
        self.userInfoLabel.setGeometry(QtCore.QRect(20, 180, 600, 300))
        self.userInfoLabel.setText("User Information:")

    def search_user_id(self):
        # Make except for if invalid ID is passed through
        request_success_flag = False
        linkTemplate = "<a href={0}>{1}</a>"
        user_id2 = self.useridTextInput.text()
        headers = { "Authorization":"{}".format(TOKEN),
                    "User-Agent":"myBotThing (http://some.url, v0.1)",
                    "Content-Type":"application/json", }


        
        url = requests.get(f"https://discord.com/api/v9/users/{user_id2}", headers=headers)
        response = json.loads(url.text)
        # print(response)
        if response:
            request_success_flag = True
        else:
            request_success_flag = False
            pass

        
        if request_success_flag:
            try:
                username = response['username']
                avatarHash = response['avatar']
                discrim = response['discriminator']
                publicFlags = response['public_flags']

                avatarUrl = f"https://cdn.discordapp.com/avatars/{user_id2}/{avatarHash}.png?size=4096"

                self.userAvatarInfoLabel.setText(linkTemplate.format(avatarUrl, avatarUrl))
                self.userInfoLabel.setText(
                    f"Username: {username}#{discrim}\n"
                    f"Flags: {publicFlags}" 
                )
                # Unknown user return JSON - {'message': 'Unknown User', 'code': 10013}
                # if the requested user ID is not an int - {'code': 50035, 'errors': {'user_id': {'_errors': [{'code': 'NUMBER_TYPE_COERCE', 'message': 'Value "f" is not snowflake.'}]}}, 'message': 'Invalid Form Body'} (In this case I typed "f")

            except KeyError:
                if response["code"] == 10013 or 50035:
                    self.userInfoLabel.setText("Invalid User ID")
                    self.userAvatarInfoLabel.setText("Invalid User ID")
                    console_log("ERROR: INVALID USER ID; REQUEST FAILED")
                elif response["code"] == 0:
                    self.userInfoLabel.setText("Please Enter a User ID")
                    self.userAvatarInfoLabel.setText("Please Enter a User ID")
                    console_log("ERROR: NO USER ID GIVEN; REQUEST FAILED")

        else:
            self.userInfoLabel.setText("Invalid User ID")
            console_log("ERROR: UNABLE TO SEND REQUEST; REQUEST FAILED")

class Ui_eventLogWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        # Remember to store raw JSON and make buttons to save to txt file the raw JSON and the parsed data
        self.setFixedSize(640, 580)
        self.setWindowTitle("Event Logger")
        self.eventListLabel = ScrollLabel(self)
        self.eventListLabel.setGeometry(QtCore.QRect(20, 20, 600, 440))
        self.eventListLabel.setText("Event Logs:")
        event_label_thread = threading.Thread(target=self.update_event_label)
        event_label_thread.start()

    def update_event_label(self):
        while True:
            try:
                self.eventListLabel.setText("\n".join(eventList))
                sleep(0.5)
            except RuntimeError:
                sys.exit()


class Ui_DebugWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        
        # console_log("DEBUG WINDOW OPENED")
        self.setFixedSize(640, 580)
        self.centralwidget = QtWidgets.QWidget(self)

        self.setWindowTitle("Chat Logger Admin Panel")
        self.debugListLabel = ScrollLabel(self)
        self.debugListLabel.setGeometry(QtCore.QRect(20, 20, 600, 440))
        self.debugListLabel.setText("Debug Logs:")
        debug_label_thread = threading.Thread(target=self.update_debugListLabel)
        debug_label_thread.start()

        # self.enableAppButton = QtWidgets.QPushButton(self)
        # self.enableAppButton.setGeometry(QtCore.QRect(20, 480, 100, 60))
        # self.enableAppButton.setText("Enable app")

    def update_debugListLabel(self):
        while True:
            try:
                self.debugListLabel.setText("\n".join(debugList))
                sleep(0.5)
            except RuntimeError:
                sys.exit()


class Ui_MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Discord Chat Logger {clientVersion}")
        self.setFixedSize(740, 610)
        self.centralwidget = QtWidgets.QWidget(self)
        
        self.menubar = QtWidgets.QMenuBar(self)
        self.menubar.setGeometry(QtCore.QRect(0, 20, 800, 20))

        self.runLoggerButton = QtWidgets.QPushButton(self)
        self.runLoggerButton.setGeometry(QtCore.QRect(148, 540, 111, 51))
        self.runLoggerButton.setText("Run Logger")
        self.runLoggerButton.clicked.connect(self.run_logger)
        self.runLoggerButton.setDisabled(True)

        self.clearOutputButton = QtWidgets.QPushButton(self)
        self.clearOutputButton.setGeometry(QtCore.QRect(610, 540, 111, 51))
        self.clearOutputButton.setText("Clear Output")
        self.clearOutputButton.clicked.connect(self.clear_output)
        self.clearOutputButton.setDisabled(True)
        
        self.checkTokenButton = QtWidgets.QPushButton(self)
        self.checkTokenButton.setGeometry(QtCore.QRect(20, 540, 111, 51))
        self.checkTokenButton.setText("Check Token")
        self.checkTokenButton.clicked.connect(self.submit_token)

        self.exportButton = QtWidgets.QPushButton(self)
        self.exportButton.setGeometry(QtCore.QRect(483, 540, 111, 51))
        self.exportButton.setText("Export to Text File")
        self.exportButton.clicked.connect(self.export_to_file)
        self.exportButton.setDisabled(True)

        self.tokenTextInput = QtWidgets.QLineEdit(self)
        self.tokenTextInput.setGeometry(QtCore.QRect(20, 21, 700, 20))

        self.tokenInfoLabel = QtWidgets.QLabel(self)
        self.tokenInfoLabel.setGeometry(QtCore.QRect(20, 40, 700, 20))
        self.tokenInfoLabel.setText("Enter User Token here")

        self.userInfoLabel = QtWidgets.QLabel(self)
        self.userInfoLabel.setGeometry(QtCore.QRect(0, 0, 0, 0))
        self.userInfoLabel.setText("")

        self.appVeriOutput = QtWidgets.QLabel(self)
        self.appVeriOutput.setGeometry(QtCore.QRect(0, 0, 0, 0))
        self.appVeriOutput.setText("")

        self.idDescLabel = QtWidgets.QLabel(self)
        self.idDescLabel.setGeometry(QtCore.QRect(30, 520, 500, 20))
        self.idDescLabel.setText("")

        self.logOutput = ScrollLabel(self)
        self.logOutput.setGeometry(20, 80, 700, 441)
        self.logOutput.setText("Output:")

        self.clientVersionLabel = QtWidgets.QLabel(self)
        self.clientVersionLabel.setGeometry(QtCore.QRect(5, 590, 300, 20))
        self.clientVersionLabel.setText(f"Client Version {clientVersion}")

        self.connectionStatusLabel = QtWidgets.QLabel(self)
        self.connectionStatusLabel.setGeometry(QtCore.QRect(290, 40, 400, 20))
        self.connectionStatusLabel.setText("")

        self.updateStatusLabel = QtWidgets.QLabel(self)
        self.updateStatusLabel.setGeometry(QtCore.QRect(0, 0, 0, 0))
        self.updateStatusLabel.setText("")
        
        ###############################            MENU BAR THING       ########################################
        
        self.menuTools = QtWidgets.QMenu(self.menubar)
        self.menuTools.setTitle("Tools")
        self.setMenuBar(self.menubar)
        
        self.statusbar = QtWidgets.QStatusBar(self)
        self.setStatusBar(self.statusbar)

        self.eventLoggerMenu = QtWidgets.QAction(self)
        self.eventLoggerMenu.setText("Event Logger")
        self.event_window = Ui_eventLogWindow()
        self.eventLoggerMenu.triggered.connect(self.event_window.show)

        self.helpPanelMenu = QtWidgets.QAction(self)
        self.helpPanelMenu.setText("Feedback")
        self.help_window = Ui_HelpWindow()
        self.help_window.setDisabled(True)
        self.helpPanelMenu.triggered.connect(self.help_window.show)

        self.adminPanelMenu = QtWidgets.QAction(self)
        self.adminPanelMenu.setText("Admin Panel")
        self.debug_window = Ui_DebugWindow()
        self.adminPanelMenu.triggered.connect(self.debug_window.show)

        self.userLookupMenu = QtWidgets.QAction(self)
        self.userLookupMenu.setText("User Lookup")
        self.userLookup_window = Ui_AccountLookupWindow()
        self.userLookupMenu.triggered.connect(self.userLookup_window.show)
        
        ###### SHOWING DROPDOWN BAR ######

        self.menubar.addAction(self.menuTools.menuAction())
        self.menuTools.addAction(self.adminPanelMenu)
        self.menuTools.addAction(self.helpPanelMenu)
        self.menuTools.addAction(self.eventLoggerMenu)
        self.menuTools.addAction(self.userLookupMenu)
        
        self.show()



    def export_to_file(self):
        console_log("EXPORTING TO TEXT FILE...")
        try:
            while True:
                global fileCount
                filepath = f"ChatLogOutput{fileCount}.txt" #change back to txt !!!!!!!!!!!!!
                path_exists = os.path.exists(filepath)

                if not path_exists:
                    try:
                        with open(filepath, "w") as writeFile:
                            outputtext = "\n".join(outputList)
                            data = f"{log_date} - {username}#{discriminator}\n{outputtext}"
                            writeFile.write(unidecode(demojize(data)))

                        console_log(f"WROTE TO {filepath}") 
                        threading._start_new_thread(self.fileMadeCooldown, ())

                        webbrowser.open(filepath) # Webbrowser module uses subprocess module to open files - EDIT, the subprocess.Popen method that it uses DOES execute the specified file
                                                # This method is unsafe if the file that it is executing is not in a TXT format

                        console_log(f"OPENED FILE: ChatLogOutput{fileCount}.txt")
                        break
                    except FileExistsError:
                        fileCount += 1
                        continue
                elif path_exists:
                    fileCount += 1
                    continue
        except FileNotFoundError:
            console_log(f"FILE NOT FOUND")
    
    def fileMadeCooldown(self):
        self.exportButton.setText("Text file Created!")
        self.exportButton.setDisabled(True)
        sleep(1)
        self.exportButton.setText("Export to Text File")
        self.exportButton.setDisabled(False)
        
    def clear_output(self):
        self.logOutput.setText("Output:")
        global outputList
        outputList = []
        console_log("OUTPUT CLEARED")


    def check_update(self):
        request_failed_flag = False
        console_log("CHECKING FOR UPDATES...")
        update_payload = json.dumps ({"ClientVersion": clientVersion})
        headers = {"Content-Type":"application/json"} 
        
        try:
            r = requests.get(api_base + "update", headers=headers, data=update_payload)
            update_response = json.loads(r.text)
            update_status = update_response['status']
            # update_request_data = update_response['data']
        except:
            console_log("ERROR: COULD NOT RETRIEVE CLIENT UPDATE STATUS")
            request_failed_flag = True

        if request_failed_flag is False:
            if update_status == "update available":
                new_client = update_response['newestClient']
                console_log("UPDATE AVAILABLE")
                self.updateStatusLabel.setText(f"A new version is available! Version {new_client}")
                self.updateStatusLabel.setGeometry(QtCore.QRect(525, 60, 700, 20))
                pass
  
            elif update_status == "client up to date":
                console_log("CLIENT VERSION UP TO DATE")
                pass

            else:
                console_log("ERROR: INVALID SERVER RESPONSE, MISSING UPDATE STATUS")
                pass

        else:
            console_log("ERROR: CANNOT GET UPDATE STATUS, NO SERVER RESPONSE")
            pass


    def refresh_keys(keyExperation):
        # LOG EVENTS INTO CONSOLE
        while True:
            headers = {"Content-Type":"application/json"} 
            waitTime = keyExperation + 3
            sleep(waitTime)
            data = json.dumps ( {"clientVersion": clientVersion} )
            r = requests.get(api_base + "tokenRefresh", headers=headers, data=data)
            response3 = json.loads(r.text)

            if "token" in response3:
                global sessionKey
                keyExperation = response3['keyExperation']
                sessionKey = response3['token']
                console_log("NEW CLIENT KEY RETRIEVED")
                # print(keyExperation)
                # print(sessionKey)

            else:
                console_log("ERROR: UNABLE TO RETRIEVE NEW TOKEN - INVALID SERVER RESPONSE")
                print(response3)



    def submit_token(self):
        token_input = self.tokenTextInput.text()
        token_verified = self.verify_token(unidecode(demojize(token_input)))

        if token_verified:
            global TOKEN
            TOKEN = token_input
            operable = Ui_MainWindow.verify_app_operable()
            if operable:
                console_log("APPLICATION PROCEEDING TO RUN")

                self.idDescLabel.setText("[          TIME          ] [          SERVER ID        ]  [        CHANNEL ID        ]")
                self.runLoggerButton.setGeometry(QtCore.QRect(148, 540, 111, 51))

            elif operable is False: 
                console_log("APPLICATION HAS BEEN REMOTELY DISABLED, UNABLE TO RUN AT THIS TIME")
                self.disable_buttons()
                self.appVeriOutput.setText("The Application has been remotely disabled by administrator and is unable to run at this time.")

            elif operable == "Error":
                console_log("ERROR RESOLVING APPLICATION VERIFICATION, UNABLE TO RUN AT THIS TIME")
                self.disable_buttons()
                self.appVeriOutput.setText("Error: Unable to verify application, if this issue persists, contact a developer.")

            else:
                self.disable_buttons()
                self.appVeriOutput.setText(f"[ERROR]: {error_message}")     
                
        else:
            console_log("USER TOKEN INVALID")

    def verify_app_operable():
        console_log("VERIFYING APPLICATION...")
        op_request_payload = json.dumps( {f"runRequest": "clientRun",
                                            "client": clientVersion,
                                            "userID": user_id,
                                            "username": username,
                                            "discriminator": discriminator,
                                            "timestamp": f"{log_time} - {log_date} ({localTimeZone})", 
                                    } )

        op_request_headers = ( {"Content-Type":"application/json"} )

        r = requests.post(api_base + "verifyApp", data=op_request_payload, headers=op_request_headers)
        response2 = json.loads(r.text)

        if "appState" in response2:
            global sessionKey, keyExperation
            appState = response2['appState']
            sessionKey = response2['sessionKey']
            keyExperation = response2['sessionKeyExpire']
            # print(keyExperation)
            # print(sessionKey)
            tokenRefreshThread = threading.Thread(target=Ui_MainWindow.refresh_keys, args=(keyExperation, ))
            tokenRefreshThread.start()
            if appState == "enabled":
                console_log("RESPONSE: APPLICATION VERIFIED TO RUN")
                return True
            elif appState == "disabled":
                console_log("RESPONSE: APPLICATION NOT VERIFIED TO RUN")
                return False
            else:
                return "Error"
        elif "data" in response2:
            global error_message
            error_message = response2['data']
            console_log(error_message)
        else:
            return "Error"

    def verify_token(self, token_input):
        global headers
        headers = { "Authorization":token_input.replace("\n", "", 1),
                    "User-Agent":"myBotThing (http://some.url, v0.1)",
                    "Content-Type":"application/json", }
        try:
            userUrl = requests.get("https://discord.com/api/v9/users/@me", headers=headers)
            json_response = json.loads(userUrl.text)
        except requests.exceptions.InvalidJSONError:
            pass

        if "id" in json_response:
            global username, discriminator, user_id
            username, discriminator, user_id = json_response['username'], json_response['discriminator'], json_response["id"]
            
            self.userInfoLabel.setText(f"Selected User Account - {username}#{discriminator}")
            self.userInfoLabel.setGeometry(QtCore.QRect(20, 60, 700, 20))
            self.tokenTextInput.setGeometry(QtCore.QRect(0, 0, 0, 0))
            self.tokenInfoLabel.setText(f"Token Verified | {log_date}")
            self.checkTokenButton.setDisabled(True)
            self.runLoggerButton.setDisabled(False)
            self.exportButton.setDisabled(False)
            self.clearOutputButton.setDisabled(False)
            self.help_window.setDisabled(False)
            # enable userIdSubmitButton
            

            console_log(f"USER TOKEN VERIFIED FOR USER: {username}#{discriminator}")
            return True 
            
        else:
            self.tokenInfoLabel.setText("Invalid user token, please try again.")
            return False

    def disable_buttons(self):
        self.tokenInfoLabel.setGeometry(QtCore.QRect(0, 0, 0, 0))
        self.userInfoLabel.setGeometry(QtCore.QRect(0, 0, 0, 0))
        self.appVeriOutput.setGeometry(QtCore.QRect(20, 60, 700, 20))
        self.idDescLabel.setGeometry(QtCore.QRect(0, 0, 0, 0))
        self.exportButton.setDisabled(True)
        self.checkTokenButton.setDisabled(True)
        self.runLoggerButton.setDisabled(True)
        self.clearOutputButton.setDisabled(True)

    def user_restart_app(self):
        try:
            global connectionLostCount
            connectionLostCount += 1
            self.connectionStatusLabel.setText(f"Disconnected from service, attempting to reconnect | Lost connection {connectionLostCount} times")
            sleep(3)
            self.run_logger()
            console_log("LOGGER RESTARTED")
        except:
            console_log("FAILED TO RESTART APP AFTER CONNECTION LOST")
            sleep(5)


    ##### RUN LOGGER FUNCTION #####

    def run_logger(self):
        self.runLoggerButton.setDisabled(True)
        def scan():
            while True:
                try:
                    event = recieve_json_response(ws)
                    # print(event) # Prints all JSON payloads before parsing
                    self.connectionStatusLabel.setText(f"Connected to service | Lost connection {connectionLostCount} times")
                except websocket._exceptions.WebSocketConnectionClosedException:
                    sleep(1)
                    if not ws.connected:
                        console_log("THE CONNECTION WAS INTERRUPTED; PROGRAM RESTARTING")
                        self.user_restart_app()
                        break
                try:
                    message_payload = event['d']
                    if "guild_id" in message_payload:
                        try:
                            output1 = f"[{event['d']['guild_id']}] [{event['d']['channel_id']}] - {event['d']['author']['username']}#{event['d']['author']['discriminator']}: {event['d']['content']}"
                            outputList.append(f"[       {log_time}      ] {output1}")
                            self.logOutput.setText("\n".join(outputList))
                            
                        except:
                            pass
                    else:
                        try:
                            output2 = f"[               NULL             ] [{event['d']['channel_id']}] - {event['d']['author']['username']}#{event['d']['author']['discriminator']}: {event['d']['content']}"
                            outputList.append(f"[       {log_time}      ] {output2}")
                            self.logOutput.setText("\n".join(outputList))
                        except:
                            pass

                except:
                    pass


                    
                ##### STATUS HANDLING #####

                try:
                    payload_header = event['t']
                    if payload_header == "PRESENCE_UPDATE":
                        user_id = event['d']['user']['id']
                        username = event['d']['user']['username']
                        user_discrim = event['d']['user']['discriminator']
                        status = event['d']['status']
                        client = event['d']['client_status']
                        # print(user_id)
                        # print(username)
                        # print(user_discrim)
                        # print(status)
                        # if client:
                        #     print(client)
                        

                        # Remember to also log cliens, moblie, web, etc. Should be under 'client_status'
                        # NOTE - When a user goes offline client status will be empty ( '{}' )
                        
                            # Make if statements to parse for differnet clients
                            # WARNING - CLIENT PAYLOAD CAN CONTAIN MORE THAN ONE CLIENT
                            
                            # NOTE: Do client checks within these checks since status will always be present in JSON payload; rewrite! 
                        if status == "online":
                            if "mobile" in client:
                                presence_output = f"[     {log_time}    ] [{username}#{user_discrim} ({user_id})]: STATUS ONLINE [MOBILE CLIENT]"
                                eventList.append(presence_output)
                                Ui_eventLogWindow.eventListLabel.setText("\n".join(eventList))
                            elif "web" in client:
                                presence_output = f"[     {log_time}    ] [{username}#{user_discrim} ({user_id})]: STATUS ONLINE [WEB CLIENT]"
                                eventList.append(presence_output)
                                Ui_eventLogWindow.eventListLabel.setText("\n".join(eventList))
                            elif "desktop":
                                presence_output = f"[     {log_time}    ] [{username}#{user_discrim} ({user_id})]: STATUS ONLINE [DESKTOP CLIENT]"
                                eventList.append(presence_output)
                                Ui_eventLogWindow.eventListLabel.setText("\n".join(eventList))
                            else:
                                console_log(f'ERROR HANDLING CLIENT STATUS: UNEXPECTED CLIENT "{client}"')
                                pass

                        elif status == "offline":
                            presence_output = f"[     {log_time}    ] [{username}#{user_discrim} ({user_id})]: STATUS OFFLINE"
                            eventList.append(presence_output)
                            Ui_eventLogWindow.eventListLabel.setText("\n".join(eventList))

                        elif status == "dnd":
                            if "mobile" in client:
                                presence_output = f"[     {log_time}    ] [{username}#{user_discrim} ({user_id})]: STATUS DO NOT DISTURB [MOBILE CLIENT]"
                                eventList.append(presence_output)
                                Ui_eventLogWindow.eventListLabel.setText("\n".join(eventList))
                            elif "web" in client:
                                presence_output = f"[     {log_time}    ] [{username}#{user_discrim} ({user_id})]: STATUS DO NOT DISTURB [WEB CLIENT]"
                                eventList.append(presence_output)
                                Ui_eventLogWindow.eventListLabel.setText("\n".join(eventList))
                            elif "desktop":
                                presence_output = f"[     {log_time}    ] [{username}#{user_discrim} ({user_id})]: STATUS DO NOT DISTURB [DESKTOP CLIENT]"
                                eventList.append(presence_output)
                                Ui_eventLogWindow.eventListLabel.setText("\n".join(eventList))
                            else:
                                console_log(f'ERROR HANDLING CLIENT STATUS: UNEXPECTED CLIENT "{client}"')
                            

                        elif status == "idle":
                                if "mobile" in client:
                                    presence_output = f"[     {log_time}    ] [{username}#{user_discrim} ({user_id})]: STATUS IDLE [MOBILE CLIENT]"
                                    eventList.append(presence_output)
                                    Ui_eventLogWindow.eventListLabel.setText("\n".join(eventList))
                                elif "web" in client:
                                    presence_output = f"[     {log_time}    ] [{username}#{user_discrim} ({user_id})]: STATUS IDLE [WEB CLIENT]"
                                    eventList.append(presence_output)
                                    Ui_eventLogWindow.eventListLabel.setText("\n".join(eventList))
                                elif "desktop":
                                    presence_output = f"[     {log_time}    ] [{username}#{user_discrim} ({user_id})]: STATUS IDLE [DESKTOP CLIENT]"
                                    eventList.append(presence_output)
                                    Ui_eventLogWindow.eventListLabel.setText("\n".join(eventList))
                                else:
                                    console_log(f'ERROR HANDLING CLIENT STATUS: UNEXPECTED CLIENT "{client}"')

                        else:
                                console_log(f'ERROR, UNEXPECTED STATUS "{status}"')

                except:
                    pass

                    
                # try:
                #     if payload_header == ""

                    




                    op_code = event['op']
                    if op_code == 11:
                        console_log("WEBSOCKET HEARTBEAT RECIVED")
        
        console_log("LOGGER PROMPTED, STARTING...")

        def send_json_request(ws, request):
            ws.send(json.dumps(request))
            console_log(f'JSON REQUEST SENT WITH TOKEN')

        def recieve_json_response(ws):
            response = ws.recv()
            if response:
                console_log("JSON RESPONSE RECIEVED")
                return json.loads(response)

        def heartbeat(interval, ws):
            console_log("WEBSOCKET HEARTBEAT BEGIN")
            while True:
                sleep(interval)
                heartbeatJSON = {
                    "op": 1,
                    "d": "null"
                }
                try:
                    send_json_request(ws, heartbeatJSON)
                    console_log("WEBSOCKET HEARTBEAT SENT")
                except websocket._exceptions.WebSocketConnectionClosedException:
                    pass

        ws = websocket.WebSocket()
        discord_gateway = "wss://gateway.discord.gg/?v=6&encording=json"
        
        try:
            ws.connect(discord_gateway)
            console_log(f"REQUEST SENT TO DISCORD WEBSOCKET")
        except:
            console_log("WEBSOCKET REQUEST FAILED TO SEND; PROGRAM RESTARTED")
            self.user_restart_app()

        event = recieve_json_response(ws)

        heartbeat_interval = event['d']['heartbeat_interval'] / 1000
        threading._start_new_thread(heartbeat, (heartbeat_interval, ws))

        # Identify Payload
        payload = {
            'op': 2,
            "d": {
                "token": TOKEN,
                "properties": {
                    "$os": "windows",
                    "$browser": "chrome",
                    "$device": 'pc'
                }
            }
        }
        try:
            send_json_request(ws, payload)
        except:
            pass
        threading._start_new_thread(scan, ())

def console_log(message):
    global log_time, log_date, localTimeZone
    global debugList
    now = datetime.now()
    local_now = now.astimezone()
    local_tz = local_now.tzinfo
    localTimeZone = local_tz.tzname(local_now)
    log_date = now.strftime("%m/%d/%Y")
    log_time = now.strftime("%I:%M:%S %p")

    print(f"{log_time} | {message}")
    debugList.append(f"{log_time} | {message}")

def configure():
    load_dotenv()

def run_app():
    print("====================================\n")
    app = QtWidgets.QApplication(sys.argv)
    ui = Ui_MainWindow()
    appthread = threading.Thread(target=ui.show)
    appthread.start()
    console_log("PROGRAM STARTED SUCCESSFULLY")
    Ui_MainWindow.check_update(ui)

    sys.exit(app.exec_())
    
if (__name__ == "__main__"):
    configure()
    run_app()