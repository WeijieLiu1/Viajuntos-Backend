from email.policy import default
from app import db
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum

from app.module_chat.models import Chat

# Define a User model
class User(db.Model):
    __tablename__ = 'users'

    # User id
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4())
    # Username
    username = db.Column(db.String, nullable=False)
    # Email
    email = db.Column(db.String, unique=True, nullable=False)
    # User description / information
    description = db.Column(db.String, default="", nullable=False)
    # User hobbies
    hobbies = db.Column(db.String, default="", nullable=False)
    # User premuim
    # isPremuim = db.Column(db.bool, default=False, nullable=False)

    # User image url
    image_url = db.Column(db.String, default="", nullable=True)

    # To CREATE an instance of a User
    def __init__(self, id, username, email, description, hobbies, 
            # isPremuim
            image_url
            ):
        self.id = id
        self.username = username
        self.email = email
        self.description = description
        self.hobbies = hobbies
        self.image_url = image_url
        # self.isPremuim = isPremuim

    def __repr__(self):
        # return f'User({self.id}, {self.username}, {self.description}, {self.hobbies}, {self.isPremuim})'
        return f'User({self.id}, {self.username}, {self.description}, {self.hobbies}, {self.image_url})'
    # To DELETE a row from the table
    def delete(self):
        db.session.delete(self)
        db.session.commit()
    
    # To SAVE a row from the table
    def save(self):
        db.session.add(self)
        db.session.commit()

    def toJSON(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'description': self.description,
            'hobbies': self.hobbies,
            # 'isPremuim': self.isPremuim
            'image_url': self.image_url
        }

class ViajuntosAuth(db.Model):
    __tablename__ = 'vajuntos_auth'

    # User id
    id = db.Column(UUID(as_uuid=True), db.ForeignKey(User.id), primary_key=True, default=uuid.uuid4())
    # Salt
    salt = db.Column(db.String, nullable=False)
    # Hashed and salted password
    pw = db.Column(db.String, nullable=False)

    # To CREATE an instance of a ViajuntosUser
    def __init__(self, id, salt, pw):
        self.id = id
        self.salt = salt
        self.pw = pw

    def __repr__(self):
        return f'User({self.id}, {self.salt}, {self.pw})'

    # To DELETE a row from the table
    def delete(self):
        db.session.delete(self)
        db.session.commit()
    
    # To SAVE a row from the table
    def save(self):
        db.session.add(self)
        db.session.commit()

class EmailVerificationPendant(db.Model):
    __tablename__ = 'email_verification'

    email = db.Column(db.String, primary_key=True, nullable=False)
    code = db.Column(db.String, nullable=False)
    expires_at = db.Column(db.DateTime)

    def __init__(self, email, code, expires_at):
        self.email = email
        self.code = code
        self.expires_at = expires_at

    def __repr__(self):
        return f'User({self.email}, {self.code}, {self.expires_at})'

    # To DELETE a row from the table
    def delete(self):
        db.session.delete(self)
        db.session.commit()
    
    # To SAVE a row from the table
    def save(self):
        db.session.add(self)
        db.session.commit()

class GoogleAuth(db.Model):
    __tablename__ = 'google_auth'

    # User id
    id = db.Column(UUID(as_uuid=True), db.ForeignKey(User.id), primary_key=True, default=uuid.uuid4())
    # Google access token
    access_token = db.Column(db.String, nullable=False)

    # To CREATE an instance of a GoogleUser
    def __init__(self, id, access_token):
        self.id = id
        self.access_token = access_token

    def __repr__(self):
        return f'User({self.id}, {self.access_token})'

    # To DELETE a row from the table
    def delete(self):
        db.session.delete(self)
        db.session.commit()
    
    # To SAVE a row from the table
    def save(self):
        db.session.add(self)
        db.session.commit()

class FacebookAuth(db.Model):
    __tablename__ = 'facebook_auth'

    # User id
    id = db.Column(UUID(as_uuid=True), db.ForeignKey(User.id), primary_key=True, default=uuid.uuid4())
    # facebook access token
    access_token = db.Column(db.String, nullable=False)

    # To CREATE an instance of a facebookUser
    def __init__(self, id, access_token):
        self.id = id
        self.access_token = access_token

    def __repr__(self):
        return f'User({self.id}, {self.access_token})'

    # To DELETE a row from the table
    def delete(self):
        db.session.delete(self)
        db.session.commit()
    
    # To SAVE a row from the table
    def save(self):
        db.session.add(self)
        db.session.commit()

class GithubAuth(db.Model):
    __tablename__ = 'github_auth'

    # User id
    id = db.Column(UUID(as_uuid=True), db.ForeignKey(User.id), primary_key=True, default=uuid.uuid4())
    # Github access token
    access_token = db.Column(db.String, nullable=False)

    # To CREATE an instance of a GithubUser
    def __init__(self, id, access_token):
        self.id = id
        self.access_token = access_token

    def __repr__(self):
        return f'User({self.id}, {self.access_token})'

    # To DELETE a row from the table
    def delete(self):
        db.session.delete(self)
        db.session.commit()
    
    # To SAVE a row from the table
    def save(self):
        db.session.add(self)
        db.session.commit()

class Achievement(db.Model):
    __tablename__ = 'achievements'

    # Achievement id
    id = db.Column(db.String, primary_key=True)
    # Title
    title = db.Column(db.String, nullable=False)
    # Description
    description = db.Column(db.String, nullable=False)
    # Number of stages to be completed
    stages = db.Column(db.Integer, nullable=False, default=1)

    # To CREATE an instance of a Achievement
    def __init__(self, id, title, description, stages):
        self.id = id
        self.title = title
        self.description = description
        self.stages = stages

    def __repr__(self):
        return f'Achievement({self.id}, {self.title}, {self.description}, {self.stages})'

    # To DELETE a row from the table
    def delete(self):
        db.session.delete(self)
        db.session.commit()
    
    # To SAVE a row from the table
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    @staticmethod
    def getAchievementsOfUserId(id):
        achievement_list = []
        query_result = db.session.query(Achievement, AchievementProgress) \
            .join(AchievementProgress, Achievement.id == AchievementProgress.achievement) \
            .filter(AchievementProgress.user == id) \
            .all()
        for achievement, progress in query_result:
            achievement_item = {
                'id': achievement.id,
                'title': achievement.title,
                'description': achievement.description,
                'stages': achievement.stages,
                'progress': progress.progress,
            }
            if progress.progress == achievement.stages:
                achievement_item['completed_at'] = progress.completed_at
            achievement_list.append(achievement_item)
            # achievement_list.append(achievement_item)
            # achievement_list.append(achievement_item)
            # achievement_list.append(achievement_item)
            # achievement_list.append(achievement_item)
            # achievement_list.append(achievement_item)
            # achievement_list.append(achievement_item)
            # achievement_list.append(achievement_item)
        return achievement_list

class AchievementProgress(db.Model):
    __tablename__ = 'achievement_progress'

    # User id
    user = db.Column(UUID(as_uuid=True), db.ForeignKey(User.id), primary_key=True, default=uuid.uuid4())
    # Achievement id
    achievement = db.Column(db.String, db.ForeignKey(Achievement.id), primary_key=True)
    # Progreso
    progress = db.Column(db.Integer, nullable=False, default=0)
    # Fecha completado
    completed_at = db.Column(db.DateTime)

    def __init__(self, user, achievement, progress, completed_at):
        self.user = user
        self.achievement = achievement
        self.progress = progress
        self.completed_at = completed_at

    def __repr__(self):
        return f'Achievement({self.id}, {self.achievement}, {self.progress}, {self.completed_at})'

    # To DELETE a row from the table
    def delete(self):
        db.session.delete(self)
        db.session.commit()
    
    # To SAVE a row from the table
    def save(self):
        db.session.add(self)
        db.session.commit()

class premium_expiration(db.Model):
    __tablename__ = 'premium_expiration'

    # User id
    user = db.Column(UUID(as_uuid=True), db.ForeignKey(User.id), primary_key=True, default=uuid.uuid4())
    # Fecha de vencimiento
    expiration_at  = db.Column(db.DateTime)

    def __init__(self, user, expiration_at):
        self.user = user
        self.expiration_at = expiration_at

    def __repr__(self):
        return f'Achievement({self.id}, {self.expiration_at})'

    # To DELETE a row from the table
    def delete(self):
        db.session.delete(self)
        db.session.commit()
    
    # To SAVE a row from the table
    def save(self):
        db.session.add(self)
        db.session.commit()

class Friend(db.Model):
    __tablename__ = 'friends'
    __table_args__ = (
        db.CheckConstraint('invitee <> invited'),
    )

    # Invitee id
    invitee = db.Column(UUID(as_uuid=True), db.ForeignKey(User.id), primary_key=True, default=uuid.uuid4())
    # Invited id
    invited = db.Column(UUID(as_uuid=True), db.ForeignKey(User.id), primary_key=True, default=uuid.uuid4())

    id_chat = db.Column(UUID(as_uuid=True), db.ForeignKey(Chat.id), default=uuid.uuid4())

    def __init__(self, invitee, invited, id_chat):
        self.invitee = invitee
        self.invited = invited
        self.id_chat = id_chat

    def __repr__(self):
        return f'Achievement({self.invitee}, {self.invited}, {self.id_chat})'

    # To DELETE a row from the table
    def delete(self):
        db.session.delete(self)
        db.session.commit()
    
    # To SAVE a row from the table
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    @staticmethod
    def getFriendsOfUserId(id):
        return db.session.query(User) \
            .join(Friend, Friend.invitee == User.id) \
            .filter(Friend.invited == id) \
            .union( db.session.query(User) \
                .join(Friend, Friend.invited == User.id) \
                .filter(Friend.invitee == id) \
            ).all()

class FriendInvite(db.Model):
    __tablename__ = 'friend_invites'
    __table_args__ = (
        db.CheckConstraint('invitee <> invited'),
    )

    invitee = db.Column(UUID(as_uuid=True), db.ForeignKey(User.id), primary_key=True, default=uuid.uuid4())
    invited = db.Column(UUID(as_uuid=True), db.ForeignKey(User.id), primary_key=True, default=uuid.uuid4())
    expires_at = db.Column(db.DateTime, nullable=False)
    accepted = db.Column(db.Boolean, nullable=True)

    def __init__(self, invitee, invited, expires_at):
        self.invitee = invitee
        self.invited = invited
        self.expires_at = expires_at

    def __repr__(self):
        return f'FriendInvite({self.invitee},{self.invited}, {self.expires_at}, {self.accepted})'

    # To DELETE a row from the table
    def delete(self):
        db.session.delete(self)
        db.session.commit()
    
    # To SAVE a row from the table
    def save(self):
        db.session.add(self)
        db.session.commit()

    def toJSON(self):
        return {
            'invitee': self.invitee,
            'invited': self.invited,
            'expires_at': self.expires_at,
            'accepted': self.accepted
        }

class lang(enum.Enum):
    catalan = "catalan"
    spanish = "spanish"
    english = "english"

class UserLanguage(db.Model):
    __tablename__ = 'user_lang'

    user = db.Column(UUID(as_uuid=True), db.ForeignKey(User.id), primary_key=True, default=uuid.uuid4())
    language = db.Column(db.Enum(lang), primary_key=True)

    def __init__(self, user, language):
        self.user = user
        self.language = language

    def __repr__(self):
        return f'UserLanguage({self.user}, {self.language})'

    # To DELETE a row from the table
    def delete(self):
        db.session.delete(self)
        db.session.commit()
    
    # To SAVE a row from the table
    def save(self):
        db.session.add(self)
        db.session.commit()

class BannedUsers(db.Model):
    __tablename__ = 'banned_users'
    
    email = db.Column(db.String, nullable=False, primary_key=True)
    id_user = db.Column(UUID(as_uuid=True), db.ForeignKey(User.id), default=uuid.uuid4())
    username = db.Column(db.String, nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    reason = db.Column(db.String)
    #admin who banned the user
    id_admin = db.Column(UUID(as_uuid=True), db.ForeignKey(User.id), nullable=False)

    def __init__(self, id_user, email, username, date, reason,id_admin):
        self.id_user = id_user
        self.email = email
        self.username = username
        self.date = date
        self.reason = reason
        self.id_admin = id_admin
    
    def __repr__(self):
        return f'BannedUsers({self.id_user}, {self.email}, {self.username}, {self.date}, {self.reason}, {self.id_admin})'
    
    # To DELETE a row from the table
    def delete(self):
        db.session.delete(self)
        db.session.commit()
    
    # To SAVE a row from the table
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    @staticmethod
    def exists_user(id_user):
        return BannedUsers.query.filter_by(id_user = id_user).first() != None
    @staticmethod
    def exists_email(email):
        return BannedUsers.query.filter_by(email = email).first() != None
    def toJSON(self):
        return {
            'id_user': self.id_user,
            'email': self.email,
            'username': self.username,
            'date': self.date,
            'reason': self.reason,
            'id_admin': self.id_admin
        }