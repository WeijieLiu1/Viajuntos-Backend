# Import Flask dependences
# Import module models
import sqlalchemy 
from app.module_chat.models import Message, Chat, Members
from app.module_event.models import Event
from flask_jwt_extended import get_jwt_identity, jwt_required
from app.module_users.models import User
import uuid, ipdb
from flask import Blueprint, jsonify, request

# Define the blueprint: 'Message', set its url prefix: app.url/message
module_chat_v1 = Blueprint('chat', __name__, url_prefix= '/v1/chat')
# create a private chat
def crear_private_chat(user1_id, user2_id):

    user1 = User.query.filter_by(id = user1_id).first()
    if user1 == None:
        return jsonify({'error_message': 'No such user.'}), 404
    
    user2 = User.query.filter_by(id = user2_id).first()
    if user2 == None:
        return jsonify({'error_message': 'No such user.'}), 404
    
    id = uuid.uuid4()
    New_Chat = Chat(id, "private", "private", "")

    try:
        New_Chat.save()
        
        new_member1 = Members(user1_id, New_Chat.id)
        try:
            new_member1.save()
        except:
            return jsonify({"error_message": "Something happened in the insert"}), 400
        
        new_member2 = Members(user2_id, New_Chat.id)
        try:
            new_member2.save()
        except:
            return jsonify({"error_message": "Something happened in the insert"}), 400
    except sqlalchemy.exc.IntegrityError:
       return jsonify({"error_message": "FK problems, the user or the event doesn't exists"}), 400
    except:
        return jsonify({"error_message": "Something happened in the insert"}), 400
    
    return jsonify([New_Chat.toJSON()]), 201

def borrar_chat(chat_id):
    try:
        Chat_buscado = Chat.query.filter_by(id = chat_id).first()
        if Chat_buscado is None:
            return jsonify({"error_message": "El chat solicitado no existe"}), 400
        Messages = Message.query.filter_by(chat_id = Chat_buscado.id)
        for message in Messages:
            message.delete()
        Members = Members.query.filter_by(chat_id = Chat_buscado.id)
        for member in Members:
            member.delete()
        Chat_buscado.delete()
    except:
        return jsonify({"error_message": "Falla el eliminar los chats"}), 400

    return jsonify({"message":f"The messages from this chat have been succesfully deleted"}), 202

# create a public chat
def crear_public_chat(chat_name, creator_id, chat_members):

    creator = User.query.filter_by(id = creator_id).first()
    if creator == None:
        return jsonify({'error_message': 'No such user.'}), 404
    try:
        id = uuid.uuid4()
        New_Chat = Chat(id, chat_name, "public", creator_id)
        New_Chat.save()
        
        for member in chat_members:
            new_member = Members(member, New_Chat.id)
            ipdb.set_trace()
            new_member.save()
            
        ipdb.set_trace()
    except sqlalchemy.exc.IntegrityError:
       return jsonify({"error_message": "FK problems, the user or the event doesn't exists"}), 400
    except:
        return jsonify({"error_message": "Something happened in the insert"}), 400
    
    return jsonify([New_Chat.toJSON()]), 201

@module_chat_v1.route('/add_member', methods=['POST'])
@jwt_required(optional=False)
def add_member(id_chat,id_new_member):
    try: 
        args = request.json
    except:
        return jsonify({"error_message": "The JSON argument is bad defined"}), 400
    if args.get("id_chat") is None:
        return jsonify({"error_message": "Chat Id is not defined or its value is null"}), 400
    if args.get("id_new_member") is None:
        return jsonify({"error_message": "New member Id is not defined or its value is null"}), 400

    Chat_buscado= Chat.query.filter_by(id = id_chat).first()
    auth_id = uuid.UUID(get_jwt_identity())
    if Chat_buscado == None:
        return jsonify({'error_message': 'No such chat.'}), 404
    if Chat_buscado.type == "private":
        return jsonify({'error_message': 'Private chat.'}), 404
    if Chat_buscado.creador_id != auth_id:
        return jsonify({'error_message': 'You are not the creator of the chat.'}), 404
    try:
        new_member = Members(id_new_member, id_chat)
        new_member.save()
    except sqlalchemy.exc.IntegrityError:
       return jsonify({"error_message": "FK problems, the user or the event doesn't exists"}), 400
        
    return jsonify([new_member.toJSON()]), 201

def add_member_back(id_chat,id_new_member):
    Chat_buscado= Chat.query.filter_by(id = id_chat).first()
    if Chat_buscado == None:
        return jsonify({'error_message': 'No such chat.'}), 404
    if Chat_buscado.type == "private":
        return jsonify({'error_message': 'Private chat.'}), 404
    try:
        new_member = Members(id_new_member, id_chat)
        new_member.save()
    except sqlalchemy.exc.IntegrityError:
       return jsonify({"error_message": "FK problems, the user or the event doesn't exists"}), 400
        
    return jsonify([new_member.toJSON()]), 201

def remove_member_back(id_chat,id_new_member):
    Chat_buscado= Chat.query.filter_by(id = id_chat).first()
    if Chat_buscado == None:
        return jsonify({'error_message': 'No such chat.'}), 404
    if Chat_buscado.type == "private":
        return jsonify({'error_message': 'Private chat.'}), 404
    try:
        member = Members.query.filter_by(chat_id = id_chat, user_id = id_new_member).first()
        member.delete()
    except sqlalchemy.exc.IntegrityError:
       return jsonify({"error_message": "FK problems, the user or the event doesn't exists"}), 400
    
def remove_all_member_back(id_chat):
    try:
        Members = Members.query.filter_by(chat_id = id_chat)
        for member in Members:
            member.delete()
    except:
        return jsonify({"error_message": "Falla el eliminar los chats"}), 400

    return jsonify({"message":f"The messages from this chat have been succesfully deleted"}), 202



@module_chat_v1.route('/remove_member', methods=['POST'])
@jwt_required(optional=False)
def remove_member(id_chat,id_member):
    try: 
        args = request.json
    except:
        return jsonify({"error_message": "The JSON argument is bad defined"}), 400
    if args.get("id_chat") is None:
        return jsonify({"error_message": "Chat Id is not defined or its value is null"}), 400
    if args.get("id_member") is None:
        return jsonify({"error_message": "Member Id is not defined or its value is null"}), 400

    Chat_buscado= Chat.query.filter_by(id = id_chat).first()
    auth_id = uuid.UUID(get_jwt_identity())
    if Chat_buscado == None:
        return jsonify({'error_message': 'No such chat.'}), 404
    if Chat_buscado.type == "private":
        return jsonify({'error_message': 'Private chat.'}), 404
    if Chat_buscado.creador_id != auth_id:
        return jsonify({'error_message': 'You are not the creator of the chat.'}), 404
    try:
        member = Members.query.filter_by(user_id = id_member, chat_id = id_chat).first()
        member.delete()
    except:
         return jsonify({"error_message": "Falla el eliminar los chats"}), 400
        
    return jsonify({"message":f"The messages from this user have been succesfully deleted"}), 202

@module_chat_v1.route('/all_members/<id_chat>', methods=['GET'])
@jwt_required(optional=False)
def get_chat_members(id_chat):
    try:
        members = Members.query.filter_by(chat_id = id_chat)
        users = []
        for member in members:
            users.append(User.query.filter_by(id = member.user_id).first())
    except:
        return jsonify({"error_message": "Falla el consultar los miembros de chat"}), 400

    return jsonify([user.toJSON() for user in users]), 202

# Crear Mensaje: create a new message
# Recibe:
# POST HTTP request con los atributos del nuevo mensaje en el body(JSON)
#       {userid, eventid, text}
# Devuelve
# - 400: Un objeto JSON con un mensaje de error
# - 201: Un objeto JSON con todos los parametros del nuevo mensaje(JSON)
@module_chat_v1.route('/create_message', methods=['POST'])
@jwt_required(optional=False)
def create_message():

    auth_id = uuid.UUID(get_jwt_identity())
    try: 
        args = request.json
    except:
        return jsonify({"error_message": "The JSON argument is bad defined"}), 400
    
    if args.get("chat_id") is None:
        return jsonify({"error_message": "Chat Id is not defined or its value is null"}), 400
    if args.get("text") is None:
        return jsonify({"error_message": "Text is not defined or its value is null"}), 400
    if not isinstance(args.get("text"), str):
        return jsonify({"error_message": "The text is not a string"}), 400
    
    try:
        chat_id = uuid.UUID(args.get("chat_id"))
    except:
        return jsonify({"error_message": "The chat id not is a valid uuid"})
    
    try:
        Chat_buscat= Chat.query.filter_by(id = chat_id).first()
    except:
        return jsonify({"error_message": "El chat solicitado no existe"}), 400
    
    if Chat_buscat is None:
        return jsonify({"error_message": "No hay ningun chat con esas credenciales"}), 400
    
    try:
        Members_buscat = Members.query.filter_by(chat_id = Chat_buscat.id, user_id = auth_id).first()
    except:
        return jsonify({"error_message": "Error cuando buscando los memienbros"}), 400
    if Members_buscat is None:
        return jsonify({"error_message": "El usuario no es miembro del chat"}), 400
    
    id = uuid.uuid4()
    Message_new = Message(id, auth_id, Chat_buscat.id, args.get("text"))

    try: 
        Message_new.save()
    except sqlalchemy.exc.IntegrityError:
        return jsonify({"error_message": "FK problems, the user or the event doesn't exists"}), 400
    except:
        return jsonify({"error_message": "Something happened in the insert"}), 400

    return jsonify(Message_new.toJSON()), 201

def create_message_back(auth_id, chat_id, text):

    try:
        Chat_buscat= Chat.query.filter_by(id = chat_id).first()
    except:
        return jsonify({"error_message": "El chat solicitado no existe"}), 400
    
    if Chat_buscat is None:
        return jsonify({"error_message": "No hay ningun chat con esas credenciales"}), 400
    
    try:
        Members_buscat = Members.query.filter_by(chat_id = Chat_buscat.id, user_id = auth_id).first()
    except:
        return jsonify({"error_message": "Error cuando buscando los memienbros"}), 400
    if Members_buscat is None:
        return jsonify({"error_message": "El usuario no es miembro del chat"}), 400
    
    id = uuid.uuid4()
    Message_new = Message(id, auth_id, Chat_buscat.id, text)

    try: 
        Message_new.save()
    except sqlalchemy.exc.IntegrityError:
        return jsonify({"error_message": "FK problems, the user or the event doesn't exists"}), 400
    except:
        return jsonify({"error_message": "Something happened in the insert"}), 400
    
    return Message_new.toJSON()

@module_chat_v1.route('/delete_message', methods=['POST'])
@jwt_required(optional=False)
# Borrar Mensaje: delete a message as sender
def borrar_mensaje(id_message):
    
    auth_id = uuid.UUID(get_jwt_identity())
    try: 
        args = request.json
    except:
        return jsonify({"error_message": "The JSON argument is bad defined"}), 400
    if args.get("id_message") is None:
        return jsonify({"error_message": "Message Id is not defined or its value is null"}), 400
    try:

        Message_buscado = Message.query.filter_by(id = id_message).first()
        if Message_buscado is None:
            return jsonify({"error_message": "El mensaje solicitado no existe"}), 400
        if Message_buscado.sender_id != auth_id:
            return jsonify({"error_message": "El usuario no es el creador del mensaje"}), 400
        Message_buscado.delete()
    except:
        return jsonify({"error_message": "Falla el eliminar el message indicado"}), 400

    return jsonify({"message":f"The message has been succesfully deleted"}), 202

# delete chat and all messages from of event
def borrar_mensajes_y_evento(id_evento):
    try:
        A_borrar = Chat.query.filter_by(event_id = id_evento).first()
        borrar_mensajes_chat(A_borrar.id)
        remove_all_member_back(A_borrar.id)
        A_borrar.delete()
    except:
        return jsonify({"error message": "Falla el eliminar el chat indicado"}), 400
    


# delete all chats and all messages from a user where he is a member
def borrar_todos_chats_usuario(usuari_esborrar):
    try:
        user_member = Members.query.filter_by(user_id = usuari_esborrar)

        for member in user_member:
            Chat_buscado = Chat.query.filter_by(id = member.chat_id).first()
            Messages = Message.query.filter_by(chat_id = Chat_buscado.id)
            for message in Messages:
                message.delete()
            Members = Members.query.filter_by(chat_id = Chat_buscado.id)
            for member in Members:
                member.delete()
            Chat_buscado.delete()
    except:
        return jsonify({"error_message": "Falla el eliminar los chats del usuario"}), 400

    return jsonify({"message":f"All messages from this user have been succesfully deleted"}), 202

# delete all messages from a chat
def borrar_mensajes_chat(id_chat):
    try:
        A_borrar = Chat.query.filter_by(id = id_chat).first()
        for Chat_borrar in A_borrar:
            Messages = Message.query.filter_by(chat_id = Chat_borrar.id)
            for message in Messages:
                message.delete()
    except:
        return jsonify({"error message": "Falla el eliminar el chat indicado"}), 400

    return jsonify({"message":f"The messages from this event have been succesfully deleted"}), 201

# delete all messages from a user in a chat
def borrar_mensajes_usuario_chat(id_chat, id_usuario):
    
    try:
        member = Members.query.filter_by(chat_id = id_chat.id, user_id = id_usuario).first()
        
        if member is None:
            return jsonify({"error_message": "El usuario no es miembro del chat"}), 400

        Messages = Message.query.filter_by(chat_id = id_chat, sender_id = id_usuario)
        for message in Messages:
            message.delete()
    except:
        return jsonify({"error message": "Falliure when delete all messages from a user in a chat"}), 400

    return jsonify({"message":f"The messages from this participant have been succesfully deleted"}), 201   


    
# GET method: get all chats from a user as creator
@module_chat_v1.route('/<id>', methods=['GET'])
# RECIBE:
    # GET HTTP request con la id del usuario del que queremos obtener los chats
# DEVUELVE
    # -202: Un objeto JSON con todos los Chats del usuario solicitado
    # -400: Un objeto JSON con los posibles mensajes de error, id no valida o usuario no existe
@jwt_required(optional=False)
def get_user_chats(id):
    try: 
        user_id = uuid.UUID(id)
    except:
        return jsonify({"error_message": "The user id isn't a valid uuid"}), 400

    try:
        members_user = Members.query.filter_by(user_id = user_id)
        #check if members_user is empty
        if members_user.first() is None:
            return jsonify({"error_message": "The user has no chats"}), 200
        chats_user = []
        for member in members_user:
            chats_user.append(Chat.query.filter_by(id = member.chat_id).first())
    except:
        return jsonify({"error_message": "Chat no exist"}), 400

    return jsonify([chat.toJSON() for chat in chats_user]), 200


# # GET method: get all chats from an event
# @module_chat_v1.route('/event/<id>', methods=['GET'])
# # RECIBE:
#     # GET HTTP request con la id del evento del que queremos obtener los chats
# # DEVUELVE
#     # -202: Un objeto JSON con todos los Chats del evento solicitado
#     # -400: Un objeto JSON con los posibles mensajes de error, id no valida o usuario no existe
# @jwt_required(optional=False)
# def get_events_chats(id):
#     try: 
#         event_id_buscat = uuid.UUID(id)
#     except:
#         return jsonify({"error_message": "The user id isn't a valid uuid"}), 400

#     try:
#         chats_event = Chat.query.filter_by(event_id = event_id_buscat)
#     except:
#         return jsonify({"error_message": "Chat no exist"}), 400

#     return jsonify([chat.toJSON() for chat in chats_event]), 200

    
# Get method: get all messages from a chat
@module_chat_v1.route('/Message/<chat_id>', methods=['GET'])
# RECIBE:
    # GET HTTP request con el evento y el participante del chat
#DEVUELVE
    # -202: Un objeto JSON con todos los mensajes del chat solicitado
    # -400: Un objeto Json con el posible mensaje de error, chat no existe
@jwt_required(optional=False)
def get_chat_messages(chat_id):
    
    try: 
        auth_id = uuid.UUID(get_jwt_identity())
    except:
        return jsonify({"error_message": "The user id isn't a valid uuid"}), 400
    try:
        Chat_buscat= Chat.query.filter_by(id = chat_id).first()
    except:
        return jsonify({"error_message": "Error cuando buscando chat"}), 400

    if Chat_buscat is None:
        return jsonify({"error_message": "El chat solicitado no existe"}), 400

    try:
        Members_buscat = Members.query.filter_by(chat_id = Chat_buscat.id)
    except:
        return jsonify({"error_message": "Error cuando buscando los memienbros"}), 400
    
    if Members_buscat is None:
        return jsonify({"error_message": "El chat no tiene mienbros"}), 400
    
    is_member = False
    for member in Members_buscat:
        if member.user_id == auth_id:
            is_member = True
            break
    if not is_member:
        return jsonify({"error_message": "El usuario no es miembro del chat"}), 400

    try:
        messages = Message.query.filter_by(chat_id = Chat_buscat.id)
    except:
        return jsonify({"error_message": "Error cuando buscando los mensajes"}), 400

    return jsonify([Resultats.toJSON() for Resultats in messages]), 200

@module_chat_v1.route('/chat_image_url/<id>', methods=['GET'])
@jwt_required(optional=False)
# get chat image
def get_chat_image_url(id):

    auth_id = uuid.UUID(get_jwt_identity())


    Chat_id = uuid.UUID(id)
    try:
        Chat_buscat= Chat.query.filter_by(id = Chat_id).first()
    except:
        return jsonify({"error_message": "Error cuando buscando chat"}), 400

    if Chat_buscat is None:
        return jsonify({"error_message": "El chat solicitado no existe"}), 400
    try:
        if Chat_buscat.type == "private":
            Members_buscat = Members.query.filter_by(chat_id = Chat_buscat.id)
            for member in Members_buscat:
                if member.user_id != auth_id:
                    user = User.query.filter_by(id = member.user_id).first()
                    return jsonify({"image_url": user.image_url}), 200
        else:
            event = Event.query.filter_by(chat_id = Chat_buscat.id).first()
            return jsonify({"image_url": event.event_image_uri}), 200
    except:
        return jsonify({"error_message": "Error cuando buscando el link del imagen del chat"}), 400

    # return jsonify([Resultats.toJSON() for Resultats in messages]), 200