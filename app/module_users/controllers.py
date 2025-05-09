# Import flask dependencies
from flask import Blueprint, jsonify, request
from app.module_chat.controllers import borrar_todos_chats_usuario
from app.module_event.models import Event
from flask_jwt_extended import create_access_token, create_refresh_token, get_jwt_identity, jwt_required, get_jwt
from datetime import datetime, timedelta, timezone
#from google.oauth2 import id_token
#from google.auth.transport import requests
import requests
import uuid

# Import the database object from the main app module
from app import db

# Import the hashing object from the main app module
from app import hashing

# Import util functions
from app.utils.email import send_email
from app.module_users.utils import increment_achievement_of_user, user_id_for_email, authentication_methods_for_user_id, send_verification_code_to, generate_tokens, get_random_salt, verify_password_strength,EmailVerificationPendant

# Import module models
from app.module_users.models import AchievementProgress, FriendInvite, User, ViajuntosAuth, GoogleAuth, FacebookAuth,GithubAuth, EmailVerificationPendant, Friend, UserLanguage, BannedUsers, premium_expiration
from app.module_admin.models import Admin
from app.module_chat.models import Message, Chat
from app.module_event.models import Like, Participant
from app.module_event.controllers_v3 import delete_event

# Define the blueprint: 'users', set its url prefix: app.url/users
module_users_v1 = Blueprint('users', __name__, url_prefix='/v1/users')


###################################### PROFILE / CREDENTIALS ######################################

@module_users_v1.route('/<id>', methods=['GET'])
@jwt_required(optional=True)
def get_profile(id):
    auth_id = get_jwt_identity()
    is_authenticated_id = id == auth_id
    
    if BannedUsers.exists_user(auth_id):
        return jsonify({'error_message': 'This User is banned'}), 409
    try:
        user_id = uuid.UUID(id)
    except:
        return jsonify({'error_message': 'ID is not a valid UUID'}), 400
    query_result = User.query.filter_by(id = user_id).first()
    if query_result == None:
            return jsonify({'error_message':f'User with id {id} does not exist'}), 404
    profile = query_result.toJSON()
    profile['profile_img_uri'] = ''
    profile['mini_profile_img_uri'] = ''
    if is_authenticated_id:
        profile['friends'] = []
    else:
        del profile['email']
    return jsonify(profile), 200

@module_users_v1.route('/<id>', methods=['PUT'])
@jwt_required(optional=False)
def update_profile(id):
    auth_id = get_jwt_identity()
    if id != auth_id:
        return jsonify({'error_message': 'Only the owner of the profile can update it'}), 403
    if BannedUsers.exists_user(auth_id):
        return jsonify({'error_message': 'This User is banned'}), 409
    if 'username' not in request.json:
        return jsonify({'error_message': 'Username attribute missing in json'}), 400
    if 'description' not in request.json:
        return jsonify({'error_message': 'Description attribute missing in json'}), 400
    if 'languages' not in request.json:
        return jsonify({'error_message': 'Languages list attribute missing in json'}), 400
    if 'hobbies' not in request.json:
        return jsonify({'error_message': 'Hobbies list attribute missing in json'}), 400
    if 'image_url' not in request.json:
        return jsonify({'error_message': 'image_url list attribute missing in json'}), 400
    if 'isPremium' not in request.json:
        return jsonify({'error_message': 'isPremium list attribute missing in json'}), 400
    
    username = request.json['username']
    description = request.json['description']
    languages = request.json['languages']
    hobbies = request.json['hobbies']
    image_url = request.json['image_url']
    isPremium = request.json['isPremium']
    update_premium(auth_id,isPremium)
    if len(languages) == 0 or any([l not in ['catalan', 'spanish', 'english'] for l in languages]):
        return jsonify({'error_message': 'Languages must be a subset of the following: {catalan, spanish, english}'}), 400

    user = User.query.filter_by(id = uuid.UUID(id)).first()
    if (user == None):
        return jsonify({'error_message': f'User does not exist for id {id}'}), 404
    
    if (len(description) > 180):
        return jsonify({'error_message': f'Description is too long. No more than 180 characters allowed.'}), 400

    user.username = username
    user.description = description
    user.hobbies = hobbies
    user.image_url = image_url
    try:
        user.save()
    except:
        return jsonify({'error_message': f'An error occured when updating user {id}'}), 500
    
    if len(description) > 120:
        increment_achievement_of_user('storyteller', user.id)

    user_languages = UserLanguage.query.filter_by(user = user.id).all()
    for ul in user_languages:
        if ul.language.value not in languages:
            try:
                ul.delete()
            except:
                return jsonify({'error_message': f'An error occured when updating previous language {ul.language.value}'}), 500
        else:
            languages.remove(ul.language.value)
    for l in languages:
        try:
            UserLanguage(user.id, l).save()
        except:
            return jsonify({'error_message': f'An error occured when updating new language {l}'}), 500

    profile = user.toJSON()
    # Añadir amigos
    friends = Friend.getFriendsOfUserId(user.id)
    profile['friends'] = [{'id': f.id, 'username': f.username} for f in friends]
    # Añadir idiomas
    user_languages = UserLanguage.query.filter_by(user = user.id).all()
    profile['languages'] = [ str(l.language.value) for l in user_languages ]

    return jsonify(profile), 200

def update_premium(id,isPremium):
    pre_exp = premium_expiration.query.filter_by(user = id).first()
    if pre_exp is None:
        new_premium_expiration = premium_expiration(id,datetime.now()+ timedelta(days=365))
        new_premium_expiration.save()
    else:
        pre_exp.delete()
    

@module_users_v1.route('/<id>/update_premium', methods=['POST'])
@jwt_required(optional=False)
def purchase_premium(id):
    auth_id = get_jwt_identity()
    if BannedUsers.exists_user(auth_id):
        return jsonify({'error_message': 'This email is banned'}), 409
    if id != auth_id:
        return jsonify({'error_message': 'Only the owner of the profile can update it'}), 403
    pre_exp = premium_expiration.query.filter_by(user = auth_id).first()
    if pre_exp is None:
        new_premium_expiration = premium_expiration(auth_id,datetime.now()+ timedelta(days=365))
        new_premium_expiration.save()
        return jsonify({'message': 'Premuim actived'}), 200
    else:
        pre_exp.delete()
        return jsonify({'message': 'Premuim desactived'}), 200

@module_users_v1.route('/<id>/get_premium', methods=['GET'])
@jwt_required(optional=False)
def get_premium(id):
    auth_id = get_jwt_identity()
    if BannedUsers.exists_user(auth_id):
        return jsonify({'error_message': 'This email is banned'}), 409
    if id != auth_id:
        return jsonify({'error_message': 'Only the owner of the profile can update it'}), 403
    pre_exp = premium_expiration.query.filter_by(user = auth_id).first()
    if pre_exp is None:
        return jsonify({'message': 'User is not Premium'}), 200
    else:        
        if pre_exp.expiration_at < datetime.now():
            return jsonify({'message': 'User is not Premium'}), 200
        return jsonify({'message': 'User is Premium'}), 200

@module_users_v1.route('/<id>/pw', methods=['POST'])
@jwt_required(optional=False)
def change_password(id):
    if not ('old' in  request.json and 'new' in request.json):
        return jsonify({'error_message': 'Missing old or new password in json body.'}), 400 
    old_pw = request.json['old']
    new_pw = request.json['new']

    # Check new password requirements
    if old_pw == new_pw:
        return jsonify({'error_message': 'Old and new passwords must be different'}), 400
    
    # Check password strength
    pw_msg, pw_status = verify_password_strength(new_pw)
    if pw_status != 200: return pw_msg, pw_status

    auth_id = get_jwt_identity()
    if BannedUsers.exists_user(auth_id):
        return jsonify({'error_message': 'This email is banned'}), 409
    if id != auth_id:
        return jsonify({'error_message': 'Only the owner of the account can change its password'}), 403
    viajuntos_auth = ViajuntosAuth.query.filter_by(id = uuid.UUID(id)).first()
    if viajuntos_auth == None:
        return jsonify({'error_message': 'Viajuntos authentication method not available for this user, can not change password'}), 400 
    if not hashing.check_value(viajuntos_auth.pw, old_pw, salt=viajuntos_auth.salt):
        return jsonify({'error_message': 'Wrong old password'}), 400

    debug = f'{viajuntos_auth.salt} - {viajuntos_auth.pw}'

    # Add viajuntos auth method to user
    user_salt = get_random_salt(15)
    hashed_pw = hashing.hash_value(new_pw, salt=user_salt)
    viajuntos_auth.salt = user_salt
    viajuntos_auth.pw = hashed_pw
    try:
        db.session.commit()
    except:
        return jsonify({'error_message': f'Something went wrong when changing password for user {id}, {user_salt}, {new_pw}, {hashed_pw} .... {debug}'}), 500

    user = User.query.filter_by(id = uuid.UUID(id)).first()
    send_email(user.email, 'Viajuntos password change notice!', f'Your password was recently changed, if it was not you, please log into your {user.username} account by clicking on "Forgot password" in the login screen.')
    return generate_tokens(str(user.id)), 200

############################################ REGISTER #############################################

@module_users_v1.route('/register/check', methods=['GET'])
def check_register_status():
    if 'type' not in request.args:
        return jsonify({'error_message': 'Must indicate type of authentication to check {viajuntos, google, facebook}'}), 400
    type = request.args['type']
    if type == 'viajuntos':
        return check_register_status_viajuntos(request.args)
    if type == 'google':
        return check_register_status_google(request.args)
    if type == 'facebook':
        return check_register_status_facebook(request.args)
    return jsonify({'error_message': 'Type of authentication must be one of {viajuntos, google, facebook}'}), 400

def check_register_status_viajuntos(args):
    if 'email' not in args:
        return jsonify({'error_message': 'Viajuntos auth method must indicate an email'}), 400
    email = args['email']
    if BannedUsers.exists_email(email):
        return jsonify({'error_message': 'This User is banned'}), 409
    user_id = user_id_for_email(email)
    if user_id == None:
        send_verification_code_to(email)
        return jsonify({'action': 'continue'}), 200
    # check if it is viajuntos
    auth_methods = authentication_methods_for_user_id(user_id)
    if 'viajuntos' in auth_methods:
        return jsonify({'action': 'error', 'error_message': 'User with this email already exists'}), 200
    send_verification_code_to(email)
    return jsonify({'action': 'link_auth', 'alternative_auths': auth_methods}), 200

def check_register_status_google(args):
    if 'token' not in args:
        return jsonify({'error_message': 'Google auth method must indicate a token'}), 400
    token = args['token']
    # Get google email from token
    try:
        idinfo = requests.get(f'https://www.googleapis.com/oauth2/v3/userinfo?access_token={token}')
        #idinfo = id_token.verify_oauth2_token(token, requests.Request(), os.getenv('GOOGLE_CLIENT_ID'))
        email = idinfo.json()['email']
    except:
        return jsonify({'error_message': 'Google token was invalid'}), 400
    if BannedUsers.exists(email):
        return jsonify({'error_message': 'This User is banned'}), 409
    user_id = user_id_for_email(email)
    if user_id == None:
        return jsonify({'action': 'continue'}), 200
    # check if it is google
    auth_methods = authentication_methods_for_user_id(user_id)
    if 'google' in auth_methods:
        return jsonify({'action': 'error', 'error_message': 'User with this email already exists'}), 200
    return jsonify({'action': 'link_auth', 'alternative_auths': auth_methods}), 200

def check_register_status_facebook(args):
    if 'token' not in args:
        return jsonify({'error_message': 'Google auth method must indicate a token'}), 400
    token = args['token']
    # Get email from facebook token
    try:
        idinfo = requests.get(f'https://graph.facebook.com/me?fields=email&access_token={token}')
        email = idinfo.json()['email']
    except:
        return jsonify({'error_message': 'Facebook token was invalid'}), 400
    if BannedUsers.exists(email):
        return jsonify({'error_message': 'This User is banned'}), 409
    user_id = user_id_for_email(email)
    if user_id == None:
        return jsonify({'action': 'continue'}), 200
    # check if it is google
    auth_methods = authentication_methods_for_user_id(user_id)
    if 'facebook' in auth_methods:
        return jsonify({'action': 'error', 'error_message': 'User with this email already exists'}), 200
    return jsonify({'action': 'link_auth', 'alternative_auths': auth_methods}), 200


@module_users_v1.route('/register/viajuntos', methods=['POST'])
def register_viajuntos():
    if 'email' not in request.json:
        return jsonify({'error_message': 'Email attribute missing in json'}), 400 
    if 'password' not in request.json:
        return jsonify({'error_message': 'Password attribute missing in json'}), 400 
    if 'username' not in request.json:
        return jsonify({'error_message': 'Username attribute missing in json'}), 400 
    if 'description' not in request.json:
        return jsonify({'error_message': 'Description attribute missing in json'}), 400 
    if 'languages' not in request.json:
        return jsonify({'error_message': 'Languages list attribute missing in json'}), 400 
    if 'hobbies' not in request.json:
        return jsonify({'error_message': 'Hobbies list attribute missing in json'}), 400 
    if 'verification' not in request.json:
        return jsonify({'error_message': 'Verification code attribute missing in json'}), 400 
    
    email = request.json['email']
    pw = request.json['password']
    username = request.json['username']
    description = request.json['description']
    languages = request.json['languages']
    hobbies = request.json['hobbies']
    verification = request.json['verification']
    if len(languages) == 0 or any([l not in ['catalan', 'spanish', 'english'] for l in languages]):
        
        return jsonify({'error_message': 'Languages must be a subset of the following: {catalan, spanish, english}'}), 400

    if BannedUsers.exists_email(email):
        return jsonify({'error_message': 'This User is banned'}), 409
    # Check no other user exists with that email
    if user_id_for_email(email) != None:
        return jsonify({'error_message': 'User with this email already exists'}), 400
    # Check password strength
    pw_msg, pw_status = verify_password_strength(pw)
    if pw_status != 200: return pw_msg, pw_status
    # Check verification code in codes sent to email
    db_verification = EmailVerificationPendant.query.filter(EmailVerificationPendant.email == email).filter(EmailVerificationPendant.expires_at > datetime.now(timezone.utc)).first()
    if db_verification == None:
        return jsonify({'error_message': 'Verification code was never sent to this email or the code has expired.'}), 400
    if db_verification.code != verification:
        return jsonify({'error_message': 'Verification code does not coincide with code sent to email'}), 400
    
    if (len(description) > 180):
        return jsonify({'error_message': f'Description is too long. No more than 180 characters allowed.'}), 400
    # Add user to bd
    user_id = uuid.uuid4()
    user = User(user_id, username, email, description, hobbies,"")
    try:
        user.save()
    except:
        return jsonify({'error_message': 'Something went wrong when creating new user in db.'}), 500
    # Add languages to user
    for l in languages:
        try:
            UserLanguage(user_id, l).save()
        except:
            return jsonify({'error_message': f'An error occured when adding language {l} to new user.'}), 500
    
    # Add viajuntos auth method to user
    user_salt = get_random_salt(15)
    hashed_pw = hashing.hash_value(pw, salt=user_salt)
    viajuntos_auth = ViajuntosAuth(user_id, user_salt, hashed_pw)
    # Increment achievement
    #todo
    if len(description) > 120:
        increment_achievement_of_user('storyteller', user_id)
    # increment_achievement_of_user('credential_multiverse', user_id)
    try:
        viajuntos_auth.save()
    except:
        return jsonify({'error_message': 'Something went wrong when adding auth method viajuntos to user.'}), 500

    # Remove verification code -> already used
    db_verification.delete()
    return generate_tokens(str(user_id)), 200

@module_users_v1.route('/register/google', methods=['POST'])
def register_google():
    if 'token' not in request.json:
        return jsonify({'error_message': 'Token attribute missing in json'}), 400 
    if 'username' not in request.json:
        return jsonify({'error_message': 'Username attribute missing in json'}), 400 
    if 'description' not in request.json:
        return jsonify({'error_message': 'Description attribute missing in json'}), 400 
    if 'languages' not in request.json:
        return jsonify({'error_message': 'Languages list attribute missing in json'}), 400 
    if 'hobbies' not in request.json:
        return jsonify({'error_message': 'Hobbies list attribute missing in json'}), 400
    
    token = request.json['token']
    username = request.json['username']
    description = request.json['description']
    languages = request.json['languages']
    hobbies = request.json['hobbies']
    
    if len(languages) == 0 or any([l not in ['catalan', 'spanish', 'english'] for l in languages]):
        return jsonify({'error_message': 'Languages must be a subset of the following: {catalan, spanish, english}'}), 400

    # Get google email from token
    try:
        idinfo = requests.get(f'https://www.googleapis.com/oauth2/v3/userinfo?access_token={token}')
        #idinfo = id_token.verify_oauth2_token(token, requests.Request(), os.getenv('GOOGLE_CLIENT_ID'))
        email = idinfo.json()['email']
    except:
        return jsonify({'error_message': 'Google token was invalid'}), 400
    
    if BannedUsers.exists(email):
        return jsonify({'error_message': 'This User is banned'}), 409
    
    # Check no other user exists with that email
    if user_id_for_email(email) != None:
        return jsonify({'error_message': 'User with this email already exists'}), 400
    
    if (len(description) > 180):
        return jsonify({'error_message': f'Description is too long. No more than 180 characters allowed.'}), 400

    # Add user to bd
    user_id = uuid.uuid4()
    user = User(user_id, username, email, description, hobbies)
    try:
        user.save()
    except:
        return jsonify({'error_message': 'Something went wrong when creating new user in db'}), 500
    
    # Add languages to user 
    for l in languages:
        try:
            UserLanguage(user_id, l).save()
        except:
            return jsonify({'error_message': f'An error occured when adding language {l} to new user.'}), 500
    
    # Add google auth method to user
    google_auth = GoogleAuth(user_id, token)

    # Increment achievement
    if len(description) > 120:
        increment_achievement_of_user('storyteller', user_id)
    # increment_achievement_of_user('credential_multiverse', user_id)

    try:
        google_auth.save()
    except:
        return jsonify({'error_message': 'Something went wrong when adding auth method google to user'}), 500
    
    return generate_tokens(str(user_id)), 200

@module_users_v1.route('/register/github', methods=['POST'])
def register_github():
    if 'token' not in request.json:
        return jsonify({'error_message': 'Token attribute missing in json'}), 400 
    if 'username' not in request.json:
        return jsonify({'error_message': 'Username attribute missing in json'}), 400 
    if 'description' not in request.json:
        return jsonify({'error_message': 'Description attribute missing in json'}), 400 
    if 'languages' not in request.json:
        return jsonify({'error_message': 'Languages list attribute missing in json'}), 400 
    if 'hobbies' not in request.json:
        return jsonify({'error_message': 'Hobbies list attribute missing in json'}), 400
    
    token = request.json['token']
    username = request.json['username']
    description = request.json['description']
    languages = request.json['languages']
    hobbies = request.json['hobbies']
    
    if len(languages) == 0 or any([l not in ['catalan', 'spanish', 'english'] for l in languages]):
        return jsonify({'error_message': 'Languages must be a subset of the following: {catalan, spanish, english}'}), 400

    # Get github email from token
    try:
        idinfo = requests.get(f'https://www.googleapis.com/oauth2/v3/userinfo?access_token={token}')
        #idinfo = id_token.verify_oauth2_token(token, requests.Request(), os.getenv('GOOGLE_CLIENT_ID'))
        email = idinfo.json()['email']
    except:
        return jsonify({'error_message': 'Google token was invalid'}), 400
    
    if BannedUsers.exists(email):
        return jsonify({'error_message': 'This User is banned'}), 409
    
    # Check no other user exists with that email
    if user_id_for_email(email) != None:
        return jsonify({'error_message': 'User with this email already exists'}), 400
    
    if (len(description) > 180):
        return jsonify({'error_message': f'Description is too long. No more than 180 characters allowed.'}), 400

    # Add user to bd
    user_id = uuid.uuid4()
    user = User(user_id, username, email, description, hobbies)
    try:
        user.save()
    except:
        return jsonify({'error_message': 'Something went wrong when creating new user in db'}), 500
    
    # Add languages to user 
    for l in languages:
        try:
            UserLanguage(user_id, l).save()
        except:
            return jsonify({'error_message': f'An error occured when adding language {l} to new user.'}), 500
    
    # Add github auth method to user
    github_auth = GithubAuth(user_id, token)

    # Increment achievement
    if len(description) > 120:
        increment_achievement_of_user('storyteller', user_id)
    # increment_achievement_of_user('credential_multiverse', user_id)

    try:
        github_auth.save()
    except:
        return jsonify({'error_message': 'Something went wrong when adding auth method github to user'}), 500
    
    return generate_tokens(str(user_id)), 200

@module_users_v1.route('/register/facebook', methods=['POST'])
def register_facebook():
    if 'token' not in request.json:
        return jsonify({'error_message': 'Token attribute missing in json'}), 400 
    if 'username' not in request.json:
        return jsonify({'error_message': 'Username attribute missing in json'}), 400 
    if 'description' not in request.json:
        return jsonify({'error_message': 'Description attribute missing in json'}), 400 
    if 'languages' not in request.json:
        return jsonify({'error_message': 'Languages list attribute missing in json'}), 400 
    if 'hobbies' not in request.json:
        return jsonify({'error_message': 'Hobbies list attribute missing in json'}), 400
    
    token = request.json['token']
    username = request.json['username']
    description = request.json['description']
    languages = request.json['languages']
    hobbies = request.json['hobbies']
    
    if len(languages) == 0 or any([l not in ['catalan', 'spanish', 'english'] for l in languages]):
        return jsonify({'error_message': 'Languages must be a subset of the following: {catalan, spanish, english}'}), 400

    # Get email from facebook token
    try:
        idinfo = requests.get(f'https://graph.facebook.com/me?fields=email&access_token={token}')
        email = idinfo.json()['email']
    except:
        return jsonify({'error_message': 'Google token was invalid'}), 400
    
    if BannedUsers.exists(email):
        return jsonify({'error_message': 'This User is banned'}), 409
    
    # Check no other user exists with that email
    if user_id_for_email(email) != None:
        return jsonify({'error_message': 'User with this email already exists'}), 400

    if (len(description) > 180):
        return jsonify({'error_message': f'Description is too long. No more than 180 characters allowed.'}), 400

    # Add user to bd
    user_id = uuid.uuid4()
    user = User(user_id, username, email, description, hobbies)
    try:
        user.save()
    except:
        return jsonify({'error_message': 'Something went wrong when creating new user in db'}), 500
    
    # Add languages to user
    for l in languages:
        try:
            UserLanguage(user_id, l).save()
        except:
            return jsonify({'error_message': f'An error occured when adding language {l} to new user.'}), 500
    
    # Add facebook auth method to user
    facebook_auth = FacebookAuth(user_id, token)

    # Increment achievement
    if len(description) > 120:
        increment_achievement_of_user('storyteller', user_id)
    # increment_achievement_of_user('credential_multiverse', user_id)

    try:
        facebook_auth.save()
    except:
        return jsonify({'error_message': 'Something went wrong when adding auth method facebook to user'}), 500
    
    return generate_tokens(str(user_id)), 200


############################################# LOGIN ###############################################

@module_users_v1.route('/login/check', methods=['GET'])
def check_login_status():
    if 'type' not in request.args:
        return jsonify({'error_message': 'Must indicate type of authentication to check {viajuntos, google, facebook}'}), 400
    type = request.args['type']
    email = request.args['email']
    if BannedUsers.exists_email(email):
        return jsonify({'error_message': 'This User is banned'}), 409
    if type == 'viajuntos':
        return check_login_status_viajuntos(request.args)
    if type == 'google':
        return check_login_status_google(request.args)
    if type == 'facebook':
        return check_login_status_facebook(request.args)

    return jsonify({'error_message': 'Type of authentication must be one of {viajuntos, google, facebook}'}), 400

def check_login_status_viajuntos(args):
    if 'email' not in args:
        return jsonify({'error_message': 'Viajuntos auth method must indicate an email'}), 400
    email = args['email']
    user_id = user_id_for_email(email)
    if user_id == None:
        return jsonify({'action': 'error', 'error_message': 'Account does not exist'}), 200
    # check if it is viajuntos
    auth_methods = authentication_methods_for_user_id(user_id)
    if 'viajuntos' in auth_methods:
        return jsonify({'action': 'continue'}), 200
    send_verification_code_to(email)
    return jsonify({'action': 'link_auth', 'alternative_auths': auth_methods}), 200

def check_login_status_google(args):
    if 'token' not in args:
        return jsonify({'error_message': 'Google auth method must indicate a token'}), 400
    token = args['token']
    # Get google email from token
    try:
        idinfo = requests.get(f'https://www.googleapis.com/oauth2/v3/userinfo?access_token={token}')
        #idinfo = id_token.verify_oauth2_token(token, requests.Request(), os.getenv('GOOGLE_CLIENT_ID'))
        email = idinfo.json()['email']
    except:
        return jsonify({'error_message': 'Google token was invalid'}), 400
    user_id = user_id_for_email(email)
    if user_id == None:
        return jsonify({'action': 'error', 'error_message': 'Account does not exist'}), 200
    # check if it is google
    auth_methods = authentication_methods_for_user_id(user_id)
    if 'google' in auth_methods:
        return jsonify({'action': 'continue'}), 200
    return jsonify({'action': 'link_auth', 'alternative_auths': auth_methods}), 200

def check_login_status_facebook(args):
    if 'token' not in args:
        return jsonify({'error_message': 'Facebook auth method must indicate a token'}), 400
    token = args['token']
    # Get email from facebook token
    try:
        idinfo = requests.get(f'https://graph.facebook.com/me?fields=email&access_token={token}')
        email = idinfo.json()['email']
    except:
        return jsonify({'error_message': 'Facebook token was invalid'}), 400
    user_id = user_id_for_email(email)
    if user_id == None:
        return jsonify({'action': 'error', 'error_message': 'Account does not exist'}), 200
    # check if it is facebook
    auth_methods = authentication_methods_for_user_id(user_id)
    if 'facebook' in auth_methods:
        return jsonify({'action': 'continue'}), 200
    return jsonify({'action': 'link_auth', 'alternative_auths': auth_methods}), 200

@module_users_v1.route('/login/viajuntos', methods=['POST'])
def login_viajuntos():
    if not ('email' in  request.json and 'password' in request.json):
        return jsonify({'error_message': 'Missing credentials in json body.'}), 400 
    email = request.json['email']
    password = request.json['password']
    user = User.query.filter_by(email = email).first()
    if BannedUsers.exists_email(email):
        return jsonify({'error_message': 'This User is banned'}), 409
    if user == None:
        return jsonify({'error_message': 'Email or password are wrong.'}), 400 
    viajuntos_auth = ViajuntosAuth.query.filter_by(id = user.id).first()
    if viajuntos_auth == None:
        return jsonify({'error_message': 'Authentication method not available for this email'}), 400 
    if not hashing.check_value(viajuntos_auth.pw, password, salt=viajuntos_auth.salt):
        return jsonify({'error_message': 'Email or password are wrong.'}), 400 
    return generate_tokens(str(user.id)), 200

@module_users_v1.route('/login/google', methods=['POST'])
def login_google():
    if 'token' not in request.json:
        return jsonify({'error_message': 'Missing credentials in json body.'}), 400 
    token = request.json['token']
    # Get google email from token
    try:
        idinfo = requests.get(f'https://www.googleapis.com/oauth2/v3/userinfo?access_token={token}')
        #idinfo = id_token.verify_oauth2_token(token, requests.Request(), os.getenv('GOOGLE_CLIENT_ID'))
        email = idinfo.json()['email']
    except:
        return jsonify({'error_message': 'Google token was invalid'}), 400
    
    if BannedUsers.exists(email):
        return jsonify({'error_message': 'This User is banned'}), 409
    user = User.query.filter_by(email = email).first()
    if user == None:
        return jsonify({'error_message': 'User does not exist'}), 400 
    google_auth = GoogleAuth.query.filter_by(id = user.id).first()
    if google_auth == None:
        return jsonify({'error_message': 'Authentication method not available for this email'}), 400
    google_auth.access_token = token
    google_auth.save()
    return generate_tokens(str(user.id)), 200

@module_users_v1.route('/login/github', methods=['POST'])
def login_github():
    if 'token' not in request.json:
        return jsonify({'error_message': 'Missing credentials in json body.'}), 400 
    token = request.json['token']
    # Get github email from token
    try:
        idinfo = requests.get(f'https://www.githubapis.com/oauth2/v3/userinfo?access_token={token}')
        #idinfo = id_token.verify_oauth2_token(token, requests.Request(), os.getenv('GITHUB_CLIENT_ID'))
        email = idinfo.json()['email']
    except:
        return jsonify({'error_message': 'Github token was invalid'}), 400
    
    if BannedUsers.exists(email):
        return jsonify({'error_message': 'This User is banned'}), 409
    user = User.query.filter_by(email = email).first()
    if user == None:
        return jsonify({'error_message': 'User does not exist'}), 400 
    github_auth = GithubAuth.query.filter_by(id = user.id).first()
    if github_auth == None:
        return jsonify({'error_message': 'Authentication method not available for this email'}), 400
    github_auth.access_token = token
    github_auth.save()
    return generate_tokens(str(user.id)), 200

@module_users_v1.route('/login/facebook', methods=['POST'])
def login_facebook():
    if 'token' not in request.json:
        return jsonify({'error_message': 'Missing credentials in json body.'}), 400 
    token = request.json['token']
    # Get email from facebook token
    try:
        idinfo = requests.get(f'https://graph.facebook.com/me?fields=email&access_token={token}')
        email = idinfo.json()['email']
    except:
        return jsonify({'error_message': 'Facebook token was invalid'}), 400
    
    if BannedUsers.exists(email):
        return jsonify({'error_message': 'This User is banned'}), 409
    user = User.query.filter_by(email = email).first()
    if user == None:
        return jsonify({'error_message': 'User does not exist'}), 400 
    facebook_auth = FacebookAuth.query.filter_by(id = user.id).first()
    if facebook_auth == None:
        return jsonify({'error_message': 'Authentication method not available for this email'}), 400
    facebook_auth.access_token = token
    facebook_auth.save()
    return generate_tokens(str(user.id)), 200

@module_users_v1.route('/refresh', methods=['GET'])
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()
    
    if BannedUsers.exists_user(identity):
        return jsonify({'error_message': 'This User is banned'}), 409
    access_token = create_access_token(identity=identity)
    exp_timestamp = get_jwt()["exp"]
    now = datetime.now(timezone.utc)
    target_timestamp = datetime.timestamp(now + timedelta(days=2))
    if target_timestamp > exp_timestamp:
        refresh_token = create_refresh_token(identity=identity)
        return jsonify({'id': identity, 'access_token': access_token, 'refresh_token': refresh_token})
    return jsonify({'id': identity, 'access_token': access_token})


########################################## ADD AUTH METHOD ########################################

@module_users_v1.route('/auth_method', methods=['POST'])
def link_auth_method():
    if 'type' not in request.json:
        return jsonify({'error_message': 'Must indicate type of authentication to link {viajuntos, google, facebook}'}), 400
    if 'credentials' not in request.json:
        return jsonify({'error_message': 'Missing attribute credentials in json body'}), 400
    type = request.json['type']
    if type == 'viajuntos':
        return link_viajuntos_auth_method(request.json['credentials'])
    if type == 'google':
        return link_google_auth_method(request.json['credentials'])
    if type == 'facebook':
        return link_facebook_auth_method(request.json['credentials'])

def link_viajuntos_auth_method(args):
    if not ('email' in args and 'password' in args and 'verification' in args):
        return jsonify({'error_message': 'Viajuntos auth method must indicate email, password and verification in credentials'}), 400
    email = args['email']
    if BannedUsers.exists(email):
        return jsonify({'error_message': 'This User is banned'}), 409
    password = args['password']
    verification = args['verification']
    user_id = user_id_for_email(email)
    # Check user exists
    if user_id == None:
        return jsonify({'error_message': 'User with this email does not exist, please register first'}), 400

    # Check password strength
    pw_msg, pw_status = verify_password_strength(password)
    if pw_status != 200: return pw_msg, pw_status

    # Check verification code in codes sent to email
    db_verification = EmailVerificationPendant.query.filter(EmailVerificationPendant.email == email).filter(EmailVerificationPendant.expires_at > datetime.now(timezone.utc)).first()
    if db_verification == None:
        return jsonify({'error_message': 'Verification code was never sent to this email or the code has expired.'}), 400
    if db_verification.code != verification:
        return jsonify({'error_message': 'Verification code does not coincide with code sent to email'}), 400
    
    # Add viajuntos auth method to user
    user_salt = get_random_salt(15)
    hashed_pw = hashing.hash_value(password, salt=user_salt)
    viajuntos_auth = ViajuntosAuth(user_id, user_salt, hashed_pw)

    # Increment achievement
    # increment_achievement_of_user('credential_multiverse', user_id)

    try:
        viajuntos_auth.save()
    except:
        return jsonify({'error_message': 'Something went wrong when adding auth method viajuntos to user'}), 500

    # Remove verification code -> already used
    db_verification.delete()
    
    return generate_tokens(str(user_id)), 200

def link_google_auth_method(args):
    if 'token' not in args:
        return jsonify({'error_message': 'Google auth method must indicate token in credentials'}), 400
    token = args['token']
    # Get google email from token
    try:
        idinfo = requests.get(f'https://www.googleapis.com/oauth2/v3/userinfo?access_token={token}')
        #idinfo = id_token.verify_oauth2_token(token, requests.Request(), os.getenv('GOOGLE_CLIENT_ID'))
        email = idinfo.json()['email']
    except:
        return jsonify({'error_message': 'Google token was invalid'}), 400
    if BannedUsers.exists(email):
        return jsonify({'error_message': 'This User is banned'}), 409
    user_id = user_id_for_email(email)
    # Check user exists
    if user_id == None:
        return jsonify({'error_message': 'User with this email does not exist, please register first'}), 400
    
    # Check user does not already have google auth enabled
    google_auth = GoogleAuth.query.filter_by(id = user_id).first()
    if (google_auth != None):
        return jsonify({'error_message': 'Google auth method already linked to this account'}), 400
    
    # Add google auth method to user
    google_auth = GoogleAuth(user_id, token)

    # Increment achievement
    # increment_achievement_of_user('credential_multiverse', user_id)

    try:
        google_auth.save()
    except:
        return jsonify({'error_message': 'Something went wrong when adding auth method google to user'}), 500
    
    return generate_tokens(str(user_id)), 200

def link_github_auth_method(args):
    if 'token' not in args:
        return jsonify({'error_message': 'Github auth method must indicate token in credentials'}), 400
    token = args['token']
    # Get github email from token
    try:
        idinfo = requests.get(f'https://www.githubapis.com/oauth2/v3/userinfo?access_token={token}')
        #idinfo = id_token.verify_oauth2_token(token, requests.Request(), os.getenv('GITHUB_CLIENT_ID'))
        email = idinfo.json()['email']
    except:
        return jsonify({'error_message': 'Github token was invalid'}), 400
    if BannedUsers.exists(email):
        return jsonify({'error_message': 'This User is banned'}), 409
    user_id = user_id_for_email(email)
    # Check user exists
    if user_id == None:
        return jsonify({'error_message': 'User with this email does not exist, please register first'}), 400
    
    # Check user does not already have github auth enabled
    github_auth = GithubAuth.query.filter_by(id = user_id).first()
    if (github_auth != None):
        return jsonify({'error_message': 'Github auth method already linked to this account'}), 400
    
    # Add github auth method to user
    github_auth = GithubAuth(user_id, token)

    # Increment achievement
    # increment_achievement_of_user('credential_multiverse', user_id)

    try:
        github_auth.save()
    except:
        return jsonify({'error_message': 'Something went wrong when adding auth method github to user'}), 500
    
    return generate_tokens(str(user_id)), 200


def link_facebook_auth_method(args):
    if 'token' not in args:
        return jsonify({'error_message': 'Facebook auth method must indicate token in credentials'}), 400
    token = args['token']
    # Get google email from token
    try:
        idinfo = requests.get(f'https://graph.facebook.com/me?fields=email&access_token={token}')
        email = idinfo.json()['email']
    except:
        return jsonify({'error_message': 'Facebook token was invalid'}), 400
    if BannedUsers.exists(email):
        return jsonify({'error_message': 'This User is banned'}), 409
    user_id = user_id_for_email(email)
    # Check user exists
    if user_id == None:
        return jsonify({'error_message': 'User with this email does not exist, please register first'}), 400
    
    # Check user does not already have google auth enabled
    facebook_auth = FacebookAuth.query.filter_by(id = user_id).first()
    if (facebook_auth != None):
        return jsonify({'error_message': 'Facebook auth method already linked to this account'}), 400
    
    # Add facebook auth method to user
    facebook_auth = FacebookAuth(user_id, token)

    # Increment achievement
    # increment_achievement_of_user('credential_multiverse', user_id)

    try:
        facebook_auth.save()
    except:
        return jsonify({'error_message': 'Something went wrong when adding auth method google to user'}), 500
    
    return generate_tokens(str(user_id)), 200

########################################## DELETE ACCOUNT ########################################

@module_users_v1.route('/<id>/delete', methods=['DELETE'])
@jwt_required(optional=False)
def delete_account(id):
    #return jsonify({'message': 'You have successfully deleted your viajuntos account.'}), 201
    try:
        user_id = uuid.UUID(id)
    except:
        return jsonify({"error_message": "User_id isn't a valid UUID"}), 400
    if BannedUsers.exists(user_id):
        return jsonify({'error_message': 'This User is banned'}), 409
    try:
        user = User.query.get(user_id)
    except:
        return jsonify({"error_message": f"Error getting the event"}), 400

    if user is None:
        return jsonify({"error_message": f"The event {user_id} doesn't exist"}), 400

    # restricion: El usuario solo puede eliminar su cuenta propia (mirando Bearer Token)
    auth_id = get_jwt_identity()
    if id != auth_id:
        return jsonify({'error_message': 'Users can only delete their own account. '}), 403
    current_time = datetime.now()
    msg, status = borrar_todos_chats_usuario(user_id)
    if status != 202:
        return jsonify({'error_message': 'Chats cannot be successfully deleted.', 'details': msg['error_message']}), 500

    # Buscar los eventos creados por user
    all_events = Event.query.filter_by(user_creator = user.id).all()
    if all_events != None:
        for event in all_events:
            # Si el evento era futuro, notificar participantes de que el evento es cancelado.
            if current_time < event.date_started:
                
                event_date_str = event.date_started.strftime('%Y-%m-%d')
                for participant in event.participants_in_event:
                    
                    participant_user = User.query.filter_by(id = participant.user_id).first()
                    if participant_user.id != user.id:
                        send_email(participant_user.email, 'Event cancellation!', f'We are sorry to inform you that the event titled "{event.name}" that was scheduled for {event_date_str} has been cacelled.\n\nYours sincerely,\nThe Viajuntos team.')
                    Participant.query.filter_by(user_id = participant.id).delete()
                    # participant.delete()
            msg, status = delete_event(str(event.id))
            if status != 202:
                return jsonify({'error_message': 'Events cannot be successfully deleted.', 'details': msg['error_message']}), 500
            event.delete()


    # return jsonify({'error_message': 'Events cannot be successfully deleted.', 'details': msg['error_message']}), 500
    # Eliminar métodos de autenticación del usuario
    so_auth = ViajuntosAuth.query.filter_by(id = user.id).first()
    if so_auth != None:
        so_auth.delete()
    g_auth = GoogleAuth.query.filter_by(id = user.id).first()
    if g_auth != None:
        g_auth.delete()
    f_auth = FacebookAuth.query.filter_by(id = user.id).first()
    if f_auth != None:
        f_auth.delete()
    gh_auth = GithubAuth.query.filter_by(id = user.id).first()
    if gh_auth != None:
        gh_auth.delete()
    v_auth = ViajuntosAuth.query.filter_by(id = user.id).first()
    if v_auth != None:
        v_auth.delete()
    # Eliminar logros del usuario
    ach = AchievementProgress.query.filter_by(user = user.id).all()
    for a in ach:
        a.delete()
    # Eliminar correo verificacion del usuario
    evps = EmailVerificationPendant.query.filter_by(email = user.email).all()
    for evp in evps:
        evp.delete()
    # Eliminar like del usuario
    likes = Like.query.filter_by(user_id = user.id).all()
    for like in likes:
        like.delete()
    
    # Eliminar amistades del usuario
    friends = Friend.query.filter_by(invitee = user.id).all()
    friends.extend(Friend.query.filter_by(invited = user.id).all())
    for f in friends:
        f.delete()
    invitees = FriendInvite.query.filter_by(invitee = user.id).all()
    for invitee in invitees:
        invitee.delete()
    
    inviteds = FriendInvite.query.filter_by(invited = user.id).all()
    for invited in inviteds:
        invited.delete()
    
    # Eliminar relación idiomas de usuario
    lang = UserLanguage.query.filter_by(user = user.id).all()
    for l in lang:
        l.delete()
    # Eliminar relación admin de usuario
    admin = Admin.query.filter_by(id = user.id).all()
    for a in admin:
        a.delete()
        
    # Eliminar usuario
    try:
        user.delete()
    except Exception as e:
        return jsonify({'error_message': 'Error while deleting user instance', 'details': e}), 500
    
    # Notificar usuario
    email_body = f'Dear {user.username}, You have successfully deleted your viajuntos account.'
    send_email(user.email, 'You have been banned from Viajuntos', email_body)

    return jsonify({'message': 'You have successfully deleted your viajuntos account.'}), 200