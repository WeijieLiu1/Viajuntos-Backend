# Librerias
from datetime import datetime, timedelta
#from dotenv import load_dotenv, find_dotenv
from sqlalchemy.dialects.postgresql import UUID
from app import db

# Settings
# app.config['SQLALCHEMY_DATABASE_URI'] = environ.get('DATABASE')
# app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

#Define the chat model
class Chat(db.Model):
    '''
    Table Chat
    '''

    __tablename__ = 'chat'

    #id del Chat
    id = db.Column(UUID(as_uuid = True), primary_key = True)
    
    #type of chat private or group
    type = db.Column(db.String, nullable=False)

    #nombre del chat
    name = db.Column(db.String, nullable=False)

    #id del usuari al que pertany
    creator_id = db.Column(UUID(as_uuid=True) , db.ForeignKey('users.id'), nullable=True) 

    #time when the chat was created
    created_at = db.Column(db.DateTime, nullable=False, default =  datetime.now() + timedelta(hours=2))

    #To create a instance of a Chat
    def __init__(self, id, name, type, creator_id):
        self.id = id
        self.name = name
        self.type = type
        self.creator_id = creator_id

    def __repr__(self):
        return f'Chat(id: {self.id}, type: {self.type}, name: {self.name}, type: {self.creator_id}, created_at: {self.created_at})'

    #To delete a row from the table
    def delete(self):
        db.session.delete(self)
        db.session.commit()

    # To save a row from the table
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    #To convert a Chat object in a dictionary
    def toJSON(self):
        return{
            "id": self.id,
            "type": self.type,
            "name": self.name,
            "creator_id": self.creator_id,
            "created_at": self.created_at
        }
#Defueine the members model
class Members(db.Model):
    '''
    Table Members
    '''

    __tablename__ = 'members'

    #id del usuari al que pertany
    user_id = db.Column(UUID(as_uuid=True) , db.ForeignKey('users.id') , primary_key=True)  

    #id del chat al que pertany
    chat_id = db.Column(UUID(as_uuid=True) , db.ForeignKey('chat.id') , primary_key=True)

    #time when the member joined the chat
    joined_at = db.Column(db.DateTime, nullable=False, default =  datetime.now() + timedelta(hours=2))

    #To create a instance of a Members
    def __init__(self, id, chat_id):
        self.user_id = id
        self.chat_id = chat_id

    def __repr__(self):
        return f'Members(user_id: {self.user_id}, chat_id: {self.chat_id}, joined_at: {self.joined_at})'

    #To delete a row from the table 
    def delete(self):
        db.session.delete(self)
        db.session.commit()

    # To save a row from the table
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    #To convert a Members object in a dictionary
    def toJSON(self):
        return{
            "id": self.user_id,
            "chat_id": self.chat_id,
            "joined_at": self.joined_at,
        }
    
#Define the message model
class Message(db.Model):
    '''
    Table message
    '''
    __tablename__ = 'message'

    #id del missatge
    id = db.Column(UUID(as_uuid = True), primary_key=True)

    #id del usuari que ho envia
    sender_id = db.Column(UUID(as_uuid=True) , db.ForeignKey('users.id') , nullable = False)   

    #id del chat al que pertany
    chat_id = db.Column(UUID(as_uuid=True) , db.ForeignKey('chat.id') , nullable=False)

    #contingut del missatge
    text = db.Column(db.Text)

    #date when the missage was sent
    created_at = db.Column(db.DateTime, nullable=False, default =  datetime.now() + timedelta(hours=2))

    # To create a instance of Message
    def __init__(self, id, sender_id, chat_id, text):
        self.id = id
        self.sender_id = sender_id
        self.chat_id = chat_id
        self.text = text

    def __repr__(self):
        return '''Message(id: ' + str(self.id) + ' , sender_id: ' + str(self.sender_id) + ' , chat_id: ' + str(self.chat_id) + 
                ' , text: ' + Text(self.text) + ' , created_at: ' + str(self.created_at) ').'''

    # To delete a row from the table
    def delete(self):
        db.session.delete(self)
        db.session.commit()

    # To save a row from the table
    def save(self):
        db.session.add(self)
        db.session.commit()

    # To convert a Message object in a dictionary
    def toJSON(self):
        return{
            "id": self.id,
            "sender_id": self.sender_id,
            "chat_id": self.chat_id,
            "text": self.text,
            "created_at": self.created_at
        }
