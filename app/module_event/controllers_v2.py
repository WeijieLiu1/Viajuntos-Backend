# Import flask dependencies
# Import module models (i.e. User)
import sqlalchemy
from app.module_event.models import Event, Participant, Like
from app.module_users.models import BannedUsers, User
from flask_jwt_extended import create_access_token, create_refresh_token, get_jwt_identity, jwt_required
from datetime import datetime
from flask import (Blueprint, request, jsonify)
#from google.cloud import vision
import uuid
import validators

# Import the database object from the main app module
from app import db

# Define the blueprint: 'event', set its url prefix: app.url/event
module_event_v2 = Blueprint('event_v2', __name__, url_prefix='/v2/events')

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
@module_event_v2.route('/', methods=['POST'])
@jwt_required(optional=False)
def create_event():
  # restricion: solo puedes crear eventos para tu usuario (mirando Bearer Token)
    auth_id = get_jwt_identity()
    if str(user_creator) != auth_id:
        return jsonify({"error_message": "Un usuario no puede crear un evento por otra persona"}), 400   
    
    if BannedUsers.exists_user(auth_id):
        return jsonify({'error_message': 'This email is banned'}), 409
    try:
        args = request.json
    except:
        return jsonify({"error_message": "Mira el JSON body de la request, hay un atributo mal definido!"}), 400 
    event_uuid = uuid.uuid4() 

    response = check_atributes(args)
    if (response['error_message'] != "all good"):
        return jsonify(response), 400

    date_started = datetime.strptime(args.get("date_started"), '%Y-%m-%d %H:%M:%S')
    date_end= datetime.strptime(args.get("date_end"), '%Y-%m-%d %H:%M:%S')
    longitud = float(args.get("longitud"))
    latitude = float(args.get("latitude"))
    max_participants = int(args.get("max_participants"))
    user_creator = uuid.UUID(args.get("user_creator"))

    event = Event(event_uuid, args.get("name"), args.get("description"), date_started, date_end, user_creator, longitud, latitude, max_participants, args.get("event_image_uri"))
    
    # Errores al guardar en la base de datos: FK violated, etc
    try:
        event.save()
    except sqlalchemy.exc.IntegrityError:
        return jsonify({"error_message": "User FK violated, el usuario user_creator no esta definido en la BD"}), 400
    except: 
        return jsonify({"error_message": "Error de DB nuevo, cual es?"}), 400

    # Añadir el creador al evento como participante
    participant = Participant(event.id, user_creator)

    try:
        participant.save()
    except sqlalchemy.exc.IntegrityError:
        return jsonify({"error_message": "FK violated"}), 400
    except:
        return jsonify({"error_message": "Error de DB nuevo, cual es?"}), 400

    eventJSON = event.toJSON()
    return jsonify(eventJSON), 201


# MODIFICAR EVENTO: Modifica la información de un evento
# Recibe:
# PUT HTTP request con la id del evento en la URI y los atributos del evento en el body (formato JSON)
#       {name, description, date_started, date_end, user_creator, longitud, latitude, max_participants}
# Devuelve:
# - 400: Un objeto JSON con un mensaje de error
# - 200: Un objeto JSON con un mensaje de evento modificado con exito 
@module_event_v2.route('/<id>', methods=['PUT'])
@jwt_required(optional=False)
def modify_events_v2(id):
    # restricion: solo el usuario creador puede modificar su evento (mirando Bearer Token)
    auth_id = get_jwt_identity()
    
    if BannedUsers.exists_user(auth_id):
        return jsonify({'error_message': 'This email is banned'}), 409
    if str(event.user_creator) != auth_id:
        return jsonify({"error_message": "A user cannot update the events of others"}), 400    
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
    response = check_atributes(args)
    if (response['error_message'] != "all good"):
        return jsonify(response), 400

    # restricion: solo el usuario creador puede editar su evento
    if event.user_creator != uuid.UUID(args.get("user_creator")):
        return jsonify({"error_message": "solo el usuario creador puede modificar su evento"}), 400
   

    event.name = args.get("name")
    event.description = args.get("description")
    event.date_started = datetime.strptime(args.get("date_started"), '%Y-%m-%d %H:%M:%S')
    event.date_end= datetime.strptime(args.get("date_end"), '%Y-%m-%d %H:%M:%S')
    event.longitud = float(args.get("longitud"))
    event.latitude = float(args.get("latitude"))
    event.max_participants = int(args.get("max_participants"))
    event.event_image_uri = args.get("event_image_uri")

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
def check_atributes(args):
    # restriccion 0: Mirar si los atributos estan en el body
    if args.get("name") is None or len(args.get("name")) == 0:
        return {"error_message": "atributo name no esta en el body, es null o esta vacio"}
    if args.get("description") is None or len(args.get("description")) == 0:
        return {"error_message": "atributo description no esta en el body, es null o esta vacio"}
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
    if args.get("event_image_uri") is None:
        return {"error_message": "atributo event_image_uri no esta en la URL o es null"} 

    # TODO restriccion 1: mirar las palabras vulgares en el nombre y la descripcion
    
    # restriccion 2: Atributos string estan vacios
    try:
        user_creator = uuid.UUID(args.get("user_creator"))
    except ValueError:
        return {"error_message": f"user_creator id isn't a valid UUID"}
    if not isinstance(args.get("name"), str):
        return {"error_message": "name isn't a string!"} 
    if not isinstance(args.get("description"), str):
        return {"error_message": "description isn't a string!"}
    if len(args.get("name")) == 0 | len(args.get("description")) == 0 | len(str(user_creator)) == 0:
        return {"error_message": "name, description or user_creator is empty!"}
    
    # restriccion 3: date started es mas grande que end date del evento (format -> 2015-06-05 10:20:10) y Comprobar Value Error
    try:
        date_started = datetime.strptime(args.get("date_started"), '%Y-%m-%d %H:%M:%S')
        date_end= datetime.strptime(args.get("date_end"), '%Y-%m-%d %H:%M:%S')
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
    if len(args.get("event_image_uri")) != 0:
        if not validators.url(args.get("event_image_uri")):
            return {"error_message": "la imagen del evento no es una URL valida"} 
        
    # TODO restriccion 10: mirar si la imagen es una imagen vulgar
    # event_image_uri = args.get("event_image_uri")
    # is_it_safe = detect_safe_search_uri(event_image_uri)
    # for category in is_it_safe:
    #     if(is_it_safe[category] == 'UNKNOWN' | is_it_safe[category] == 'POSSIBLE' | is_it_safe[category] == 'LIKELY' | is_it_safe[category] == 'VERY_LIKELY'):
    #         return {"error_message": "la imagen del evento no puede ser explicita (hemos detectado que podria serlo)"} 

    return {"error_message": "all good"}


#def detect_safe_search_uri(uri):
#    """Detects unsafe features in the file located in Google Cloud Storage or
#    on the Web."""
#    client = vision.ImageAnnotatorClient()
#    image = vision.Image()
#    image.source.image_uri = uri
#
#    is_it_safe = {}

#    response = client.safe_search_detection(image=image)
#    safe = response.safe_search_annotation

    # Names of likelihood from google.cloud.vision.enums
#    likelihood_name = ('UNKNOWN', 'VERY_UNLIKELY', 'UNLIKELY', 'POSSIBLE',
#                       'LIKELY', 'VERY_LIKELY')
                    
#    is_it_safe["adult"] = likelihood_name[safe.adult]
#    is_it_safe["medical"] = likelihood_name[safe.medical]
#    is_it_safe["spoofed"] = likelihood_name[safe.spoof]
#    is_it_safe["violence"] = likelihood_name[safe.violence]
#    is_it_safe["racy"] = likelihood_name[safe.racy]

#    if response.error.message:
#        return {"error_message": "la imagen del evento no se ha compilado correctamente"} 

#    return is_it_safe


# UNIRSE EVENTO: Usuario se une a un evento
# Recibe:
# POST HTTP request con la id del evento en la URI y el usuario que se quieran añadir al evento en el body (formato JSON)
#       {user_id}
# Devuelve:
# - 400: Un objeto JSON con un mensaje de error
# - 200: Un objeto JSON con un mensaje de el usuario se ha unido con exito
@module_event_v2.route('/<id>/join', methods=['POST'])
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
        return jsonify({"error_message":f"Error al hacer query de un evento"}), 400
    
    if event is None:
        return jsonify({"error_message":f"El evento {event_id} no existe en la BD"}), 400
    
    # TODO Mirar si el user puede unirse al evento (tema banear)
    
    try:
        args = request.json
    except:
        return jsonify({"error_message": "Mira el JSON body de la request, hay un atributo mal definido"}), 400 

    try:
        user_id = uuid.UUID(args.get("user_id"))
    except:
        return jsonify({"error_message":f"la user_id no es una UUID valida"}), 400

    auth_id = get_jwt_identity()
    
    if BannedUsers.exists_user(auth_id):
        return jsonify({'error_message': 'This email is banned'}), 409
    if str(user_id) != auth_id:
        return jsonify({"error_message": "A user cannot join a event for others"}), 400   
                
    # restriccion: el usuario creador no se puede unir a su propio evento (ya se une automaticamente al crear el evento)
    if event.user_creator == user_id:
        return jsonify({"error_message": f"El usuario {user_id} es el creador del evento (ya esta dentro)"}), 400

    # restriccion: el usuario ya esta dentro del evento
    particip = Participant.query.filter_by(event_id=event_id, user_id=user_id).first()
    if particip is not None:
        return jsonify({"error_message": f"El usuario {user_id} ya esta dentro del evento {event_id}"}), 400

    # restriccion: el evento ya esta lleno
    num_participants = Participant.query.filter_by(event_id=event_id).all()
    if len(num_participants) >= event.max_participants:
        return jsonify({"error_message": f"El evento {event_id} ya esta lleno!"}), 400

    participant = Participant(event_id, user_id)
    
    # Errores al guardar en la base de datos: FK violated, etc
    try:
        participant.save()
    except sqlalchemy.exc.IntegrityError:
        return jsonify({"error_message":f"FK violated, el usuario {user_id} ya se ha unido al evento o no esta definido en la BD"}), 400
    except:
        return jsonify({"error_message": "Error de DB nuevo, cual es?"}), 400

    return jsonify({"message":f"el usuario {user_id} se han unido CON EXITO"}), 200


# ABANDONAR EVENTO: Usuario abandona a un evento
# Recibe:
# POST HTTP request con la id del evento en la URI y el usuario que se quieran añadir al evento en el body (formato JSON)
#       {user_id}
# Devuelve:
# - 400: Un objeto JSON con un mensaje de error
# - 200: Un objeto JSON con un mensaje de el usuario ha abandonado el evento CON EXITO
@module_event_v2.route('/<id>/leave', methods=['POST'])
@jwt_required(optional=False)
def leave_event(id):
    try:
        event_id = uuid.UUID(id)
    except:
        return jsonify({"error_message": "la id del evento no es una UUID valida"}), 400

    try:
        event = Event.query.get(event_id)
    except:
        return jsonify({"error_message":f"Error al hacer query de un evento"}), 400
    
    if event is None:
        return jsonify({"error_message":f"El evento {event_id} no existe en la BD"}), 400
    
    try:
        args = request.json
    except:
        return jsonify({"error_message": "Mira el JSON body de la request, hay un atributo mal definido"}), 400 

    try:
        user_id = uuid.UUID(args.get("user_id"))
    except:
        return jsonify({"error_message":f"la user_id no es una UUID valida"}), 400

    # restriccion: Un usuario no puede abandonar un evento por otro
    auth_id = get_jwt_identity()
    if str(user_id) != auth_id:
        return jsonify({"error_message": "A user cannot leave a event for others"}), 400   
    if BannedUsers.exists_user(user_id):
        return jsonify({'error_message': 'This email is banned'}), 409
    # restriccion: el usuario no es participante del evento
    try:
        participant = Participant.query.filter_by(event_id = event_id, user_id = user_id).first()
    except:
        return jsonify({"error_message":f"Error en el query de participante"}), 400
    
    if participant is None:
        return jsonify({"error_message":f"El usuario {user_id} no es participante del evento {event_id}"}), 400

    # restriccion: el usuario creador no puede abandonar su evento
    if event.user_creator == user_id:
        return jsonify({"error_message":
                f"El usuario {user_id} es el creador del evento (no puede abandonar)"}), 400
    
    # Errores al guardar en la base de datos: FK violated, etc
    try:
        participant.delete()
    except sqlalchemy.exc.IntegrityError:
        return jsonify({"error_message":f"FK violated, el usuario {user_id} no esta definido en la BD"}), 400
    except:
        return jsonify({"error_message": "Error de DB nuevo, cual es?"}), 400

    return jsonify({"message":f"el participante {user_id} ha abandonado CON EXITO"}), 200

# PARTICIPACIONES DE UN USER: todos los eventos a los que un usuario se ha unido
@module_event_v2.route('/joined/<id>', methods=['GET'])
# RECIBE:
# - GET HTTP request con la id del usuario que queremos solicitar
# DEVUELVE:
# - 400: Un objeto JSON con los posibles mensajes de error, id no valida o evento no existe
# - 200: Un objeto JSON con los eventos a los que se a unido
@jwt_required(optional=False)
def get_user_joins(id):
    try:
        user_id = uuid.UUID(id)
    except:
        return jsonify({"error_message": f"The user id isn't a valid UUID"}), 400
    if BannedUsers.exists_user(user_id):
        return jsonify({'error_message': 'This email is banned'}), 409
    try:
        events_joined = Participant.query.filter_by(user_id = user_id)
    except:
            return jsonify({"error_message": "Error when querying participants"}), 400       
    try:
        events = []
        for ides in events_joined:
            events.append(Event.query.get(ides.event_id))
        return jsonify([event.toJSON() for event in events]), 200
    except:
        return jsonify({"error_message": "Unexpected error"}), 400       



# OBTENER UN EVENTO: returns the information of one event
@module_event_v2.route('/<id>', methods=['GET'])
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
        return jsonify(event.toJSON()), 200
    except:
        return jsonify({"error_message": f"The event {event_id} doesn't exist"}), 400

# OBTENER EVENTOS POR USUARIO CREADOR method: devuelve todos los eventos creados por un usuario
@module_event_v2.route('/creator', methods=['GET'])
# RECIBE:
# - GET HTTP request con la id del usuario del que se quieren obtener los eventos creados como query parameter.
# - 400: Un objeto JSON con los posibles mensajes de error, id no valida
# - 201: Un objeto JSON con TODOS los parametros del evento con la id de la request
@jwt_required(optional=False)
def get_creations():
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
    if BannedUsers.exists_user(user_id):
        return jsonify({'error_message': 'This email is banned'}), 409
    user = User.query.get(user_id)
    if user is None:
        return jsonify({"error_message": f"User {user_id} doesn't exist"}), 400
    
    try:
        events_creats = Event.query.filter_by(user_creator = user_id)
        print("try to get created")
        return jsonify([event.toJSON() for event in events_creats]), 200
    except:
        return jsonify({"error_message": "An unexpected error ocurred"}), 400        


# DELETE EVENTO method: deletes an event from the database
@module_event_v2.route('/<id>', methods=['DELETE'])
# RECIBE:
# - DELETE HTTP request con la id del evento que se quiere eliminar
# DEVUELVE:
# - 400: Un objeto JSON con los posibles mensajes de error, id no valida o evento no existe
# - 200: Un objeto JSON confirmando que se ha eliminado correctamente
@jwt_required(optional=False)
def delete_event(id):
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

    # restricion: solo el usuario creador puede eliminar su evento (mirando Bearer Token)
    auth_id = get_jwt_identity()
    if BannedUsers.exists_user(auth_id):
        return jsonify({'error_message': 'This email is banned'}), 409
    if str(event.user_creator) != auth_id:
        return jsonify({"error_message": "A user cannot delete events if they are not the creator"}), 400          

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

    try:
        event.delete()
        return jsonify({"error_message": "Successful DELETE"}), 202
    except:
        return jsonify({"error_message": "error while deleting"}), 400
    


# GET ALL EVENTOS method: retorna toda la informacion de todos los eventos de la database
@module_event_v2.route('/', methods=['GET'])
# RECIBE:
# - GET HTTP request
# DEVUELVE:
# - 400: Un objeto JSON con los posibles mensajes de error
# - 201: Un objeto JSON con todos los eventos que hay en el sistema
@jwt_required(optional=False)
def get_all_events():
    auth_id = get_jwt_identity()
    if BannedUsers.exists_user(auth_id):
        return jsonify({'error_message': 'This email is banned'}), 409
    try:
        all_events = Event.get_all()
    except:
        return jsonify({"error_message": "Error when querying events"}), 400
    
    try:
        return jsonify([event.toJSON() for event in all_events]), 200
    except:
        return jsonify({"error_message": "Unexpected error when passing events to JSON format"}), 400


# FILTRAR EVENTO: Retorna un conjunto de eventos en base a unas caracteristicas
# Recibe:
# GET HTTP request con los atributos que quiere filtrar (formato JSON)
#       {name, date_started, date_end}
# Devuelve:
@module_event_v2.route('/filter', methods=['GET'])
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
            date_start_interval = datetime.strptime(args.get("date_started"), '%Y-%m-%d %H:%M:%S')
            date_end_interval = datetime.strptime(args.get("date_end"), '%Y-%m-%d %H:%M:%S')
            if date_start_interval > date_end_interval:
                return {"error_message": "The start date must be greater than the end date"}
            if date_start_interval == date_end_interval:
                return {"error_message": "The start date and the end date are the same" }
            if date_start_interval < datetime.now():
                return {"error_message": "Date_started is before the now time"}
        except ValueError:
            return {"error_message": "date_started or date_ended aren't real dates or they don't exist!"}

    try:
        events_filter = None
        if args.get("name") is not None:
            events_filter = Event.filter_by(name = args.get["name"])

        if args.get("date_started") is not None and args.get("name") is not None:
            events_filter = events_filter.filter_by(Event.date_started >= date_start_interval, Event.date_started <= date_end_interval, Event.date_end <= date_end_interval, )
        elif args.get("date_started") is not None:
            events_filter = Event.filter_by(Event.date_started >= date_start_interval, Event.date_started <= date_end_interval, Event.date_end <= date_end_interval, )

        if events_filter is None:
                return jsonify({"error_message": "Any event match with the filter"}), 400
        else:
            return jsonify([event.toJSON() for event in events_filter]), 200
    except Exception as e:
        return jsonify({"error_message": "hello"}), 400

# OBTENER LOS 10 EVENTOS CREAS MAS RECIENTEMENTE method: Retorna un conjunto con los 10 eventos mas recientes
@module_event_v2.route('/lastten', methods=['GET'])
@jwt_required(optional=False)
def lastest_events():
    auth_id = get_jwt_identity()
    
    if BannedUsers.exists_user(auth_id):
        return jsonify({'error_message': 'This email is banned'}), 409 
    try:
        lasts_events = Event.query.order_by(Event.date_creation.desc()).all()
    except:
        return {"error_message": "Error while querying events"}
    
    lastten = []
    i = 0
    for e in lasts_events:
        if i < 10:
            lastten.append(e)
            i += 1
        else:
            break
    
    return jsonify([event.toJSON() for event in lastten]), 200


# SABER QUE PERSONAS SE HAN UNIDO A UN EVENTO method: Retorna el conjunto de users que se han unido a un evento
@module_event_v2.route('/participants', methods=['GET'])
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


########################################################################### O T R O S ###########################################################################


# If the event doesn't exist
@module_event_v2.errorhandler(404)
def page_not_found():
    return "<h1>404</h1><p>The event could not be found.</p>", 404

@module_event_v2.teardown_request
def teardown_request(exception):
    if exception:
        db.session.rollback()
    db.session.remove()


########################################################################### L I K E S ###########################################################################

 
#DAR LIKE method: un usuario le da like a un evento
@module_event_v2.route('/<id>/like', methods=['POST'])
#RECIBE:
#- POST HTTP request con los parametros en un JSON object en el body de la request.
#DEVUELVE:
#- 400: Un objeto JSON con un mensaje de error
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
    if str(user_id) != auth_id:
        return jsonify({"error_message": "A user can't like for others"}), 400    
    if BannedUsers.exists_user(auth_id):
        return jsonify({'error_message': 'This email is banned'}), 409
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
@module_event_v2.route('/<id>/like', methods=['DELETE'])
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
    if str(delete_user_id) != auth_id:
        return jsonify({"error_message": "A user can't remove likes for others"}), 400    
    if BannedUsers.exists_user(auth_id):
        return jsonify({'error_message': 'This email is banned'}), 409
    try:
        delete_event_id = uuid.UUID(id)
    except:
        return jsonify({"error_message": "Event_id isn't a valid UUID"}), 400

    
    event = Event.query.get(delete_event_id)
    if event is None:
        return jsonify({"error_message": f"The event {str(delete_event_id)} doesn't exist"}), 400

    try:
        Like_borrar = Like.query.filter_by(user_id = delete_user_id, event_id = delete_event_id).first()
        Like_borrar.delete()
        return jsonify({"message": "Successful DELETE"}), 200
    except:
        return jsonify({"error_message": f"The like of user {delete_user_id} in event {delete_event_id} doesn't exist"}), 400

# LIKES DE UN USER: todos los eventos a los que un usuario ha dado like
@module_event_v2.route('/like/<iduser>', methods=['GET'])
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
    if str(user_id) != auth_id:
        return jsonify({"error_message": "A user can't get the likes of the events of someone else"}), 400       
    if BannedUsers.exists_user(auth_id):
        return jsonify({'error_message': 'This email is banned'}), 409
    try:
        likes_user = Like.query.filter_by(user_id = user_id)
    except:
            return jsonify({"error_message": "Error when querying likes"}), 400       
    try:
        events = []
        for i in likes_user:
            events.append(Event.query.get(i.event_id))
        return jsonify([event.toJSON() for event in events]), 200
    except:
        return jsonify({"error_message": "Unexpected error"}), 400       


# SABER SI USUARIO HA DADO LIKE A UN EVENTO method: saber si un usuario ha dado like a un evento
@module_event_v2.route('/<iduser>/like/<idevento>', methods=['GET'])
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
        liked = Like.query.filter_by(user_id = user_id_q, event_id = event_id_q).first()
    except:
        return jsonify({"error_message": "Error while querying Like"}), 400
    
    if liked is None:
        return jsonify({"message": "No le ha dado like"}), 200    
    else:
        return jsonify({"message": "Le ha dado like"}), 200


# DIEZ EVENTOS CON MAYOR NUMERO DE LIKES: los 10 eventos con el mayor numero de likes
@module_event_v2.route('/topten', methods=['GET'])
# DEVUELVE:
# - 400: Un objeto JSON con los posibles mensajes de error, id no valida o evento no existe
# - 200: Un objeto JSON con los top 10 eventos con mas likes
@jwt_required(optional=False)
def get_top_ten_events():
    auth_id = get_jwt_identity()
    if BannedUsers.exists_user(auth_id):
        return jsonify({'error_message': 'This email is banned'}), 409
    # Coger todos los likes de la DB
    try:
        all_likes = Like.get_all()
    except:
        return jsonify({"error_message": "error getting likes"}), 400    
    
    # Guardar todos los likes de cada evento en un array Y FUNCIONA
    try:
        likes_in_events = {}
        for like in all_likes:
            s = str(like.event_id)
            if s in likes_in_events:
                likes_in_events[s] = likes_in_events[s] + 1
            else:
                likes_in_events[s] = 1
    except:
        return jsonify({"error_message": "error asignando vector likes"}), 400

    # Guardar los top 10 eventos con mas likes en un array
    i = 1
    top_ten = []
    while i <= 10:
        most_likes = 0
        most_liked_event = None
        for event in likes_in_events:
            if likes_in_events[event] >= most_likes:
                most_liked_event = event
                most_likes = likes_in_events[event]
        if most_liked_event != None:
            top_ten.append(most_liked_event)
            likes_in_events.pop(most_liked_event)
        i += 1
    
    # Coger la info de cada evento
    top_ten_with_info = []
    for event in top_ten:
        try:
            event_to_add = Event.query.filter_by(id=event).first()
        except:
            return jsonify({"error_message": "error en coger el top ten"}), 400
        
        top_ten_with_info.append(event_to_add)

    return jsonify([event.toJSON() for event in top_ten_with_info]), 200


     