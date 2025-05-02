# Import flask dependencies
from flask import Blueprint, jsonify, request, current_app
from datetime import datetime
from flask_jwt_extended import get_jwt_identity, jwt_required
import sqlalchemy as db
from sqlalchemy import create_engine, desc
import uuid

from app.module_event.controllers_v3 import delete_event

# Import the database object from the main app module
from app import hashing

# Import module models
from app.module_admin.models import Admin, ReportedEvent, ReportedUser
from app.module_users.models import AchievementProgress, BannedUsers, FacebookAuth, Friend, GoogleAuth,GithubAuth, User, ViajuntosAuth, UserLanguage
from app.module_users.utils import generate_tokens
from app.utils.email import send_email
from app.module_event.models import Event, BannedEvents, Participant
from app.module_chat.controllers import borrar_todos_chats_usuario

import ipdb
# Define the blueprint: 'admin', set its url prefix: app.url/v1/admin
module_admin_v1 = Blueprint('admin', __name__, url_prefix='/v1/admin')

@module_admin_v1.route('/login', methods=['POST'])
def login():
    if not ('email' in  request.json and 'password' in request.json):
        return jsonify({'error_message': 'Missing credentials in json body.'}), 400 
    email = request.json['email']
    password = request.json['password']
    user = User.query.filter_by(email = email).first()
    if user == None:
        return jsonify({'error_message': 'Email or password are wrong.'}), 404
    if not Admin.exists(user.id):
        return jsonify({'error_message': 'Only administrators can access this resource.'}), 403
    viajuntos_auth = ViajuntosAuth.query.filter_by(id = user.id).first()
    if viajuntos_auth == None:
        return jsonify({'error_message': 'Authentication method not available for this email.'}), 400 
    if not hashing.check_value(viajuntos_auth.pw, password, salt=viajuntos_auth.salt):
        return jsonify({'error_message': 'Email or password are wrong.'}), 400 
    return generate_tokens(str(user.id)), 200


# listar todos los eventos reportados: obtener una lista de, por cada evento, todos los usuarios que lo han reportado
@module_admin_v1.route('/reported_events', methods=['GET'])
# DEVUELVE:
# - 400: Un objeto JSON con los posibles mensajes de error, id no valida o evento no existe
# - 200: Un objeto JSON con los usuarios y, en cada uno, sus eventos reportados 
@jwt_required(optional=False)
def get_reported_events():
    # Ver si el token es de un admin
    auth_id = get_jwt_identity()
    if not Admin.exists(auth_id):
        return jsonify({"error_message": "Only administrators can access this resource."}), 400
    if BannedUsers.exists_user(auth_id):
            return jsonify({'error_message': 'This email is banned'}), 409
    reported_events = ReportedEvent.query.all()
    event_ids = [reported_event.id_event_reported for reported_event in reported_events]
    all_events = Event.query.filter(Event.id.in_(event_ids)).all()
    event_map = {event.id: event for event in all_events}

    banned_events = BannedEvents.query.all()
    
    banned_event_ids = {bu.event_id for bu in banned_events}
    result = []
    for reported_event in reported_events:
        event = event_map.get(reported_event.id_event_reported)
        
        if event.id in banned_event_ids:
            continue
        if event:
            event_data = {
                'id_user': reported_event.id_user,
                'event': event.toJSON(),
                'comment': reported_event.comment
            }
            result.append(event_data)

    return jsonify(result), 200

# LISTAR TODOS LOS USUARIOS REPORTADOS: obtener una lista de, por cada usuario, todos sus eventos reportados
@module_admin_v1.route('/reported_users', methods=['GET'])
# DEVUELVE:
# - 400: Un objeto JSON con los posibles mensajes de error, id no valida o evento no existe
# - 200: Un objeto JSON con los usuarios y, en cada uno, sus eventos reportados 
@jwt_required(optional=False)
def get_reported_users():
    auth_id = get_jwt_identity()
    if not Admin.exists(auth_id):
        return jsonify({"error_message": "Only administrators can access this resource."}), 400
    if BannedUsers.exists_user(auth_id):
            return jsonify({'error_message': 'This email is banned'}), 409
    reported_users = ReportedUser.query.all()
    reported_user_ids = {ru.id_user_reported for ru in reported_users}
    
    reported_users_data = User.query.filter(User.id.in_(reported_user_ids)).all()
    user_map = {user.id: user for user in reported_users_data}

    banned_users = BannedUsers.query.all()
    banned_user_ids = {bu.id_user for bu in banned_users}
    result = []
    for reported_user in reported_users:
            if reported_user.id_user_reported in banned_user_ids:
                continue
            user = user_map.get(reported_user.id_user_reported)
            if user:
                user_data = {
                    'id_user': str(reported_user.id_user),
                    'id_user_reported': user.toJSON(),
                    'comment': reported_user.comment
                }
                result.append(user_data)

    return jsonify(result), 200


@module_admin_v1.route('/banned_users', methods=['GET'])
@jwt_required(optional=False)
def get_banned_user():
    auth_id = get_jwt_identity()
    if not Admin.exists(auth_id):
        return jsonify({'error_message': 'Only administrators can make this action.'}), 403
    if BannedUsers.exists_user(auth_id):
            return jsonify({'error_message': 'This email is banned'}), 409
    banned_users = BannedUsers.query.order_by(desc(BannedUsers.date)).all()
    return jsonify([bu.toJSON() for bu in banned_users]), 200

@module_admin_v1.route('/banned_events', methods=['GET'])
@jwt_required(optional=False)
def get_banned_event():
    auth_id = get_jwt_identity()
    if not Admin.exists(auth_id):
        return jsonify({'error_message': 'Only administrators can make this action.'}), 403
    if BannedUsers.exists_user(auth_id):
            return jsonify({'error_message': 'This email is banned'}), 409
    banned_events = BannedEvents.query.order_by(desc(BannedEvents.date)).all()
    return jsonify([be.toJSON() for be in banned_events]), 200

@module_admin_v1.route('/ban_user', methods=['POST'])
@jwt_required(optional=False)
def ban_user():
    auth_id = get_jwt_identity()
    if not Admin.exists(auth_id):
        return jsonify({'error_message': 'Only administrators can make this action.'}), 403
    if BannedUsers.exists_user(auth_id):
            return jsonify({'error_message': 'This email is banned'}), 409
    if not (request.json and 'id' in request.json):
        return jsonify({'error_message': 'Missing id in json body.'}), 400

    try:
        user_id = uuid.UUID(request.json['id'])
    except:
        return jsonify({"error_message": "id isn't a valid UUID"}), 400
    if Admin.exists(user_id):
        return jsonify({'error_message': 'An administrator user cannot be banned by another administrator user, please contact a higher clearence member.'}), 409
    banned_user = User.query.filter_by(id = user_id).first()
    if banned_user == None:
        return jsonify({'error_message': 'No such user.'}), 404
    ban_reason = None if 'reason' not in request.json else request.json['reason']
    current_time = datetime.now()

    email_to_ban = banned_user.email
    username_to_ban = banned_user.username
    
    if BannedUsers.query.filter_by(email = email_to_ban).first() != None:
        return jsonify({'error_message': 'User email already banned.'}), 200
    ban_instance = BannedUsers(user_id,email_to_ban, username_to_ban, current_time, ban_reason,auth_id)
    ban_instance.save()

    email_body = 'Due to an accumulation of bad reviews that have been determined to be sufficient to take action we feel obligated to ban you from the Viajuntos platform.\n'
    if ban_reason != None:
        email_body += f'\nFurther explanation follows:\n{ban_reason}\n'
    email_body += f'\nIf you feel like this decision is unjustified contact us directly. Your account will be terminated permanently but your email can be removed from our blacklist in the future.\n\nThe Viajuntos team.'
    send_email(banned_user.email, 'You have been banned from Viajuntos', email_body)
    return jsonify({'message': 'User email has banned.'}), 201

@module_admin_v1.route('/ban_event', methods=['POST'])
@jwt_required(optional=False)
def ban_event():
    auth_id = get_jwt_identity()
    if not Admin.exists(auth_id):
        return jsonify({'error_message': 'Only administrators can make this action.'}), 403
    if BannedUsers.exists_user(auth_id):
            return jsonify({'error_message': 'This email is banned'}), 409
    if not (request.json and 'id' in request.json):
        return jsonify({'error_message': 'Missing id in json body.'}), 400
    try:
        event_id = uuid.UUID(request.json['id'])
    except:
        return jsonify({"error_message": "id isn't a valid UUID"}), 400
    banned_event = Event.query.filter_by(id=event_id).first()
    if banned_event is None:
        return jsonify({'error_message': 'No such event.'}), 404

    ban_reason = None if 'reason' not in request.json else request.json['reason']
    current_time = datetime.now()

    if BannedEvents.query.filter_by(event_id=event_id).first() is not None:
        return jsonify({'error_message': 'Event already banned.'}), 200

    ban_instance = BannedEvents(event_id, current_time, ban_reason, auth_id)
    ban_instance.save()

    participants = Participant.query.filter_by(event_id=event_id).all()
    for participant in participants:
        user_participant = User.query.filter_by(id=participant.user_id).first()

        email_body = f"""
        Hello,

        We regret to inform you that the event "{banned_event.name}" you were part of has been banned on Viajuntos. This decision was made after careful consideration.

        {f'Reason for the ban: {ban_reason}' if ban_reason else 'No specific reason was provided.'}

        If you have questions or believe this action was taken in error, feel free to contact our support team.

        Regards,
        The Viajuntos Team.
        """
        send_email(user_participant.email, f'Event "{banned_event.name}" Banned Notification', email_body)

    return jsonify({'message': 'Event has been banned.'}), 201

@module_admin_v1.route('/unban_user', methods=['POST'])
@jwt_required(optional=False)
def unban_user():
    auth_id = get_jwt_identity()
    if not Admin.exists(auth_id):
        return jsonify({'error_message': 'Only administrators can make this action.'}), 403
    if BannedUsers.exists_user(auth_id):
            return jsonify({'error_message': 'This email is banned'}), 409
    if not (request.json and 'email' in request.json):
        return jsonify({'error_message': 'Missing email in json body.'}), 400
    
    email = request.json['email']
    reason = None if 'reason' not in request.json else request.json['reason']

    ban = BannedUsers.query.filter_by(email = email).first()
    if ban == None:
        return jsonify({'error_message': 'This email is not in the banned emails list.'}), 404

    ban_reason = ban.reason

    email_body = 'Hey there! Welcome back to Viajuntos.\n\nYou have been unbaned by one of our staff members, \
        please behave properly this time and do not repeat your past mistakes.\n\n'
    if ban_reason != None:
        email_body += f'We remind you the reason you were banned for: {ban_reason}\n\n'
    if reason != None:
        email_body += f'This is the reason for your unban: {reason}\n\n'
    email_body += 'See you around!\nThe Viajuntos team.'
    send_email(email, 'Unban from Viajuntos notice.', email_body)

    ban.delete()
    return jsonify({'message': 'Email unbaned'}), 200


@module_admin_v1.route('/unban_event', methods=['POST'])
@jwt_required(optional=False)
def unban_event():
    auth_id = get_jwt_identity()
    if not Admin.exists(auth_id):
        return jsonify({'error_message': 'Only administrators can make this action.'}), 403
    if BannedUsers.exists_user(auth_id):
            return jsonify({'error_message': 'This email is banned'}), 409
    if not (request.json and 'event_id' in request.json):
        return jsonify({'error_message': 'Missing event_id in json body.'}), 400

    event_id = request.json['event_id']
    reason = None if 'reason' not in request.json else request.json['reason']

    ban = BannedEvents.query.filter_by(event_id=event_id).first()
    if ban is None:
        return jsonify({'error_message': 'This event is not in the banned events list.'}), 404

    ban_reason = ban.reason

    event = Event.query.filter_by(id=event_id).first()
    participants = Participant.query.filter_by(event_id=event_id).all()
    for participant in participants:
        user_participant = User.query.filter_by(id=participant.user_id).first()
        email_body = f"""
        Hello,

        Good news! The event "{event.name}" you were part of has been unbanned on Viajuntos. 
        {f'The event was initially banned due to: {ban_reason}' if ban_reason else ''}

        {f'Reason for the unban: {reason}' if reason else ''}

        We hope you enjoy participating in the event. For any questions, feel free to reach out to us.

        Regards,
        The Viajuntos Team.
        """
        send_email(user_participant.email, f'Event "{event.name}" Unbanned Notification', email_body)

    # Notify the creator of the event
    user_creator_email = User.query.filter_by(id=event.user_creator).first().email

    email_body = f"""
    Hello,

    Your event "{event.name}" has been unbanned on Viajuntos. We appreciate your patience while we reviewed this matter.

    {f'The event was initially banned due to: {ban_reason}' if ban_reason else ''}
    {f'Reason for the unban: {reason}' if reason else ''}

    Please continue to abide by the platform guidelines to ensure a smooth experience for everyone.

    Regards,
    The Viajuntos Team.
    """
    send_email(user_creator_email, f'Event "{event.name}" Unbanned Notification', email_body)

    ban.delete()

    return jsonify({'message': 'Event unbanned'}), 200
