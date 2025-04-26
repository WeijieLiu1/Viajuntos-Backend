from uuid import UUID
from app import app
import os,json, time, ipdb
from flask import Flask, render_template
from flask_socketio import SocketIO, join_room, leave_room, rooms, send
from datetime import datetime
from flask_cors import CORS
from app.module_chat.controllers import create_message_back
from app.module_event.models import Participant
def default(o):
    if isinstance(o, UUID):
        return str(o)
    if isinstance(o, datetime):
        return o.isoformat()
CORS(app, resources={r"/*": {"origins": "*"}})
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
    
@socketio.on('disconnect')
def disconnect():
    print('Client disconnected')
    for room in rooms():
        leave_room(room)

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
    
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))  # 默认为8080
    socketio.run(app, host='0.0.0.0', port=port)