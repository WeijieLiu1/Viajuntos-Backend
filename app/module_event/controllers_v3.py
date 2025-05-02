# Import flask dependencies
# Import module models (i.e. User)
import os
import sqlalchemy
from app.module_event.models import BannedEvents, Event, EventImages, EventPosts, EventType, LikePost, Participant, Like, Payment, PaymentStatus, PostImages, Review
from app.module_users.models import BannedUsers, Friend, User, GoogleAuth,GithubAuth
from app.module_admin.models import Admin, ReportedEvent
from app.module_airservice.controllers import general_quality_at_a_point
from app.module_users.utils import increment_achievement_of_user

from app.module_chat.controllers import add_member_back, borrar_mensajes_usuario_chat, borrar_mensajes_y_evento,crear_public_chat, remove_member_back
from app.module_calendar.functions_calendar import crearEvento, eliminarEventoTitle, editarEventoTitle, editarEventoDesciption
import secrets

from profanityfilter import ProfanityFilter
from flask_jwt_extended import get_jwt_identity, jwt_required
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from flask import (Blueprint, request, jsonify, current_app)
import uuid
import validators
import json
import ipdb
# Import the database object from the main app module
from app import db
from wsgi import socketio
# Define the blueprint: 'event', set its url prefix: app.url/event
module_event_v3 = Blueprint('event_v3', __name__, url_prefix='/v3/events')

# # Min y Max longitud and latitude of Catalunya from resource https://www.idescat.cat/pub/?id=aec&n=200&t=2019
# min_longitud_catalunya = 0.15
# max_longitud_catalunya = 3.316667

# min_latitude_catalunya = 40.51667
# max_latitude_catalunya = 42.85

# Set the route and accepted methods

# CREAR EVENTO: Crea un evento en la base de datos
# Recibe:
# POST HTTP request con los atributos del nuevo evento en el body (formato JSON)
#       {name, description, date_started, date_end, user_creator, longitud, latitude, max_participants}
# Devuelve:
# - 400: Un objeto JSON con un mensaje de error
# - 201: Un objeto JSON con todos los parametros del evento creado (con la id incluida)
@module_event_v3.route('/', methods=['POST'])
@jwt_required(optional=True)  # cambio esto y lo pongo en True
def create_event():
    
    auth_id = get_jwt_identity()
    if BannedUsers.exists_user(auth_id):
            return jsonify({'error_message': 'This email is banned'}), 409
    try:
        args = request.json
        #args.noauth_local_webserver = True
    except:
        return jsonify({"error_message": "Mira el JSON body de la request, hay un atributo mal definido!"}), 400

    event_uuid = uuid.uuid4()

    response = check_atributes(args, "create")
    if (response['error_message'] != "all good"):
        return jsonify(response), 400

    date_started = datetime.strptime(
        args.get("date_started"), '%Y-%m-%d %H:%M:%S')
    date_end = datetime.strptime(args.get("date_end"), '%Y-%m-%d %H:%M:%S')
    longitud = float(args.get("longitud"))
    latitude = float(args.get("latitude"))
    max_participants = int(args.get("max_participants"))
    user_creator = uuid.UUID(args.get("user_creator"))
    is_event_free = bool(args.get("is_event_free"))
    event_type = args.get("event_type")
    
    if(is_event_free == True):
        amount_event = 0
    else:
        amount_event = float(args.get("amount_event"))
    if(event_type == "PUBLIC"):
        enum_type = EventType.PUBLIC
    elif(event_type == "FRIENDS"):
        enum_type = EventType.FRIENDS
    elif(event_type == "PRIVATE"):
        enum_type = EventType.PRIVATE
  # restricion: solo puedes crear eventos para tu usuario (mirando Bearer Token)
    if str(user_creator) != auth_id:
        return jsonify({"error_message": "Un usuario no puede crear un evento por otra persona"}), 403
    try:
        new_chat = crear_public_chat(args.get("name"),user_creator,[user_creator])
        json_string = new_chat[0].response[0].decode('utf-8')
        chat_id = json.loads(json_string)[0]["id"]
    except:
        return jsonify({"error_message": "Error creating event's chat"}), 400
    
    event = Event(event_uuid, args.get("name"),enum_type, args.get("description"), date_started, date_end,
                  user_creator, longitud, latitude, max_participants,is_event_free,amount_event,chat_id)
    
    # Errores al guardar en la base de datos: FK violated, etc
    try:
        event.save()
    except sqlalchemy.exc.IntegrityError:
        return jsonify({"error_message": "User FK violated, el usuario user_creator no esta definido en la BD"}), 400
    except:
        return jsonify({"error_message": "Error de DB nuevo, cual es?"}), 400

    event_image_uris = args.get("event_image_uris")
    for event_image_uri in event_image_uris:
        event_image_uuid = uuid.uuid4()
        event_image = EventImages(event_image_uuid,event.id, event_image_uri)
        
        try:
            event_image.save()
        except Exception as e:
            
            return jsonify({"error_message": "Error de DB nuevo, cual es?"}), 400

    # Añadir el creador al evento como participante
    participant = Participant(event.id, user_creator, "thecreator")

    # Si es el primer evento que crea, darle el noob host
    increment_achievement_of_user("noob_host", user_creator)

    
    try:
        participant.save()
    except sqlalchemy.exc.IntegrityError:
        return jsonify({"error_message": "FK violated"}), 400
    except:
        return jsonify({"error_message": "Error de DB nuevo, cual es?"}), 400

    # Añadir evento al calendario del creador
    auth_id = uuid.UUID(get_jwt_identity())
    user = GoogleAuth.query.filter_by(id=auth_id).first()
    if user is not None:
        date_started_formatted = event.date_started.strftime("%Y-%m-%dT%H:%M:%S")
        date_end_formatted = event.date_end.strftime("%Y-%m-%dT%H:%M:%S")
        crearEvento(user.access_token, event.name, event.description, event.latitude, event.longitud, date_started_formatted, date_end_formatted)
    
    eventJSON = event.toJSON()
    return jsonify(eventJSON), 201


# MODIFICAR EVENTO: Modifica la información de un evento
# Recibe:
# PUT HTTP request con la id del evento en la URI y los atributos del evento en el body (formato JSON)
#       {name, description, date_started, date_end, user_creator, longitud, latitude, max_participants}
# Devuelve:
# - 400: Un objeto JSON con un mensaje de error
# - 200: Un objeto JSON con un mensaje de evento modificado con exito
@module_event_v3.route('/<id>', methods=['PUT'])
@jwt_required(optional=False)
def modify_events_v2(id):
    auth_id = get_jwt_identity()
    if BannedUsers.exists_user(auth_id):
            return jsonify({'error_message': 'This email is banned'}), 409
    try:
        event_id = uuid.UUID(id)
    except:
        return jsonify({"error_message": f"la id no es una UUID valida"}), 400

    # Parametros JSON
    try:
        args = request.json
    except:
        return jsonify({"error_message": "Mira el JSON body de la request, hay un atributo mal definido"}), 400

    try:
        event = Event.query.get(event_id)
    except:
        return jsonify({"error_message": f"El evento {event_id} ha dado un error al hacer query"}), 400

    # Si el evento no existe
    if event is None:
        return jsonify({"error_message": f"El evento {event_id} no existe"}), 400

    # Comprobar atributos de JSON para ver si estan bien
    response = check_atributes(args, "modify")
    if (response['error_message'] != "all good"):
        return jsonify(response), 400

    # restricion: solo el usuario creador puede editar su evento
    if event.user_creator != uuid.UUID(get_jwt_identity()):
        return jsonify({"error_message": "solo el usuario creador puede modificar su evento"}), 400

    # restricion: solo el usuario creador puede modificar su evento (mirando Bearer Token)
    if str(event.user_creator) != auth_id:
        return jsonify({"error_message": "A user cannot update the events of others"}), 403

    # Cambiar el calendario si el modify es correcto
    auth_id = uuid.UUID(get_jwt_identity())
    user = GoogleAuth.query.filter_by(id=auth_id).first()
    if user is not None:
        editarEventoDesciption(user.access_token, str(event.name), str(args.get("description")))
        editarEventoTitle(user.access_token, str(event.name), str(args.get("name")))
    

    event.name = args.get("name")
    event.description = args.get("description")
    event.longitud = float(args.get("longitud"))
    event.latitude = float(args.get("latitude"))
    event.max_participants = int(args.get("max_participants"))
    
    event_image_uris = set(args.get("event_image_uris"))

    old_event_images = EventImages.query.filter_by(event_id=event.id).all()
    old_event_image_uris = set(image.event_image_uri for image in old_event_images)

    # 找到需要删除的旧图片链接
    removed_images_uris = old_event_image_uris - event_image_uris
    for event_image_uri in removed_images_uris:
        # 找到需要删除的图片记录
        event_image_to_remove = next(
            image for image in old_event_images if image.event_image_uri == event_image_uri
        )
        try:
            event_image_to_remove.delete()
        except Exception as e:
            return jsonify({"error_message": "Error de DB al eliminar imágenes antiguas"}), 400

    # 添加新的图片链接
    new_images_uris = event_image_uris - old_event_image_uris
    for event_image_uri in new_images_uris:
        event_image_uuid = uuid.uuid4()
        event_image = EventImages(event_image_uuid, event.id, event_image_uri)
        try:
            event_image.save()
        except Exception as e:
            return jsonify({"error_message": "Error de DB nuevo, cual es?"}), 400

    # event.event_image_uri = args.get("event_image_uri")
    # Errores al guardar en la base de datos: FK violated, etc
    try:
        event.save()
    except sqlalchemy.exc.IntegrityError:
        return jsonify({"error_message": "User FK violated, el usuario user_creator no esta definido en la BD"}), 400
    except:
        return jsonify({"error_message": "Error de DB nuevo, cual es?"}), 400

    return jsonify({"message": "evento modificado CON EXITO"}), 200


# Metodo para comprobar los atributos pasados de un evento a crear o modificat (POST o PUT)
# Devuelve: Diccionario con un mensaje de error o un mensaje de todo bien
def check_atributes(args, type):
    # restriccion 0: Mirar si los atributos estan en el body
    if args.get("name") is None:
        return {"error_message": "atributo name no esta en el body o es null"}
    if args.get("description") is None:
        return {"error_message": "atributo description no esta en el body o es null"}
    if type != "modify":
        if args.get("date_started") is None:
            return {"error_message": "atributo date_started no esta en la URL o es null"}
        if args.get("date_end") is None:
            return {"error_message": "atributo date_end no esta en la URL o es null"}
        if args.get("user_creator") is None:
            return {"error_message": "atributo user_creator no esta en la URL o es null"}
    if args.get("longitud") is None:
        return {"error_message": "atributo longitud no esta en la URL o es null"}
    if args.get("latitude") is None:
        return {"error_message": "atributo latitud no esta en la URL o es null"}
    if args.get("max_participants") is None:
        return {"error_message": "atributo max_participants no esta en la URL o es null"}
    if args.get("event_image_uris") is None:
        return {"error_message": "atributo event_image_uris no esta en la URL o es null"}

    # restriccion 1: mirar las palabras vulgares en el nombre y la descripcion
    pf = ProfanityFilter()
    if pf.is_profane(args.get("name")):
        return {"error_message": "The name attribute is vulgar"}
    if pf.is_profane(args.get("description")):
        return {"error_message": "The description attribute is vulgar"}

    # restriccion 2: Atributos string estan vacios
    if type != "modify":
        try:
            user_creator = uuid.UUID(args.get("user_creator"))
        except ValueError:
            return {"error_message": f"user_creator id isn't a valid UUID"}
    if not isinstance(args.get("name"), str):
        return {"error_message": "name isn't a string!"}
    if not isinstance(args.get("description"), str):
        return {"error_message": "description isn't a string!"}
    if len(args.get("name")) == 0 or len(args.get("description")) == 0 or (type != "modify" and len(str(user_creator)) == 0 ):
        return {"error_message": "name, description or user_creator is empty!"}

    # restriccion 3: date started es mas grande que end date del evento (format -> 2015-06-05 10:20:10) y Comprobar Value Error
    if type != "modify":
        try:
            date_started = datetime.strptime(
                args.get("date_started"), '%Y-%m-%d %H:%M:%S')
            date_end = datetime.strptime(args.get("date_end"), '%Y-%m-%d %H:%M:%S')
            if date_started > date_end:
                return {"error_message": f"date Started {date_started} is bigger than date End {date_end}, that's not possible!"}
        except ValueError:
            return {"error_message": f"date_started or date_ended aren't real dates or they don't exist!"}

    # # restriccion 4: longitud y latitude en Catalunya y checkear Value Error
    # try:
    #     longitud = float(args.get("longitud"))
    #     latitude = float(args.get("latitude"))
    #     if max_longitud_catalunya < longitud or longitud < min_longitud_catalunya or max_latitude_catalunya < latitude or latitude < min_latitude_catalunya:
    #         return {"error_message": "location given by longitud and latitude are outside of Catalunya"}
    # except ValueError:
    #     return {"error_message": "longitud or latitude aren't floats!"}

    # restriccion 5: date started deberia ser ahora mismo o en el futuro
    if type != "modify":
      if date_started < datetime.now():
        return {"error_message": f"date Started {date_started} es antes de ahora mismo, ha comenzado ya?"}

    # restriccion 6: atributo description es mas grande que 250 characters
    if len(args.get("description")) > 250:
        return {"error_message": "Description es demasiado largo"}

    # restriccion 7: atributo name es mas grande que 25 characters
    if len(args.get("name")) > 25:
        return {"error_message": "Name es demasiado largo"}

    # TODO restriccion 8: max participants es mas grande que MAX_PARTICIPANTS_NORMAL_EVENT o es mas pequeño que 2 (creator included) y Comprobar Value Error
    try:
        max_participants = int(args.get("max_participants"))
    except ValueError:
        return {"error_message": "max participants no es un mumero"}
    if max_participants < 2:
        return {"error_message": f"el numero maximo de participantes ({max_participants}) ha de ser mas grande que 2"}

    # restriccion 9: imagen del evento no es una URL valida (pero si no hay no pasa nada)
    event_image_uris = args.get("event_image_uris")
    if event_image_uris is not None:
        for event_image_uri in event_image_uris:
            if not validators.url(event_image_uri):
                return {"error_message": "la imagen del evento no es una URL valida"}
    

    return {"error_message": "all good"}




# UNIRSE EVENTO: Usuario se une a un evento
# Recibe:
# POST HTTP request con la id del evento en la URI y el usuario que se quieran añadir al evento en el body (formato JSON)
#       {user_id}
# Devuelve:
# - 400: Un objeto JSON con un mensaje de error
# - 200: Un objeto JSON con un mensaje de el usuario se ha unido con exito
@module_event_v3.route('/<id>/join', methods=['POST'])
@jwt_required(optional=False)
def join_event(id):
    auth_id = get_jwt_identity()
    if BannedUsers.exists_user(auth_id):
            return jsonify({'error_message': 'This email is banned'}), 409
    try:
        event_id = uuid.UUID(id)
    except:
        return jsonify({"error_message": "la id del evento no es una UUID valida"}), 400

    try:
        event = Event.query.get(event_id)
    except:
        return jsonify({"error_message": f"Error al hacer query de un evento"}), 400

    if event is None:
        return jsonify({"error_message": f"El evento {event_id} no existe en la BD"}), 400

    try:
        args = request.json
    except:
        return jsonify({"error_message": "Mira el JSON body de la request, hay un atributo mal definido"}), 400

    try:
        user_id = uuid.UUID(args.get("user_id"))
    except:
        return jsonify({"error_message": f"la user_id no es una UUID valida"}), 400

    if str(user_id) != auth_id:
        return jsonify({"error_message": "A user cannot join a event for others"}), 403

    # restriccion: el usuario creador no se puede unir a su propio evento (ya se une automaticamente al crear el evento)
    if event.user_creator == user_id:
        return jsonify({"error_message": f"El usuario {user_id} es el creador del evento (ya esta dentro)"}), 400

    # restriccion: el usuario ya esta dentro del evento
    particip = Participant.query.filter_by(
        event_id=event_id, user_id=user_id).first()
    if particip is not None:
        return jsonify({"error_message": f"El usuario {user_id} ya esta dentro del evento {event_id}"}), 400

    # restriccion: el evento ya esta lleno
    num_participants = Participant.query.filter_by(event_id=event_id).all()
    if len(num_participants) >= event.max_participants:
        return jsonify({"error_message": f"El evento {event_id} ya esta lleno!"}), 400

    # restriccion: el evento ya esta pasado
    current_date = datetime.now() + timedelta(hours=2)
    if event.date_end <= current_date:
        return jsonify({"error_message": f"El evento {event_id} ya ha acabado!"}), 400
    verification_code = generate_verification_code()
    participant = Participant(event_id, user_id,verification_code)

    # Errores al guardar en la base de datos: FK violated, etc
    try:
        participant.save()
    except sqlalchemy.exc.IntegrityError:
        return jsonify({"error_message": f"FK violated, el usuario {user_id} ya se ha unido al evento o no esta definido en la BD"}), 400
    except:
        return jsonify({"error_message": "Error de DB nuevo, cual es?"}), 400

    # Si es un evento con contaminacion baja, se añade uno al achievement Social bug
    cont_level, cont_status = general_quality_at_a_point(event.longitud, event.latitude)
    if cont_status == 200:
        # Si es un evento con poca contaminacion, suma achievement Social Bug
        contaminacion = json.loads(cont_level.response[0])
        # if contaminacion["pollution"] < 0.15:
        #     increment_achievement_of_user("social_bug",user_id)

    # Se crea un chat entre el participante y el creador
    err, sts = add_member_back(event.chat_id, user_id)
    if sts != 201:
        return err, 500

    # Añadir evento al calendario del usuario
    auth_id = uuid.UUID(get_jwt_identity())
    user = GoogleAuth.query.filter_by(id=auth_id).first()
    
    if user is not None:
        date_started_formatted = event.date_started.strftime("%Y-%m-%dT%H:%M:%S")
        date_end_formatted = event.date_end.strftime("%Y-%m-%dT%H:%M:%S")
        crearEvento(user.access_token, event.name, event.description, event.latitude, event.longitud, date_started_formatted, date_end_formatted)    



    return jsonify({"message": f"el usuario {user_id} se han unido CON EXITO"}), 200


# ABANDONAR EVENTO: Usuario abandona a un evento
# Recibe:
# POST HTTP request con la id del evento en la URI y el usuario que se quieran añadir al evento en el body (formato JSON)
#       {user_id}
# Devuelve:
# - 400: Un objeto JSON con un mensaje de error
# - 200: Un objeto JSON con un mensaje de el usuario ha abandonado el evento CON EXITO
@module_event_v3.route('/<id>/leave', methods=['POST'])
@jwt_required(optional=False)
def leave_event(id):
    auth_id = get_jwt_identity()
    if BannedUsers.exists_user(auth_id):
            return jsonify({'error_message': 'This email is banned'}), 409
    try:
        event_id = uuid.UUID(id)
    except:
        return jsonify({"error_message": "la id del evento no es una UUID valida"}), 400

    try:
        event = Event.query.get(event_id)
    except:
        return jsonify({"error_message": f"Error al hacer query de un evento"}), 400

    if event is None:
        return jsonify({"error_message": f"El evento {event_id} no existe en la BD"}), 400

    try:
        args = request.json
    except:
        return jsonify({"error_message": "Mira el JSON body de la request, hay un atributo mal definido"}), 400

    try:
        user_id = uuid.UUID(args.get("user_id"))
    except:
        return jsonify({"error_message": f"la user_id no es una UUID valida"}), 400

    # restriccion: Un usuario no puede abandonar un evento por otro
    if str(user_id) != auth_id:
        return jsonify({"error_message": "A user cannot leave a event for others"}), 403

    # restriccion: el usuario no es participante del evento
    try:
        participant = Participant.query.filter_by(
            event_id=event_id, user_id=user_id).first()
    except:
        return jsonify({"error_message": f"Error en el query de participante"}), 400

    if participant is None:
        return jsonify({"error_message": f"El usuario {user_id} no es participante del evento {event_id}"}), 400

    # restriccion: el usuario creador no puede abandonar su evento
    if event.user_creator == user_id:
        return jsonify({"error_message":
                        f"El usuario {user_id} es el creador del evento (no puede abandonar)"}), 400

    # Eliminar Chat
    borrar_mensajes_usuario_chat(id_chat=event.chat_id, id_usuario=auth_id)
    remove_member_back(event.chat_id, user_id)
    # Eliminar el evento del calendario
    auth_id = uuid.UUID(get_jwt_identity())
    user = GoogleAuth.query.filter_by(id=auth_id).first()
    if user is not None:
        eliminarEventoTitle(user.access_token, event.name)

    # Errores al guardar en la base de datos: FK violated, etc
    try:
        participant.delete()
    except sqlalchemy.exc.IntegrityError:
        return jsonify({"error_message": f"FK violated, el usuario {user_id} no esta definido en la BD"}), 400
    except:
        return jsonify({"error_message": "Error de DB nuevo, cual es?"}), 400

    return jsonify({"message": f"el participante {user_id} ha abandonado CON EXITO"}), 200



# PARTICIPACIONES DE UN USER: todos los eventos a los que un usuario se ha unido
@module_event_v3.route('/joined/<id>', methods=['GET'])
# RECIBE:
# - GET HTTP request con la id del usuario que queremos solicitar
# DEVUELVE:
# - 400: Un objeto JSON con los posibles mensajes de error, id no valida o evento no existe
# - 200: Un objeto JSON con los eventos a los que se a unido
@jwt_required(optional=False)
def get_user_joins(id):
    auth_id = get_jwt_identity()
    if BannedUsers.exists_user(auth_id):
            return jsonify({'error_message': 'This email is banned'}), 409
    try:
        user_id = uuid.UUID(id)
    except:
        return jsonify({"error_message": f"The user id isn't a valid UUID"}), 400

    try:
        events_joined = Participant.query.filter_by(user_id=user_id)
    except:
        return jsonify({"error_message": "Error when querying participants"}), 400
    try:
        events = []
        current_date = datetime.now() + timedelta(hours=2)
        for ides in events_joined:
            the_event = Event.query.get(ides.event_id)
            # Solo añadir los eventos ACTIVOS
            if the_event.date_end >= current_date:
                events.append(the_event)
        return jsonify([event.toJSON() for event in events]), 200
    except:
        return jsonify({"error_message": "Unexpected error"}), 400


# OBTENER UN EVENTO: returns the information of one event
@module_event_v3.route('/<id>', methods=['GET'])
# RECIBE:
# - GET HTTP request con la id del evento del que se quieren TODOS obtener los parametros
# DEVUELVE:
# - 400: Un objeto JSON con los posibles mensajes de error, id no valida o evento no existe
# - 201: Un objeto JSON con TODOS los parametros del evento con la id de la request
@jwt_required(optional=False)
def get_event(id):
    auth_id = get_jwt_identity()
    if BannedUsers.exists_user(auth_id):
            return jsonify({'error_message': 'This email is banned'}), 409
    try:
        event_id = uuid.UUID(id)
    except:
        return jsonify({"error_message": f"The event id isn't a valid UUID"}), 400

    try:
        event = Event.query.get(event_id)
    except:
        return jsonify({"error_message": f"The event {event_id} doesn't exist"}), 400
    creator = User.query.get(event.user_creator)
    if not creator:
        return jsonify({"error_message": "Event creator not found"}), 404
    event_data = event.toJSON()
    event_data['creator_name'] = creator.username
    event_data['creator_image_url'] = creator.image_url
    return jsonify(event_data), 200


# OBTENER EVENTOS POR USUARIO CREADOR method: devuelve todos los eventos creados por un usuario
@module_event_v3.route('/creator', methods=['GET'])
# RECIBE:
# - GET HTTP request con la id del usuario del que se quieren obtener los eventos creados como query parameter.
# - 400: Un objeto JSON con los posibles mensajes de error, id no valida
# - 201: Un objeto JSON con TODOS los parametros del evento con la id de la request
@jwt_required(optional=False)
def get_creations():
    auth_id = get_jwt_identity()
    if BannedUsers.exists_user(auth_id):
            return jsonify({'error_message': 'This email is banned'}), 409
    try:
        args = request.args
    except:
        return jsonify({"error_message": "Error loading args"}), 400

    try:
        if args.get("userid") is None:
            return jsonify({"error_message": "the id of the user isn't in the URL as a query parameter with name userid :("}), 400
        else:
            user_id = uuid.UUID(args.get("userid"))
    except:
        return jsonify({"error_message": "userid isn't a valid UUID"}), 400

    user = User.query.get(user_id)
    if user is None:
        return jsonify({"error_message": f"User {user_id} doesn't exist"}), 400

    try:
        events_creats = Event.query.filter_by(user_creator=user_id)
        current_date = datetime.now() + timedelta(hours=2)
        active_events = []
        if events_creats is not None:
            if events_creats.count() == 0:

                return jsonify(""), 200
         # Solo añadir los eventos ACTIVOS
        for event in events_creats: 
            if event.date_end >= current_date:
                active_events.append(event)
        return jsonify([event.toJSON() for event in active_events]), 200
    except:
        return jsonify({"error_message": "An unexpected error ocurred"}), 400


# DELETE EVENTO method: deletes an event from the database
@module_event_v3.route('/<id>', methods=['DELETE'])
# RECIBE:
# - DELETE HTTP request con la id del evento que se quiere eliminar
# DEVUELVE:
# - 400: Un objeto JSON con los posibles mensajes de error, id no valida o evento no existe
# - 200: Un objeto JSON confirmando que se ha eliminado correctamente
@jwt_required(optional=False)
def delete_event(id):
    auth_id = get_jwt_identity()
    if BannedUsers.exists_user(auth_id):
            return jsonify({'error_message': 'This email is banned'}), 409
    try:
        event_id = uuid.UUID(id)
    except:
        return jsonify({"error_message": "Event_id isn't a valid UUID"}), 400

    try:
        event = Event.query.get(event_id)
    except:
        return jsonify({"error_message": f"Error getting the event"}), 400

    if event is None:
        return jsonify({"error_message": f"The event {event_id} doesn't exist"}), 400

    # restricion: solo el usuario creador puede eliminar su evento (o un admin) (mirando Bearer Token)
    if str(event.user_creator) != auth_id and not Admin.exists(auth_id):
        return jsonify({"error_message": "A user cannot delete events if they are not the creator"}), 403

    # Eliminar todos los participantes del evento ANTES DE ELIMINAR EL EVENTO
    try:
        participants = Participant.query.filter_by(event_id=event_id).all()
    except:
        return jsonify({"error_message": "error while querying participants of an event"}), 400

    for p in participants:
        try:
            p.delete()
        except:
            return jsonify({"error_message": "error while deleting participants of an event"}), 400

    # Eliminar todos los likes del evento ANTES DE ELIMINAR EL EVENTO
    try:
        likes = Like.query.filter_by(event_id=event_id).all()
    except:
        return jsonify({"error_message": "error while querying likes of an event"}), 400

    for l in likes:
        try:
            l.delete()
        except:
            return jsonify({"error_message": "error while deleting likes of an event"}), 400

   # Eliminar las reviews de un evento ANTES DE ELIMINAR EL EVENTO
    try:
        reviews = Review.query.filter_by(event_id=event_id).all()
    except:
        return jsonify({"error_message": "error while querying likes of an event"}), 400

    for r in reviews:
        try:
            r.delete()
        except:
            return jsonify({"error_message": "error while deleting reviews of an event"}), 400

    # Eliminar chat
    borrar_mensajes_y_evento(event.id)

    # Eliminar el evento del calendario
    auth_id = uuid.UUID(get_jwt_identity())
    user = GoogleAuth.query.filter_by(id=auth_id).first()
    if user is not None:
        eliminarEventoTitle(user.access_token, event.name)


    try:
        event.delete()
        return jsonify({"error_message": "Successful DELETE"}), 202
    except:
        return jsonify({"error_message": "error while deleting the event"}), 400


# GET ALL EVENTOS ACTIVOS method: retorna toda la informacion de todos los eventos activos de la database
@module_event_v3.route('/', methods=['GET'])
# RECIBE:
# - GET HTTP request
# DEVUELVE:
# - 400: Un objeto JSON con los posibles mensajes de error
# - 201: Un objeto JSON con todos los eventos activos que hay en el sistema
@jwt_required(optional=False)
def get_all_events():
    user_id = uuid.UUID(get_jwt_identity())
    if BannedUsers.exists_user(user_id):
            return jsonify({'error_message': 'This email is banned'}), 409
    try:
        # La data de ahora es en GMT+2 por lo tanto tenemos que sumar dos horas en el tiempo actual
        current_date = datetime.now() + timedelta(hours=2)
        active_events = Event.query.filter(Event.date_end >= current_date)
    except:
        return jsonify({"error_message": "Error when querying events"}), 400
    
    filtered_events = []

    for event in active_events:
        participant = Participant.query.filter_by(event_id=event.id, user_id=user_id).first()
        if participant is None:
            if event.event_type == EventType.PRIVATE:
                if event.user_creator != user_id:
                    continue
            if event.event_type == EventType.FRIENDS:
                if event.user_creator != user_id:
                    friends = Friend.getFriendsOfUserId(event.user_creator)
                    is_friend = any(friend.id == user_id for friend in friends)
                    if not is_friend:
                        continue
        filtered_events.append(event)

    try:
        return jsonify([event.toJSON() for event in filtered_events]), 200
    except:
        return jsonify({"error_message": "Unexpected error when passing events to JSON format"}), 400

# FILTRAR EVENTO: Retorna un conjunto de eventos en base a unas caracteristicas
# Recibe:
# GET HTTP request con los atributos que quiere filtrar (formato JSON)
#       {name, date_started, date_end}
# Devuelve:
@module_event_v3.route('/filter', methods=['GET'])
@jwt_required(optional=False)
def filter_by():
    auth_id = get_jwt_identity()
    if BannedUsers.exists_user(auth_id):
            return jsonify({'error_message': 'This email is banned'}), 409
    try:
        args = request.json
    except:
        return jsonify({"error_message": "The JSON body from the request is poorly defined"}), 400

    if args.get("name") is not None:
        if len(args.get("name")) == 0:
            return {"error_message": "The name is not defined!"}

    if args.get("date_started") is not None or args.get("date_end") is not None:
        try:
            date_start_interval = datetime.strptime(
                args.get("date_started"), '%Y-%m-%d %H:%M:%S')
            date_end_interval = datetime.strptime(
                args.get("date_end"), '%Y-%m-%d %H:%M:%S')
            if date_start_interval > date_end_interval:
                return {"error_message": "The start date must be greater than the end date"}
            if date_start_interval == date_end_interval:
                return {"error_message": "The start date and the end date are the same"}
            if date_start_interval < datetime.now():
                return {"error_message": "Date_started is before the now time"}
        except ValueError:
            return {"error_message": "date_started or date_ended aren't real dates or they don't exist!"}

    try:
        events_filter = None
        if args.get("name") is not None:
            events_filter = Event.filter_by(name=args.get["name"])

        if args.get("date_started") is not None and args.get("name") is not None:
            events_filter = events_filter.filter_by(
                Event.date_started >= date_start_interval, Event.date_started <= date_end_interval, Event.date_end <= date_end_interval, )
        elif args.get("date_started") is not None:
            events_filter = Event.filter_by(Event.date_started >= date_start_interval,
                                            Event.date_started <= date_end_interval, Event.date_end <= date_end_interval, )

        if events_filter is None:
            return jsonify({"error_message": "Any event match with the filter"}), 400
        else:
            return jsonify([event.toJSON() for event in events_filter]), 200
    except Exception as e:
        return jsonify({"error_message": "hello"}), 400


# OBTENER LOS 10 EVENTOS CREAS MAS RECIENTEMENTE method: Retorna un conjunto con los 10 eventos mas recientes
@module_event_v3.route('/lastten', methods=['GET'])
@jwt_required(optional=False)
def lastest_events():
    user_id = uuid.UUID(get_jwt_identity())
    
    if BannedUsers.exists_user(user_id):
            return jsonify({'error_message': 'This email is banned'}), 409
    try:
        # La data de ahora es en GMT+2 por lo tanto tenemos que sumar dos horas en el tiempo actual
        current_date = datetime.now() + timedelta(hours=2)
        lasts_events = Event.query.filter(Event.date_end >= current_date).order_by(Event.date_creation.desc()).all()
    except:
        return {"error_message": "Error while querying events"}
    user_id = uuid.UUID(get_jwt_identity())
    
    if BannedUsers.exists_user(user_id):
            return jsonify({'error_message': 'This email is banned'}), 409
    lastten = []
    i = 0
    for event in lasts_events:
        if i < 10:
            participant = Participant.query.filter_by(event_id=event.id, user_id=user_id).first()
            if(participant is not None or event.user_creator == user_id):
                lastten.append(event)
            else:
                if(event.event_type == EventType.PUBLIC):
                    lastten.append(event)
                elif(event.event_type == EventType.FRIENDS):
                    friends = Friend.getFriendsOfUserId(event.user_creator)
                    for friend in friends:
                        if(friend.id == user_id):
                            lastten.append(event)
            i += 1
        else:
            break

    return jsonify([event.toJSON() for event in lastten]), 200


# SABER QUE PERSONAS SE HAN UNIDO A UN EVENTO method: Retorna el conjunto de users que se han unido a un evento
@module_event_v3.route('/participants', methods=['GET'])
@jwt_required(optional=False)
def who_joined_event():
    auth_id = get_jwt_identity()
    if BannedUsers.exists_user(auth_id):
            return jsonify({'error_message': 'This email is banned'}), 409
    try:
        args = request.args
    except:
        return jsonify({"error_message": "Error loading args"}), 400

    try:
        if args.get("eventid") is None:
            return jsonify({"error_message": "the id of the event isn't in the URL as a query parameter with name eventid :("}), 400
        else:
            event_id = uuid.UUID(args.get("eventid"))
    except:
        return jsonify({"error_message": "eventid isn't a valid UUID"}), 400

    try:
        event = Event.query.get(event_id)
    except:
        return jsonify({"error_message": f"Error getting the event"}), 400

    if event is None:
        return jsonify({"error_message": f"The event {event_id} doesn't exist"}), 400

    # TODO todos pueden acceder a esta info?

    try:
        participants = Participant.query.filter_by(event_id=event_id)
    except:
        return jsonify({"error_message": "Error when querying participants"}), 400

    participant_list = []

    for p in participants:
        participant_list.append(p.user_id)

    return jsonify(participant_list), 200


# LISTAR TODOS LOS EVENTOS PASADOS DE UN USUARIO:
@module_event_v3.route('/pastevents', methods=['GET'])
# DEVUELVE:
# - 400: Un objeto JSON con los posibles mensajes de error, id no valida o evento no existe
# - 200: Un objeto JSON con los atributos de la review creada
@jwt_required(optional=False)
def get_past_evento():
    try:
        args = request.args
    except:
        return jsonify({"error_message": "Error loading args"}), 400

    # restriccion: el user id tiene que estar en la URL y ser una UUID valida
    try:
        if args.get("userid") is None:
            return jsonify({"error_message": "the id of the user isn't in the URL as a query parameter with name userid :("}), 400
        else:
            user_id = uuid.UUID(args.get("userid"))
    except:
        return jsonify({"error_message": "eventid isn't a valid UUID"}), 400
    
    # restriccion: el user ha de existir
    try:
        user = User.query.get(user_id)
        if user is None:
            return jsonify({"error_message": f"User {user_id} doesn't exist"}), 400
    except:
        return jsonify({"error_message": f"user {user} doesn't exist"}), 400

    # restricion: solo el usuario creador puede eliminar su evento (mirando Bearer Token)
    auth_id = get_jwt_identity()
    if BannedUsers.exists_user(auth_id):
            return jsonify({'error_message': 'This email is banned'}), 409
    if str(user_id) != auth_id:
        return jsonify({"error_message": "A user cannot see the events that another user participated in"}), 403


    # if events_of_participant is None, it means that the user doesn't participate in any event
    events_of_participant = Participant.query.filter_by(user_id=user_id)

    # La data de ahora es en GMT+2 por lo tanto tenemos que sumar dos horas en el tiempo actual
    current_date = datetime.now() + timedelta(hours=2)
    past_events = []        

    for ev in events_of_participant:
        try:
            the_event = Event.query.get(ev.event_id)
            # eventos de un participantes NO INCLUYEN tus eventos
            if the_event.user_creator != user_id:
                if the_event.date_end <= current_date:
                    past_events.append(the_event)
        except:
            return jsonify({"error_message": "Error when querying events"}), 400

    try:
        return jsonify([event.toJSON() for event in past_events]), 200
    except:
        return jsonify({"error_message": "Unexpected error when passing events to JSON format"}), 400




########################################################################### O T R O S ########################################################

#  genera un codigo de verificacion para un evento
def generate_verification_code():
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    verification_code = ''.join(secrets.choice(alphabet) for _ in range(6))  # 生成一个包含 6 个字符的验证码
    return verification_code

# If the event doesn't exist
@module_event_v3.errorhandler(404)
def page_not_found():
    return "<h1>404</h1><p>The event could not be found.</p>", 404


@module_event_v3.teardown_request
def teardown_request(exception):
    if exception:
        db.session.rollback()
    db.session.remove()


########################################################################### L I K E S #############################################################


# DAR LIKE method: un usuario le da like a un evento
@module_event_v3.route('/<id>/like', methods=['POST'])
# RECIBE:
# - POST HTTP request con los parametros en un JSON object en el body de la request.
# DEVUELVE:
# - 400: Un objeto JSON con un mensaje de error
@jwt_required(optional=False)
def create_like(id):
    try:
        args = request.json
    except:
        return jsonify({"error_message": "Mira el JSON body de la request, hay un atributo mal definido"}), 400

    try:
        user_id = uuid.UUID(args.get("user_id"))
    except:
        return jsonify({"error_message": "User_id isn't a valid UUID"}), 400

    # Un usuario solo puede dar like por si mismo
    auth_id = get_jwt_identity()
    if BannedUsers.exists_user(auth_id):
            return jsonify({'error_message': 'This email is banned'}), 409
    if str(user_id) != auth_id:
        return jsonify({"error_message": "A user can't like for others"}), 403

    try:
        event_id = uuid.UUID(id)
    except:
        return jsonify({"error_message": "Event_id isn't a valid UUID"}), 400

    # Mirar si el evento existe
    find_event = Event.query.get(event_id)
    if find_event is None:
        return jsonify({"error_message": f"The event {event_id} doesn't exist"}), 400

    Nuevo_like = Like(user_id, event_id)

    try:
        Nuevo_like.save()
    except sqlalchemy.exc.IntegrityError:
        return jsonify({"error_message": "El usuario ya ha dado like a este evento"})
    except:
        return jsonify({"error_message": "Error nuevo de base de datos, ¿cual es?"})

    LikeJSON = Nuevo_like.toJSON()
    return jsonify(LikeJSON), 201


# QUITAR LIKE method: deletes a like from the database
@module_event_v3.route('/<id>/dislike', methods=['POST'])
# RECIBE:
# - DELETE HTTP request con la id del evento que se quiere eliminar
# DEVUELVE:
# - 400: Un objeto JSON con los posibles mensajes de error, id no valida o evento no existe
# - 200: Un objeto JSON confirmando que se ha eliminado correctamente
@jwt_required(optional=False)
def delete_like(id):
    try:
        args = request.json
    except:
        return jsonify({"error_message": "Mira el JSON body de la request, hay un atributo mal definido"}), 400

    try:
        delete_user_id = uuid.UUID(args.get("user_id"))
    except:
        return jsonify({"error_message": "User_id isn't a valid UUID"}), 400

    auth_id = get_jwt_identity()
    if BannedUsers.exists_user(auth_id):
            return jsonify({'error_message': 'This email is banned'}), 409
    if str(delete_user_id) != auth_id:
        return jsonify({"error_message": "A user can't remove likes for others"}), 403

    try:
        delete_event_id = uuid.UUID(id)
    except:
        return jsonify({"error_message": "Event_id isn't a valid UUID"}), 400

    event = Event.query.get(delete_event_id)
    if event is None:
        return jsonify({"error_message": f"The event {str(delete_event_id)} doesn't exist"}), 400

    try:
        Like_borrar = Like.query.filter_by(
            user_id=delete_user_id, event_id=delete_event_id).first()
        Like_borrar.delete()
        return jsonify({"message": "Successful DELETE"}), 200
    except:
        return jsonify({"error_message": f"The like of user {delete_user_id} in event {delete_event_id} doesn't exist"}), 400


# LIKES DE UN USER: todos los eventos a los que un usuario ha dado like
@module_event_v3.route('/like/<iduser>', methods=['GET'])
# RECIBE:
# - GET HTTP request con la id del usuario que queremos solicitar
# DEVUELVE:
# - 400: Un objeto JSON con los posibles mensajes de error, id no valida o evento no existe
# - 200: Un objeto JSON confirmando que se ha eliminado correctamente
@jwt_required(optional=False)
def get_likes_by_user(iduser):
    try:
        user_id = uuid.UUID(iduser)
    except:
        return jsonify({"error_message": "User_id isn't a valid UUID"}), 400

    # No todos los usuarios pueden conseguir esta info (ESTO YA MIRA SI EL USUARIO EXISTE O NO, PQ LO COMPARA CON EL TOKEN QUE ES UN USUARIO QUE EXISTE SEGURO)
    auth_id = get_jwt_identity()
    
    if BannedUsers.exists_user(auth_id):
            return jsonify({'error_message': 'This email is banned'}), 409
    if str(user_id) != auth_id:
        return jsonify({"error_message": "A user can't get the likes of the events of someone else"}), 403

    try:
        likes_user = Like.query.filter_by(user_id=user_id)
    except:
        return jsonify({"error_message": "Error when querying likes"}), 400
    try:
        events = []
        current_date = datetime.now() + timedelta(hours=2)
        for i in likes_user:
            the_event = Event.query.get(i.event_id)
            # Solo añadir los eventos ACTIVOS
            if the_event.date_end >= current_date:
                events.append(the_event)
        return jsonify([event.toJSON() for event in events]), 200
    except:
        return jsonify({"error_message": "Unexpected error"}), 400


# SABER SI USUARIO HA DADO LIKE A UN EVENTO method: saber si un usuario ha dado like a un evento
@module_event_v3.route('/<iduser>/like/<idevento>', methods=['GET'])
# RECIBE:
# - GET HTTP request con la id del usuario que queremos consultar
# DEVUELVE:
# - 400: Un objeto JSON con los posibles mensajes de error, id no valida o evento no existe
# - 200: Un objeto JSON confirmando que se ha eliminado correctamente
@jwt_required(optional=False)
def get_likes_from_user(iduser, idevento):
    auth_id = get_jwt_identity()
    if BannedUsers.exists_user(auth_id):
            return jsonify({'error_message': 'This email is banned'}), 409
    try:
        user_id_q = uuid.UUID(iduser)
    except:
        return jsonify({"error_message": "User_id isn't a valid UUID"}), 400

    user = User.query.get(user_id_q)
    if user is None:
        return jsonify({"error_message": f"User {user_id_q} doesn't exist"}), 400

    try:
        event_id_q = uuid.UUID(idevento)
    except:
        return jsonify({"error_message": "Event_id isn't a valid UUID"}), 400

    event = Event.query.get(event_id_q)
    if event is None:
        return jsonify({"error_message": f"Event {event_id_q} doesn't exist"}), 400

    try:
        liked = Like.query.filter_by(
            user_id=user_id_q, event_id=event_id_q).first()
    except:
        return jsonify({"error_message": "Error while querying Like"}), 400

    if liked is None:
        return jsonify({"message": "No le ha dado like"}), 200
    else:
        return jsonify({"message": "Le ha dado like"}), 200


# DIEZ EVENTOS CON MAYOR NUMERO DE LIKES: los 10 eventos con el mayor numero de likes
@module_event_v3.route('/topten', methods=['GET'])
# DEVUELVE:
# - 400: Un objeto JSON con los posibles mensajes de error, id no valida o evento no existe
# - 200: Un objeto JSON con los top 10 eventos con mas likes
@jwt_required(optional=False)
def get_top_ten_events():
    auth_id = get_jwt_identity()
    if BannedUsers.exists_user(auth_id):
            return jsonify({'error_message': 'This email is banned'}), 409
    db_uri = current_app.config.get('SQLALCHEMY_DATABASE_URI')
    engine = create_engine(db_uri)
    sql_query = db.text("select e.id, e.name, e.description, e.date_started, e.date_end, e.date_creation, e.user_creator, e.longitud, e.latitude, e.max_participants, e.is_event_free from events e left join likes l on e.id = l.event_id where e.date_end >= CURRENT_TIMESTAMP group by e.id order by count(distinct l.user_id) desc;")
    with engine.connect() as conn:
        result_as_list = conn.execute(sql_query).fetchall() 
        
    user_id = uuid.UUID(get_jwt_identity())
    top_ten_with_info = []
    i = 0
    for result in result_as_list:
        if i < 10:
            event_data = dataToJSON(result)
            str_event_id = str(event_data["id"])
            event_id = uuid.UUID(str_event_id)
            event = Event.query.filter_by(id=event_id).first()
            participant = Participant.query.filter_by(event_id=event.id, user_id=user_id).first()
            if(participant is not None or event.user_creator == user_id):
                top_ten_with_info.append(event)
                i += 1
            else:
                if(event.event_type == EventType.PUBLIC):
                    top_ten_with_info.append(event)
                    i += 1
                elif(event.event_type == EventType.FRIENDS):
                    friends = Friend.getFriendsOfUserId(event.user_creator)
                    for friend in friends:
                        if(friend.id == user_id):
                            top_ten_with_info.append(event)
                            i += 1
            
    return jsonify([e.toJSON() for e in top_ten_with_info]), 200


def dataToJSON(data):
    return {
        "id": data[0],
        "name": data[1],
        "description": data[2],
        "date_started": data[3],
        "date_end": data[4],
        "date_creation": data[5],
        "user_creator": data[6],
        "longitud": data[7],
        "latitude": data[8],
        "max_participants": data[9],
        "is_event_free": data[10]
    }

########################################################################### R E V I E W S ##################################################################

# CREAR REVIEW: crear una review de un evento
@module_event_v3.route('/review', methods=['POST'])
# DEVUELVE:
# - 400 o 403: Un objeto JSON con los posibles mensajes de error, id no valida o evento no existe
# - 200: Un objeto JSON con los atributos de la review creada
@jwt_required(optional=False)
def crear_review():
    try:
        args = request.json
    except:
        return jsonify({"error_message": "Mira el JSON body de la request, hay un atributo mal definido"}), 400

    # restriccion 0: Mirar si los atributos estan en el body
    if args.get("event_id") is None:
        return {"error_message": "atributo event_id no esta en el body o es null"}
    if args.get("user_id") is None:
        return {"error_message": "atributo user_id no esta en el body o es null"}
    if args.get("comment") is None:
        return {"error_message": "atributo comment no esta en el body, es null o esta vacio"}
    if args.get("rating") is None:
        return {"error_message": "atributo rating no esta en el body, es null"}

    # restriccion 1: event_id tiene que ser una UUID valida y tiene que existir
    try:
        event_id = uuid.UUID(args.get("event_id"))
    except:
        return jsonify({"error_message": "Event_id isn't a valid UUID"}), 400

    event = Event.query.get(event_id)
    if event is None:
        return jsonify({"error_message": f"Event {event_id} doesn't exist"}), 400

    # restriccion 2: El user_id tiene que ser una UUID valida
    try:
        user_id = uuid.UUID(args.get("user_id"))
    except:
        return jsonify({"error_message": "User_id isn't a valid UUID"}), 400

    # restriccion 3: Un usuario no puede dar una review por otra persona (por extra seguridad). Tmb implicitamente comprovamos si el usuario existe
    auth_id = get_jwt_identity()
    
    if BannedUsers.exists_user(auth_id):
            return jsonify({'error_message': 'This email is banned'}), 409
    if str(user_id) != auth_id:
        return jsonify({"error_message": "A user can't create a review for others"}), 403

    # restriccion 4: el comentario tiene que ser una string y no puede ser mas largo que 500 caracteres
    if not isinstance(args.get("comment"), str):
        return {"error_message": "comment isn't a string!"}
    if len(args.get("comment")) == 0:
        return {"error_message": "comment can't be empty!"}
    if len(args.get("comment")) > 500:
        return {"error_message": "el comentario es demasiado largo, pasa los 500 caracteres"}

    # restriccion 5: Un rating ha de ser un integer entre 0 y 5
    try:
        rating = int(args.get("rating"))
    except ValueError:
        return jsonify({"error_message": "rating isn't an integer"}), 400
    if rating < 0 or rating > 5:
        return {"error_message": f"el rating de la review ({rating}) ha de ser mas grande que 0 y menos que 5"}

    # restriccion 6: el usuario ha de ser participante del evento (como eliminamos el participante despues de la review, no pueden estar duplicadas!)
    participant = Participant.query.filter_by(
        event_id=event_id, user_id=user_id).first()
    if participant is None:
        return jsonify({"error_message": f"El usuario {user_id} no es participante del evento {event_id}"}), 400

    # restriccion 7: el creador del evento no puede dar una review a su propio evento
    if user_id == event.user_creator:
        return jsonify({"error_message": "El creador del evento no puede dar una review a su propio evento"}), 400

    new_rating = Review(user_id=user_id, event_id=event_id,
                        rating=rating, comment=args.get("comment"))

    # Errores al guardar en la base de datos: FK violated, etc
    try:
        new_rating.save()
    except sqlalchemy.exc.IntegrityError:
        return jsonify({"error_message": "Integrity error, FK violated (algo no esta definido en la BD) o ya existe la review en la DB"}), 400
    except:
        return jsonify({"error_message": "Error de DB nuevo, cual es?"}), 400


    # Si es la primera review de un usuario, darle el logro feedback monster
    # increment_achievement_of_user("feedback_monster", user_id)

    # Devolver nueva review en formato JSON si todo ha funcionado correctamente
    ratingJSON = new_rating.toJSON()
    return jsonify(ratingJSON), 201


# LISTAR TODAS LAS REVIEW DE UN EVENTO: crear una review de un evento
@module_event_v3.route('/review', methods=['GET'])
# DEVUELVE:
# - 400: Un objeto JSON con los posibles mensajes de error, id no valida o evento no existe
# - 200: Un objeto JSON con los atributos de la review creada
@jwt_required(optional=False)
def get_reviews_evento():  
    auth_id = uuid.UUID(get_jwt_identity())
    if BannedUsers.exists_user(auth_id):
            return jsonify({'error_message': 'This email is banned'}), 409
    try:
        args = request.args
    except:
        return jsonify({"error_message": "Error loading args"}), 400

    # restriccion: el evento tiene que estar en la URL, ser una UUID valida y ha de existir
    try:
        if args.get("eventid") is None:
            return jsonify({"error_message": "the id of the event isn't in the URL as a query parameter with name eventid :("}), 400
        else:
            event_id = uuid.UUID(args.get("eventid"))
    except:
        return jsonify({"error_message": "eventid isn't a valid UUID"}), 400

    event = Event.query.get(event_id)
    if event is None:
        return jsonify({"error_message": f"Event {event_id} doesn't exist"}), 400
    
    user = User.query.filter_by(id = event.user_creator).first()
    
    try:
        reviews = Review.query.filter_by(event_id=event_id)
    except:
        return jsonify({"error_message": "Error querying the reviews"}), 400
    
    review_list = []

    for r in reviews:
        review_list.append(r)

    return jsonify({'event': event.toJSON(), 'username': user.username, 'email': user.email, 'reviews': [review.toJSON() for review in reviews]}), 200

# add payment data of event
@module_event_v3.route('/add_payment', methods=['Post'])
# DEVUELVE:
# - 400: Un objeto JSON con los posibles mensajes de error, id no valida o evento no existe
# - 200: Un objeto JSON con los atributos de la review creada
@jwt_required(optional=False)
def add_payment():  
    # restriccion: el evento tiene que estar en la URL, ser una UUID valida y ha de existir
    try:
        if "event_id" not in request.json:
            return jsonify({"error_message": "add_paymentthe id of the event isn't in the URL as a query parameter with name eventid :("}), 400
        else:
            event_id = uuid.UUID(request.json['event_id'])
    except:
        return jsonify({"error_message": "event_id isn't a valid UUID"}), 400

    event = Event.query.get(event_id)
    if event is None:
        return jsonify({"error_message": f"Event {event_id} doesn't exist"}), 400
    
    auth_id = uuid.UUID(get_jwt_identity())
    
    if BannedUsers.exists_user(auth_id):
            return jsonify({'error_message': 'This email is banned'}), 409
    if(auth_id == event.user_creator):
        return jsonify({"error_message": f"User {auth_id} is the creator of the event"}), 400
    if "amount" not in request.json:
        return jsonify({"error_message": "the amount of the payment isn't in the URL as a query parameter with name eventid :("}), 400
    else:
        amount = float(request.json['amount'])
        if(event.amount_event != amount):
            return jsonify({"error_message": f"Amount paid is not the same as the event amount"}), 400
        
    if "payment_type" not in request.json:
        return jsonify({"error_message": "the type of the payment isn't in the URL as a query parameter with name eventid :("}), 400
    if "payment_id" not in request.json:
        return jsonify({"error_message": "the id of the payment isn't in the URL as a query parameter with name eventid :("}), 400
    
    aux_payment = Payment.query.filter_by(
        event_id=event_id, user_id=auth_id,status=PaymentStatus.PAID).first()
    if aux_payment is not None:
        return jsonify({"error_message": f"User {auth_id} already paid for this event"}), 400

    new_payment = Payment(event_id=event_id, user_id=auth_id, payment_type=request.json['payment_type'], payment_id=request.json['payment_id'], amount=amount, status = PaymentStatus.PAID)

    try:
        new_payment.save()
    except sqlalchemy.exc.IntegrityError:
        return jsonify({"error_message": "Integrity error, FK violated (algo no esta definido en la BD) o ya existe la payment en la DB"}), 400
    except:
        return jsonify({"error_message": "Error de DB nuevo, cual es?"}), 400
    return new_payment.toJSON(), 201

# get payment data of event
@module_event_v3.route('/<id>/get_payment', methods=['Get'])
# DEVUELVE:
# - 400: Un objeto JSON con los posibles mensajes de error, id no valida o evento no existe
# - 200: Un objeto JSON con los atributos de la review creada
@jwt_required(optional=False)
def get_payment(id):  
    
    try:
        event_id = uuid.UUID(id)
    except:
        return jsonify({"error_message": "event_id isn't a valid UUID"}), 400
    try:
        auth_id = uuid.UUID(get_jwt_identity())
    except:
        return jsonify({"error_message": "auth_id isn't a valid UUID"}), 400
    if BannedUsers.exists_user(auth_id):
            return jsonify({'error_message': 'This email is banned'}), 409
    aux_payment = Payment.query.filter_by(
        event_id=event_id, user_id=auth_id,status=PaymentStatus.PAID).first()
    if aux_payment is None:
        return jsonify({"error_message": "No payment found"}), 400
    
    return aux_payment.toJSON(), 200
# return jsonify(aux_payment.toJSON()), 200
# get all payment data of event
@module_event_v3.route('/<id>/get_all_payments', methods=['Get'])
# DEVUELVE:
# - 400: Un objeto JSON con los posibles mensajes de error, id no valida o evento no existe
# - 200: Un objeto JSON con los atributos de la review creada
@jwt_required(optional=False)
def get_all_payments(id):  
    try:
        event_id = uuid.UUID(id)
    except:
        return jsonify({"error_message": "event_id isn't a valid UUID"}), 400
    try:
        auth_id = uuid.UUID(get_jwt_identity())
    except:
        return jsonify({"error_message": "event_id isn't a valid UUID"}), 400
    
    if BannedUsers.exists_user(auth_id):
            return jsonify({'error_message': 'This email is banned'}), 409
    event = Event.query.get(id)
    # if(auth_id != event.user_creator):
    #     return jsonify({"warning_message": f"User {auth_id} is not the creator of the event"}), 200
    
    aux_payments = Payment.query.filter_by(
        event_id=event_id, status = PaymentStatus.PAID).all()

    return jsonify([payment.toJSON() for payment in aux_payments]), 200

# get all post without parent of event
@module_event_v3.route('/<id>/post/', methods=['Get'])
def get_posts_without_parent(id): 
    try: 
        try:
            event_id = uuid.UUID(id)
        except:
            return jsonify({"error_message": "event_id isn't a valid UUID"}), 400
        posts_without_parent = EventPosts.query.filter_by(event_id=event_id, parent_post_id = None).all()

        # for post_without_parent in posts_without_parent:
        #     images = PostImages.query.filter_by(post_id=post_without_parent.id).all()
        #     post_images_uris = []
        #     for image in images:
        #         post_images_uris.append(image.post_image_uri)
            
        #     post_without_parent.post_image_uris = post_images_uris
        #     
        # a = posts_without_parent[0]
        # ipdb.set_trace()  
        return jsonify([post_without_parent.toJSON() for post_without_parent in posts_without_parent]), 200
    except:
        return jsonify({"error_message": "Unexpected error"}), 400

# post a post of event
@module_event_v3.route('/<id>/post/', methods=['Post'])
@jwt_required(optional=False)
def post_a_post(id): 
    try: 
        try:
            event_id = uuid.UUID(id)
        except:
            return jsonify({"error_message": "event_id isn't a valid UUID"}), 400
        try:
            args = request.json
        except:
            return jsonify({"error_message": "Mira el JSON body de la request, hay un atributo mal definido"}), 400
        
        auth_id = uuid.UUID(get_jwt_identity())
        if BannedUsers.exists_user(auth_id):
            return jsonify({'error_message': 'This email is banned'}), 409
        if args.get("parent_post_id") is None:
            return jsonify({"error_message": "parent_post_id is invalid"}), 400
        if args.get("text") is None:
            return jsonify({"error_message": "text isn't is invalid"}), 400
        if args.get("post_image_uris") is None:
            return jsonify({"error_message": "post_image_uris isn't is invalid"}), 400
        if args.get("parent_post_id") == "":
            parent_post_id = None
        new_post = EventPosts(parent_post_id=parent_post_id, event_id=event_id, user_id=auth_id, text=args.get("text"))
        try:
            new_post.save()
            for post_image_uri in args.get("post_image_uris"):
                new_post_image = PostImages(post_id=new_post.id, post_image_uri=post_image_uri)
                new_post_image.save()
        except sqlalchemy.exc.IntegrityError:
            return jsonify({"error_message": "Integrity error, FK violated (algo no esta definido en la BD) o ya existe la payment en la DB"}), 400
        except:
            return jsonify({"error_message": "Error de DB nuevo, cual es?"}), 400
        return new_post.toJSON(), 200
    except:
        return jsonify({"error_message": "Unexpected error"}), 400
# get all children-post of post of event
@module_event_v3.route('/<id>/post/<post_id>', methods=['Get'])
def get_children_post(id, post_id): 
    try: 
        try:
            event_id = uuid.UUID(id)
        except:
            return jsonify({"error_message": "event_id isn't a valid UUID"}), 400
        
        children_post = EventPosts.query.filter_by(event_id=event_id, parent_post_id = post_id).all()
        return jsonify([child_post.toJSON() for child_post in children_post]), 200
    except:
        return jsonify({"error_message": "Unexpected error"}), 400

# like a post
@module_event_v3.route('/<id>/post/<post_id>/like', methods=['Put'])
@jwt_required(optional=False)
def put_like_post(id,post_id):
    
    try:
        event_id = uuid.UUID(id)
    except:
        return jsonify({"error_message": "Event_id isn't a valid UUID"}), 400
    event = Event.query.get(event_id)
    if event is None:
        return jsonify({"error_message": f"Event {event_id} doesn't exist"}), 400

    user_id = get_jwt_identity()
    if BannedUsers.exists_user(user_id):
        return jsonify({'error_message': 'This email is banned'}), 409
    user = User.query.get(user_id)
    if user is None:
        return jsonify({"error_message": f"User {user_id} doesn't exist"}), 400
    
    post = EventPosts.query.get(post_id)
    if post is None:
        return jsonify({"error_message": f"Post {post_id} doesn't exist"}), 400

    like_post = LikePost.query.filter_by(user_id=user_id, post_id=post_id).first()
    if(like_post is not None):
        # delete like
        like_post.delete()
        return jsonify({"message": "Successful delete like"}), 200
    else :
        new_like_post = LikePost(user_id=user_id, post_id=post_id)
        try:
            new_like_post.save()
        except sqlalchemy.exc.IntegrityError:
            return jsonify({"error_message": "Integrity error, FK violated (algo no esta definido en la BD) o ya existe la payment en la DB"}), 400
        except:
            return jsonify({"error_message": "Error de DB nuevo, cual es?"}), 400
        return jsonify({"message": "Successful create like"}), 200
    

# SABER SI USUARIO HA DADO LIKE A UN EVENTO method: saber si un usuario ha dado like a un evento
@module_event_v3.route('/<iduser>/likepost/<idevent>/<idpost>', methods=['GET'])
# RECIBE:
# - GET HTTP request con la id del usuario que queremos consultar
# DEVUELVE:
# - 400: Un objeto JSON con los posibles mensajes de error, id no valida o evento no existe
# - 200: Un objeto JSON confirmando que se ha eliminado correctamente
@jwt_required(optional=False)
def get_likes_post_from_user(iduser, idevent, idpost):
    auth_id = get_jwt_identity()
    if BannedUsers.exists_user(auth_id):
            return jsonify({'error_message': 'This email is banned'}), 409
    try:
        user_id_q = uuid.UUID(iduser)
    except:
        return jsonify({"error_message": "User_id isn't a valid UUID"}), 400

    user = User.query.get(user_id_q)
    if user is None:
        return jsonify({"error_message": f"User {user_id_q} doesn't exist"}), 400

    try:
        event_id_q = uuid.UUID(idevent)
    except:
        return jsonify({"error_message": "Event_id isn't a valid UUID"}), 400
    event = Event.query.get(event_id_q)
    if event is None:
        return jsonify({"error_message": f"Event {event_id_q} doesn't exist"}), 400
    
    post = EventPosts.query.filter_by(id = idpost,event_id = event_id_q)
    if post is None:
        return jsonify({"error_message": f"Post {idpost} doesn't exist"}), 400

    try:
        liked = LikePost.query.filter_by(
            user_id=user_id_q, post_id=idpost).first()
    except:
        return jsonify({"error_message": "Error while querying Like"}), 400

    if liked is None:
        return jsonify({"message": "No le ha dado like"}), 200
    else:
        return jsonify({"message": "Le ha dado like"}), 200


########################################################################### REGISTER ########################################################


@module_event_v3.route('/<id>/verify_code', methods=['GET'])
@jwt_required(optional=False)
def get_verification_code(id):
    auth_id = uuid.UUID(get_jwt_identity())
    if BannedUsers.exists_user(auth_id):
        return jsonify({'error_message': 'This email is banned'}), 409
    participant = Participant.query.filter_by(event_id=id, user_id=auth_id).first()
    if participant is None:
        return jsonify({"error_message": "You are not participant of this event"}), 400
    code = participant.verification_code

    link = os.getenv('API_DOMAIN_NAME')+':'+os.getenv('API_PORT') + f'/v3/events/{id}/verify_event?username={auth_id}&code={code}'
    return jsonify({'verify_code': link}), 200

@module_event_v3.route('/<id>/verify_event', methods=['GET'])
@jwt_required(optional=False)
def get_verify_event(id):
    auth_id = uuid.UUID(get_jwt_identity())
    if BannedUsers.exists_user(auth_id):
        return jsonify({'error_message': 'This email is banned'}), 409
    event = Event.query.get(id)
    msg = ""
    if event is None:
        msg = "Event doesn't exist"
        # return jsonify({"error_message": "Event doesn't exist"}), 400
    if event.user_creator != auth_id:
        msg = "You are not the creator of this event"
        # return jsonify({"error_message": "You are not the creator of this event"}), 400
    code = request.args.get('code')
    username = request.args.get('username')
    participant = Participant.query.filter_by(event_id=id,user_id = username, verification_code=code).first()

    if participant is None:
        msg = "User or Code is not correct for this event"
        # return jsonify({"error_message": "User or Code is not correct for this event"}), 400
    else:
        if participant.time_verified is not None:
            msg = "User already verified"
            # return jsonify({"message": "User already verified"}), 200
        else:
            participant.time_verified = datetime.now()
            participant.save()
            msg = "Successful verification"
            # socketio.emit('VerificationDone', to='628a0571-605a-49d4-9c81-d71773eaff7f_38d1837b-c4ea-4e0a-98e5-ba09a4ee69bd')
    socketio.emit('VerificationDone', msg,to='628a0571-605a-49d4-9c81-d71773eaff7f_38d1837b-c4ea-4e0a-98e5-ba09a4ee69bd')
    return jsonify({"message": msg}), 200


@module_event_v3.route('/<id>/report/', methods=['POST'])
@jwt_required(optional=False)
def report_event(id): 
    try:
        auth_id = uuid.UUID(get_jwt_identity())
        if BannedUsers.exists_user(auth_id):
            return jsonify({'error_message': 'This email is banned'}), 409
        try:
            event_id = uuid.UUID(id)
        except:
            return jsonify({"error_message": "event_id isn't a valid UUID"}), 400
        event = Event.query.filter_by(id=event_id)
        if event is None:
            return jsonify({"error_message": f"Event {event_id} doesn't exist"}), 400
        if BannedEvents.query.filter_by(event_id=event_id).first() is not None:
            return jsonify({"error_message": "Event is already banned"}), 400
        
        if "comment" not in request.json:
            return jsonify({"error_message": "comment is not in the body"}), 400
        new_report = ReportedEvent(id_user=auth_id, id_event_reported=event_id, comment=request.json['comment'])
        try:
            new_report.save()
        except sqlalchemy.exc.IntegrityError:
            return jsonify({"error_message": "Integrity error, FK violated (algo no esta definido en la BD) o ya existe el report en la DB"}), 400
        except:
            return jsonify({"error_message": "Error de DB nuevo, cual es?"}), 400
        return new_report.toJSON(), 201
    except:
        return jsonify({"error_message": "Unexpected error"}), 400 
