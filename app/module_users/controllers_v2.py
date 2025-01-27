# Import flask dependencies
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
import os
import uuid

import sqlalchemy

# Import the database object from the main app module
from app import db

# Import util functions
from app.module_admin.models import ReportedUser
from app.utils.email import send_email
from app.module_users.utils import increment_achievement_of_user, user_id_for_email, authentication_methods_for_user_id, send_verification_code_to, generate_tokens, get_random_salt, verify_password_strength
from app.module_chat.models import Chat
from app.module_chat.controllers import crear_private_chat
# Import module models
from app.module_users.models import BannedUsers, FriendInvite, User, Achievement, AchievementProgress, Friend, UserLanguage, EmailVerificationPendant, ViajuntosAuth,premium_expiration

# Import the hashing object from the main app module
from app import hashing

from datetime import datetime, timedelta, timezone

# Define the blueprint: 'users', set its url prefix: app.url/users
module_users_v2 = Blueprint('users_v2', __name__, url_prefix='/v2/users')


###################################### PROFILE / CREDENTIALS ######################################

@module_users_v2.route('/<id>', methods=['GET'])
@jwt_required(optional=True)
def get_profile(id):
    auth_id = get_jwt_identity()
    if BannedUsers.exists_user(auth_id):
        return jsonify({'error_message': 'This email is banned'}), 409
    is_authenticated_id = id == auth_id
    try:
        user_id = uuid.UUID(id)
    except:
        return jsonify({'error_message': 'ID is not a valid UUID'}), 400
    query_result = User.query.filter_by(id = user_id).first()
    if query_result == None:
            return jsonify({'error_message':f'User with id {id} does not exist'}), 404
    profile = query_result.toJSON()
    if is_authenticated_id:
        friends = Friend.getFriendsOfUserId(user_id)
        profile['friends'] = [{'id': f.id, 'username': f.username,'image_url':f.image_url} for f in friends]
        # profile['friends'] += profile['friends'] * 2
        # profile['friends'] += profile['friends'] * 2
        profile['auth_methods'] = authentication_methods_for_user_id(user_id)
    else:
        del profile['email']
    
    profile['achievements'] = Achievement.getAchievementsOfUserId(user_id)
    is_premium =  premium_expiration.query.filter_by(user = auth_id).first()
    if is_premium == None:
        profile['isPremium'] = False
    else: 
        profile['isPremium'] = True
    user_languages = UserLanguage.query.filter_by(user = user_id).all()
    profile['languages'] = [ str(l.language.value) for l in user_languages ]
    return jsonify(profile), 200


@module_users_v2.route('/forgot_pw', methods=['GET'])
def send_password_reset_code():
    if not (request.args and 'email' in request.args):
        return jsonify({'error_message': 'Must indicate an email'}), 400
    email = request.args['email']
    user_id = user_id_for_email(email)
    if BannedUsers.exists(email):
        return jsonify({'error_message': 'This email is banned'}), 409
    if user_id == None:
        return jsonify({'action': 'error', 'error_message': 'No user found for this email'}), 404

    auth_methods = authentication_methods_for_user_id(user_id)
    if 'viajuntos' not in auth_methods:
        return jsonify({'action': 'no_auth', 'alternative_auths': auth_methods}), 202
        
    code = get_random_salt(6)
    # Save code to database
    db_verification = EmailVerificationPendant.query.filter_by(email = email).first()
    if db_verification == None:
        db_verification = EmailVerificationPendant(email, code, datetime.now(timezone.utc)+timedelta(minutes=15))
        db_verification.save()
    else:
        db_verification.code = code
        db_verification.expires_at = datetime.now(timezone.utc)+timedelta(minutes=15)
        db.session.commit()
    send_email(email, 'Viajuntos: Reset your password with this code.', f'Your verification code for Viajuntos password reset is {code}. It expires in 15 minutes.')

    return jsonify({'action': 'continue'}), 200

@module_users_v2.route('/forgot_pw', methods=['POST'])
def reset_forgotten_password():
    if not request.json:
        return jsonify({'error_message': 'Missing json object'}), 400 
    if 'email' not in request.json:
        return jsonify({'error_message': 'Email attribute missing in json'}), 400 
    if 'password' not in request.json:
        return jsonify({'error_message': 'Password attribute missing in json'}), 400 
    if 'verification' not in request.json:
        return jsonify({'error_message': 'Verification code attribute missing in json'}), 400 

    email = request.json['email']
    if BannedUsers.exists(email):
        return jsonify({'error_message': 'This email is banned'}), 409
    pw = request.json['password']
    verification = request.json['verification']
    user_id = user_id_for_email(email)

    if user_id == None:
        return jsonify({'error_message': 'No user found for this email'}), 404

     # Check password strength
    pw_msg, pw_status = verify_password_strength(pw)
    if pw_status != 200: return pw_msg, pw_status

    # Check verification code in codes sent to email
    db_verification = EmailVerificationPendant.query.filter(EmailVerificationPendant.email == email).filter(EmailVerificationPendant.expires_at > datetime.now(timezone.utc)).first()
    if db_verification == None:
        return jsonify({'error_message': 'Verification code was never sent to this email or the code has expired.'}), 403
    if db_verification.code != verification:
        return jsonify({'error_message': 'Verification code does not coincide with code sent to email'}), 403
    
    viajuntos_auth = ViajuntosAuth.query.filter(ViajuntosAuth.id == user_id).first()

    # Update viajuntos auth method to user
    user_salt = get_random_salt(15)
    hashed_pw = hashing.hash_value(pw, salt=user_salt)
    viajuntos_auth.salt = user_salt
    viajuntos_auth.pw = hashed_pw
    try:
        viajuntos_auth.save()
    except:
        return jsonify({'error_message': 'Something went wrong when adding auth method viajuntos to user.'}), 500

    # Remove verification code -> already used
    db_verification.delete()
    
    return generate_tokens(str(user_id)), 200

# @module_users_v2.route('/friend_link', methods=['GET'])
# @jwt_required(optional=False)
# def request_new_friend_link():
#     auth_id = uuid.UUID(get_jwt_identity())
#     if BannedUsers.exists_user(auth_id):
#         return jsonify({'error_message': 'This email is banned'}), 409
#     user_invites = FriendInvite.query.filter_by(invitee = auth_id).filter(FriendInvite.expires_at > datetime.now(timezone.utc)).all()
#     if len(user_invites) >= 5:
#         return jsonify({'error_message': f'You already have {len(user_invites)} invitation links active.'}), 409

#     code = get_random_salt(15)
#     exp_date = datetime.now()+timedelta(days=365)
#     new_invite = FriendInvite(auth_id, code, exp_date)
#     try:
#         new_invite.save()
#     except Exception as e:
#         return jsonify({"error_message": f"Something went wrong inserting new invitation code to DB: {code}"}), 500

#     link = os.getenv('API_DOMAIN_NAME')+':'+os.getenv('API_PORT') + f'/v2/users/new_friend?code={code}'
#     return jsonify({'invite_link': link}), 200

@module_users_v2.route('/add_friend_request', methods=['POST'])
@jwt_required(optional=False)
def add_friend_request():
    auth_id = uuid.UUID(get_jwt_identity())  # 获取当前用户的 UUID

    # 检查用户是否被封禁
    if BannedUsers.exists_user(auth_id):
        return jsonify({'error_message': 'This email is banned'}), 409

    # 确保请求中包含 'id' 参数
    if 'id' not in request.json:
        return jsonify({'error_message': 'Id attribute missing in JSON'}), 400

    try:
        invited_id = uuid.UUID(request.json['id'])  # 验证并解析被邀请用户的 UUID
    except ValueError:
        return jsonify({'error_message': 'Invalid UUID format for id'}), 400

    # 删除所有已过期的邀请
    FriendInvite.query.filter(FriendInvite.expires_at <= datetime.now(timezone.utc)).delete()
    db.session.commit()

    # 检查是否已存在有效的邀请
    existing_invitation = FriendInvite.query.filter_by(
        invitee=auth_id, invited=invited_id
    ).filter(FriendInvite.expires_at > datetime.now(timezone.utc)).first()

    if existing_invitation is not None:
        if existing_invitation.accepted is None:
            return jsonify({"error_message": "Invitation is pending. Please wait for the recipient to respond."}), 403
        elif existing_invitation.accepted is True:
            return jsonify({"error_message": "Invitation has already been accepted."}), 409
        elif existing_invitation.accepted is False:
            return jsonify({"error_message": "Invitation was rejected. Please try again after the expiration date."}), 403
    # 检查对方是否已经邀请过当前用户
    been_invited = FriendInvite.query.filter_by(
        invitee=invited_id, invited=auth_id
    ).filter(FriendInvite.expires_at > datetime.now(timezone.utc)).first()

    if been_invited:
        if been_invited.accepted:
            return jsonify({"error_message": "You have already been invited by this user. Please check your messages."}), 409
        else:
            # 删除对方未接受的邀请
            been_invited.delete()

    # 创建新的邀请
    exp_date = datetime.now(timezone.utc) + timedelta(days=365)
    new_invite = FriendInvite(invitee=auth_id, invited=invited_id, expires_at=exp_date)

    try:
        new_invite.save()  # 保存到数据库
        return jsonify({"message": "Friend invitation sent successfully", "invitation_id": str(new_invite.invitee)}), 201
    except Exception as e:
        db.session.rollback() 
        return jsonify({"error_message": f"Failed to save invitation to DB: {str(e)}"}), 500
    
@module_users_v2.route('/get_friend_request', methods=['GET'])
@jwt_required(optional=False)
def get_friend_request():
    auth_id = uuid.UUID(get_jwt_identity())

    if BannedUsers.exists_user(auth_id):
        return jsonify({'error_message': 'This email is banned'}), 409
    invitations_expired = FriendInvite.query.filter_by(invited=auth_id
    ).filter(FriendInvite.expires_at < datetime.now(timezone.utc)).all()
    for invitation_expired in invitations_expired:
        invitation_expired.delete()

    invitations = FriendInvite.query.filter_by(invited=auth_id
    ).filter(FriendInvite.expires_at > datetime.now(timezone.utc)).all()

    enriched_invitations = []
    for invitation in invitations:
        inviter_id = invitation.invitee  
        inviter = User.query.get(inviter_id)

        if inviter:
            invitation_data = invitation.toJSON()
            invitation_data['username'] = inviter.username 
            invitation_data['image_url'] = inviter.image_url
            enriched_invitations.append(invitation_data)
        else:
            enriched_invitations.append(invitation.toJSON())

    return jsonify(enriched_invitations), 200


@module_users_v2.route('/add_friend_response', methods=['POST'])
@jwt_required(optional=False)
def add_friend_response():
    # 验证请求中是否包含 JSON 对象
    if not request.json:
        return jsonify({'error_message': 'Missing JSON object'}), 400

    # 验证必要的字段
    if 'id' not in request.json:
        return jsonify({"error_message": "Missing argument 'id'"}), 400
    if 'res' not in request.json:
        return jsonify({"error_message": "Missing argument 'res'"}), 400

    try:
        invited_id = uuid.UUID(request.json['id'])  # 被邀请用户的 ID
        res = request.json['res']  # 用户是否接受邀请
    except (ValueError, TypeError):
        return jsonify({"error_message": "Invalid input format"}), 400

    auth_id = uuid.UUID(get_jwt_identity())

    # 检查用户是否被封禁
    if BannedUsers.exists_user(auth_id):
        return jsonify({'error_message': 'This email is banned'}), 409

    # 防止用户添加自己为好友
    if invited_id == auth_id:
        return jsonify({"error_message": "Can't add yourself as your friend, but you do have high self-esteem."}), 400

    # 检查是否已存在好友关系
    friend1 = Friend.query.filter_by(invitee=invited_id, invited=auth_id).first()
    friend2 = Friend.query.filter_by(invitee=auth_id, invited=invited_id).first()
    if friend1 or friend2:
        return jsonify({"error_message": "You are already friends with this user"}), 409

    # 查找对应的邀请
    invitation = FriendInvite.query.filter_by(invitee=invited_id, invited=auth_id).first()

    if not invitation:
        return jsonify({"error_message": "No invitation found"}), 404

    if invitation.expires_at <= datetime.now():
        return jsonify({"error_message": "Invitation has expired"}), 410

    if res:  # 用户接受邀请
        id_chat = crear_private_chat(auth_id, invited_id)  # 创建私聊

        # 创建好友关系
        friendship = Friend(invitee=invited_id, invited=auth_id, id_chat=id_chat)
        try:
            friendship.save()
            invitation.accepted = True
            invitation.save()

            increment_achievement_of_user('ambassador', invited_id)
            increment_achievement_of_user('ambassador', auth_id)

            return jsonify({"message": "Friend request accepted", "is_friend": True}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"error_message": f"Failed to accept friend request: {str(e)}"}), 500

    else:  # 用户拒绝邀请
        try:
            invitation.accepted = False
            invitation.save()
            return jsonify({"message": "Friend request rejected"}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"error_message": f"Failed to reject friend request: {str(e)}"}), 500

# @module_users_v2.route('/new_friend', methods=['GET'])
# @jwt_required(optional=False)
# def get_friend_link():
#     if not (request.args and 'code' in request.args):
#         return jsonify({"error_message": "Missing argument code"}), 400

#     code = request.args['code']

#     auth_id = uuid.UUID(get_jwt_identity())
#     if BannedUsers.exists_user(auth_id):
#         return jsonify({'error_message': 'This email is banned'}), 409
#     invitation = FriendInvite.query.filter_by(code = code).filter(FriendInvite.expires_at > datetime.now(timezone.utc)).first()
#     if invitation == None:
#         return jsonify({"error_message": "Code does not exist or it has expired"}), 404
#     if BannedUsers.exists_user(invitation.invitee):
#         return jsonify({'error_message': 'This email is banned'}), 409
#     if invitation.invitee == auth_id:
#         return jsonify({"error_message": "Can't add yourself as your frind, but you dou have high self esteem."}), 400
    
#     if invitation.invitee in [user.id for user in Friend.getFriendsOfUserId(auth_id)]:
#         return jsonify({"error_message": "You are already friends with this user"}), 409

#     # # Increment achievement when add new friend

#     # invitation.delete()
#     return get_profile(str(invitation.invitee))




@module_users_v2.route('/accept_friend', methods=['POST'])
@jwt_required(optional=False)
def accept_friend_link():
    if not request.json:
        return jsonify({'error_message': 'Missing json object'}), 400     
    if 'code' not in request.json:
        return jsonify({'error_message': 'Code attribute missing in json'}), 400 

    code = request.json['code']

    auth_id = uuid.UUID(get_jwt_identity())
    if BannedUsers.exists_user(auth_id):
        return jsonify({'error_message': 'This email is banned'}), 409
    invitation = FriendInvite.query.filter_by(code = code).filter(FriendInvite.expires_at > datetime.now(timezone.utc)).first()
    if invitation == None:
        return jsonify({"error_message": "Code does not exist or it has expired"}), 404
    if BannedUsers.exists_user(invitation.invitee):
        return jsonify({'error_message': 'This email is banned'}), 409
    if invitation.invitee == auth_id:
        return jsonify({"error_message": "Can't add yourself as your frind, but you dou have high self esteem."}), 400
    
    if invitation.invitee in [user.id for user in Friend.getFriendsOfUserId(auth_id)]:
        return jsonify({"error_message": "You are already friends with this user"}), 409
    
    id_chat = crear_private_chat(auth_id, invitation.invitee)

    friendship = Friend(invitation.invitee, auth_id, id_chat)
    friendship.save()


    # # Increment achievement when add new friend
    increment_achievement_of_user('ambassador', invitation.invitee)
    increment_achievement_of_user('ambassador', invitation.auth_id)

    # invitation.delete()
    return get_profile(str(invitation.invitee))


@module_users_v2.route('/<id>/report/', methods=['POST'])
@jwt_required(optional=False)
def report_user(id): 
    try:
        auth_id = uuid.UUID(get_jwt_identity())
        if BannedUsers.exists_user(auth_id):
            return jsonify({'error_message': 'user_id'}), 409
        try:
            user_id = uuid.UUID(id)
        except:
            return jsonify({"error_message": "user_id isn't a valid UUID"}), 400
        user = User.query.filter_by(id=user_id)
        
        if user is None:
            return jsonify({"error_message": f"User {user_id} doesn't exist"}), 400
        if BannedUsers.exists_user(user_id):
            return jsonify({'error_message': 'This email is banned'}), 409
        
        if "comment" not in request.json:
            return jsonify({"error_message": "comment is not in the body"}), 400
        report = ReportedUser.query.filter_by(id_user=auth_id, id_user_reported=user_id)
        if report is not None:
            return jsonify({'error_message': 'You have already report this user'}), 409
        new_report = ReportedUser(id_user=auth_id, id_user_reported=user_id, comment=request.json['comment'])
        try:
            new_report.save()
        except sqlalchemy.exc.IntegrityError:
            return jsonify({"error_message": "Integrity error, FK violated (algo no esta definido en la BD) o ya existe el report en la DB"}), 400
        except:
            return jsonify({"error_message": "Error de DB nuevo, cual es?"}), 400
        return new_report.toJSON(), 201
    except:
        return jsonify({"error_message": "Unexpected error"}), 400 