from uuid import UUID
from app import app
import os,json, time, ipdb
from flask import Flask, render_template
from flask_socketio import SocketIO, join_room, send
from datetime import datetime

from app.module_chat.controllers import create_message_back
from app.module_event.models import Participant
# from app.module_event.controllers_v3 import verify_code_backend

# Flask-SocketIO==4.3.1
# python-engineio==3.13.2
# python-socketio==4.6.0

# Flask-SocketIO==5.3.6
# python-engineio==4.7.0
# python-socketio==5.9.0


# python-engineio==4.8.0
# python-socketio==5.10.0
# Flask-SocketIO==5.3.6
def default(o):
    if isinstance(o, UUID):
        return str(o)
    if isinstance(o, datetime):
        return o.isoformat()

# socketio = SocketIO(app, cors_allowed_origins='*')
socketio = SocketIO(app, async_mode='eventlet', cors_allowed_origins='*')
@socketio.on('connect')
def connect():
    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")
    print("Current Time =", current_time)
    print("a client connected")
    socketio.emit('msg', "Server: client connected")
    socketio.emit('ping', "Server: client connected")
    # socketio.emit('VerificationDone', json.dumps(msg, default=default),to='628a0571-605a-49d4-9c81-d71773eaff7f_38d1837b-c4ea-4e0a-98e5-ba09a4ee69bd')

@socketio.on('disconnect')
def disconnect():
    now = datetime.now()    
    current_time = now.strftime("%H:%M:%S")
    print("Current Time =", current_time)
    print('Client disconnected')

@socketio.on('msg')
def handle_message(message):
    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")
    print("Current Time =", current_time)
    print('received message: ' + message)
    socketio.emit('fromServer', "fromServer ok")

@socketio.on('ChatMessage')
def handle_chat_message(data):
    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")
    chat_id = data['chat_id']
    text = data['text']
    sender_id = data['sender_id']
    print("Current Time =", current_time)
    print('received message: ' + text+ " to: "+chat_id)
    print("Current Time =", current_time)
    # send(message + ' has entered the room.', to=chat_id)
    msg = create_message_back(sender_id, chat_id, text)
    socketio.emit('ChatMessage', json.dumps(msg, default=default),to=chat_id)
    print("chat_id =", chat_id)
    # socketio.to(chat_id).emit('broadcast_message', message)



@socketio.on('join_room')
def on_join(data):
    username = data['username']
    room = data['room']
    join_room(room)
    print(username + ' has entered the room.'+ room )
    send(username + ' has entered the room.', to=room)

@socketio.on('be_scanning')
def on_be_scanning(data):
    username = data['username']
    room = data['idEvent'] + "_"+username
    # room = 'idEvent'
    join_room(room)
    print('be_scanning: '+username + ' has entered the room.'+ room )
    socketio.emit('CheckVerification','nada', to='628a0571-605a-49d4-9c81-d71773eaff7f_38d1837b-c4ea-4e0a-98e5-ba09a4ee69bd')
    send(username + ' has entered the room.', to=room)
    
# socket.io version v2.x
# connection error: It seems you are trying to reach a Socket.IO server in v2.x with a v3.x client, 
# but they are not compatible (more information here: https://socket.io/docs/v3/migrating-from-2-x-to-3-0/)

# https://amritb.github.io/socketio-client-tool/v1/
# http://127.0.0.1:5000 /socket.io/ {"forceNew": true, "reconnectionAttempts": 3, "timeout": 2000, "transports": ["websocket"]}
if __name__ == '__main__':
    # Secret key for signing cookies
    #os.system('source testEnv.sh')
    #print("Starting API server... "+5000)
    #print("Starting API server... "+os.environ.get('API_PORT'))
    # app.run(host='0.0.0.0', port=int(os.environ.get('API_PORT')), debug=bool(os.getenv('API_DEBUG')))
    # socketio.run(app, host='localhost', port=int(os.environ.get('API_PORT') or 5000), debug=bool(os.getenv('API_DEBUG')),)
    # print("Socket.IO version:", socketio.server.eio_manager.eio.protocol_version)
    # socketio.run(app, debug=True, async_mode='threading', transports=['websocket'])
    socketio.run(app, debug=True)
    #app.run(host='0.0.0.0', port=5000, debug=bool(os.getenv('API_DEBUG')))