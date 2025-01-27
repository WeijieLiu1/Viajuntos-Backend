# Import the database object (db) from the main application module
# We will define this inside /app/__init__.py in the next sections.
from enum import Enum
from sqlalchemy import ForeignKey, Integer
from app import db
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from app.module_users.models import User

class EventType(Enum):
    PUBLIC = 0
    FRIENDS = 1
    PRIVATE = 2

# Define an Event model

class Event(db.Model):

    __tablename__ = 'events'

    # Event id
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4())
    # Event name
    name = db.Column(db.String, nullable=False)
    event_type = db.Column(db.Enum(EventType), nullable=True, default=EventType.PUBLIC)
    # Event description
    description = db.Column(db.String, nullable=False)
    # Start date of the event
    date_started = db.Column(db.DateTime, nullable=False)
    # End date of the event
    date_end = db.Column(db.DateTime, nullable=False)
    # Date of creation of the event
    date_creation = db.Column(
        db.DateTime, nullable=False, default=datetime.now())
    # Creator of the event (with FK)
    user_creator = db.Column(
        UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=False)
    # Longitude of the location where the event will take taking place
    longitud = db.Column(db.Float, nullable=False)
    # Latitude of the location where the event will take taking place
    latitude = db.Column(db.Float, nullable=False)
    # Number of max participants of the event
    max_participants = db.Column(db.Integer, nullable=False)
    
    # Chat of the event
    chat_id = db.Column(
        UUID(as_uuid=True), db.ForeignKey('chat.id'), nullable=False)
    
    # Event is free or not
    is_event_free = db.Column(db.Boolean, default=True, nullable=True)
    # Amount of the event
    amount_event = db.Column(db.Float, default = 0, nullable=False)

    # Relationship with Participant
    participants_in_event = db.relationship(
        'Participant', backref='participants', lazy=True)
    

    # To CREATE an instance of an Event
    def __init__(self, id, name, event_type, description, date_started, date_end, user_creator, longitud, latitude, max_participants,is_event_free,amount_event,chat_id):
        self.id = id
        self.name = name
        self.event_type = event_type
        self.description = description
        self.date_started = date_started
        self.date_end = date_end
        self.user_creator = user_creator
        self.longitud = longitud
        self.latitude = latitude
        self.max_participants = max_participants
        self.is_event_free = is_event_free
        self.amount_event = amount_event
        self.chat_id = chat_id

    # To FORMAT an Event in a readable string format

    def __repr__(self):
        return '''Event(id: ' + str(self.id) + ', name: ' + str(self.name)+ ', event_type: ' + str(self.event_type) + ', description: ' + str(self.description) +
                ', date_started: ' + str(self.date_started) + ', date_end: ' + str(self.date_end) +
                ', date_creation: ' + str(self.date_creation) + ', user_creator: ' + str(self.user_creator) + 
                ', longitud: ' + str(self.longitud) + ', latitude: ' + str(self.latitude) + 
                ', max_participants: ' + str(self.max_participants) + ', event_image_uri: ' + str(self.event_image_uri) + ', is_event_free: ' + str(self.is_event_free) + ', amount_event: ' + str(self.amount_event) +', chat_id: ' + str(self.chat_id)').'''

    # To DELETE a row from the table
    def delete(self):
        db.session.delete(self)
        db.session.commit()

    # To SAVE a row from the table
    def save(self):
        db.session.add(self)
        db.session.commit()

    @staticmethod
    # To GET ALL ROWS
    def get_all():
        return Event.query.all()
        
    # To CONVERT an Event object to a dictionary
    def toJSON(self):
        return {
            "id": self.id,
            "name": self.name,
            "event_type": self.event_type.name,
            "description": self.description,
            "date_started": self.date_started,
            "date_end": self.date_end,
            "date_creation": self.date_creation,
            "user_creator": self.user_creator,
            "longitud": self.longitud,
            "latitude": self.latitude,
            "max_participants": self.max_participants,
            "event_image_uris": [event_image.event_image_uri for event_image in EventImages.query.filter_by(event_id=self.id).all()],
            "is_event_free": self.is_event_free,
            "amount_event": self.amount_event,
            "chat_id": self.chat_id
        }
# defining the event images table
class EventImages(db.Model):
    __tablename__ = 'event_images'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4())
    # Event id
    event_id = db.Column(UUID(as_uuid=True), db.ForeignKey(
        'events.id'),default=uuid.uuid4())
    # Image of event (can be null)
    event_image_uri = db.Column(db.String, default="", nullable=True)

    def __init__(self, id, event_id, event_image_uri):
        self.id = id
        self.event_id = event_id
        self.event_image_uri = event_image_uri

    # To FORMAT a EventImages in a readable string format
    def __repr__(self):
        return 'EventImages(id: ' + str(self.id) + ', event_id: ' + str(self.event_id)+ ', event_image_uri: ' + str(self.event_image_uri) +  ').'

    # To DELETE a row from the table
    def delete(self):
        db.session.delete(self)
        db.session.commit()

    # To SAVE a row from the table
    def save(self):
        db.session.add(self)
        db.session.commit()

    @staticmethod
    # To GET ALL ROWS of the table
    def get_all():
        return PostImages.query.all()

    # To CONVERT a PostImages object to a dictionary
    def toJSON(self):
        return {
            "id": self.id,
            "event_id": self.event_id,
            "event_image_uri": self.event_image_uri,
        }

# Define the like class model
class Like(db.Model):

    __tablename__ = 'likes'

    # Event id
    event_id = db.Column(UUID(as_uuid=True), db.ForeignKey(
        'events.id'), primary_key=True)
    # User id
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey(
        'users.id'), primary_key=True)

    # To create an instance of Like

    def __init__(self, user_id, event_id):

        self.user_id = user_id
        self.event_id = event_id

    # To FORMAT an Like in a readable string format
    def __repr__(self):
        return 'Like(user_id: ' + str(self.user_id) + ', event_id: ' + str(self.event_id) + ').'

    # To DELETE a row from the table
    def delete(self):
        db.session.delete(self)
        db.session.commit()

    # To SAVE a row from the table
    def save(self):
        db.session.add(self)
        db.session.commit()

    # To GET ALL ROWS of the table
    def get_all():
        return Like.query.all()

    # To CONVERT an Eent objecto to a dictionary
    def toJSON(self):
        return{
            "user_id": self.user_id,
            "event_id": self.event_id
        }

# Define a Participant model
class Participant(db.Model):

    __tablename__ = 'participant'

    # Event id
    event_id = db.Column(UUID(as_uuid=True), db.ForeignKey(
        'events.id'), primary_key=True)
    # User id
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey(
        'users.id'), primary_key=True)
    # Verification code
    verification_code = db.Column(db.String, nullable=False)
    

    time_verified = db.Column(db.DateTime, nullable=True)

    # To CREATE an instance of a Participant
    def __init__(self, event_id, user_id, verification_code):
        self.event_id = event_id
        self.user_id = user_id
        self.verification_code = verification_code
        self.time_verified = None

    # To FORMAT a Participant in a readable string format
    def __repr__(self):
        return 'Participant(event_id: ' + str(self.event_id) + ', user_id: ' + str(self.user_id) + ', verification_code: ' + str(self.verification_code)  +', time_verified: ' + str(self.time_verified) + ').'

    # To DELETE a row from the table
    def delete(self):
        db.session.delete(self)
        db.session.commit()

    # To SAVE a row from the table
    def save(self):
        db.session.add(self)
        db.session.commit()

    @staticmethod
    # To GET ALL ROWS of the table
    def get_all():
        return Participant.query.all()

    # To CONVERT a Participant object to a dictionary
    def toJSON(self):
        return {
            "event_id": self.event_id,
            "user_id": self.user_id,
            "verification_code": self.verification_code,
            "time_verified": self.time_verified
        }



# Define a Review model
class Review(db.Model):

    __tablename__ = 'review'

    # Event id
    event_id = db.Column(UUID(as_uuid=True), db.ForeignKey(
        'events.id'), primary_key=True)
    # User id
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey(
        'users.id'), primary_key=True)
    # Rating of the review
    rating = db.Column(db.Integer, nullable=False)
    # Comment de una review
    comment = db.Column(db.String, nullable=False)
    datetime = db.Column(db.DateTime, nullable=True, default=datetime.now())

    # To CREATE an instance of a Review

    def __init__(self, event_id, user_id, rating, comment):
        self.event_id = event_id
        self.user_id = user_id
        self.rating = rating
        self.comment = comment

    # To FORMAT a Review in a readable string format
    def __repr__(self):
        return 'Review(event_id: ' + str(self.event_id) + ', user_id: ' + str(self.user_id) + ', rating: ' + str(self.rating) + ', comment: ' + str(self.comment)+ ', datetime: ' + str(self.datetime) + ').'

    # To DELETE a row from the table
    def delete(self):
        db.session.delete(self)
        db.session.commit()

    # To SAVE a row from the table
    def save(self):
        db.session.add(self)
        db.session.commit()

    @staticmethod
    # To GET ALL ROWS of the table
    def get_all():
        return Review.query.all()

    # To CONVERT a Review object to a dictionary
    def toJSON(self):
        return {
            "event_id": self.event_id,
            "user_id": self.user_id,
            "rating": self.rating,
            "comment": self.comment,
            "datetime": self.datetime
        }

class FeeType(Enum):
    SPLIT_COST = 1
    FIXED_ENTRANCE_FEE = 2

class PaymentStatus(Enum):
    NOT_PAID = 0
    PAID = 1

# Define a Payment model
class Payment(db.Model):
    __tablename__ = 'payments'
    # id of payment
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4())
    # id of event
    event_id = db.Column(UUID(as_uuid=True), db.ForeignKey('events.id'), nullable=False)
    # id of user
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=False)
    # type of payment
    payment_type = db.Column(db.String, nullable=False)
    # id of payment
    payment_id = db.Column(db.String, nullable=False)
    # amount of payment
    amount = db.Column(db.Float, nullable=False)
    # status of payment
    status = db.Column(db.Enum(PaymentStatus), nullable=False, default=PaymentStatus.NOT_PAID)

    event = db.relationship('Event', backref='payments', lazy=True)
    user = db.relationship('User', backref='payments', lazy=True)

    def __init__(self, event_id, user_id, payment_type, payment_id, amount,status):
        self.event_id = event_id
        self.user_id = user_id
        self.payment_type = payment_type
        self.payment_id = payment_id
        self.amount = amount
        self.status = status

    # To FORMAT a Review in a readable string format
    def __repr__(self):
        return 'Payment(id: ' + str(self.id) + ', event_id: ' + str(self.event_id) + ', user_id: ' + str(self.user_id) + ', payment_type: ' + str(self.payment_type) +', payment_id: ' + str(self.payment_id) + ', amount: ' + str(self.amount)+ ', status: ' + str(self.status)+').'


    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def save(self):
        db.session.add(self)
        db.session.commit()

    @staticmethod
    def get_all():
        return Payment.query.all()

    def toJSON(self):
        return {
            "id": self.id,
            "event_id": self.event_id,
            "user_id": self.user_id,
            "payment_type": self.payment_type,
            "payment_id": self.payment_id,
            "amount": self.amount,
            "status": self.status.name,
        }

    # Check if the user_id and event_id exist in Participant model before saving the payment
    @classmethod
    def exists_in_participant(cls, event_id, user_id):
        return Participant.query.filter_by(event_id=event_id, user_id=user_id).first() is not None
    # Check if the user_id and event_id exist in Participant model before saving the payment
    @classmethod
    def is_free_event(cls, event_id):
        return Event.query.filter_by(event_id=event_id).first() is not None

    def save_with_check(self):
        if self.exists_in_participant(self.event_id, self.user_id):
            if self.is_free_event(self.event_id):
                self.save()
            return True
        else:
            return False
        
# Define a Event's Post model
class EventPosts(db.Model):

    __tablename__ = 'event_posts'

    # id of post
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    # id of parent post
    parent_post_id = db.Column(db.Integer, db.ForeignKey('event_posts.id'))
    # Event id
    event_id = db.Column(UUID(as_uuid=True), db.ForeignKey(
        'events.id'))
    # User id
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey(
        'users.id'))
    # Date of creation of the post
    datetime = db.Column(db.DateTime, nullable=False, default=datetime.now())

    # text de una Event's Post
    text = db.Column(db.String, nullable=False)
    
    # To CREATE an instance of a EventPosts

    def __init__(self, parent_post_id, event_id,user_id, text):
        self.parent_post_id = parent_post_id
        self.event_id = event_id
        self.user_id = user_id
        self.text = text

    # To FORMAT a EventPosts in a readable string format
    def __repr__(self):
        return 'EventPosts(parent_post_id: ' + str(self.parent_post_id) + ', event_id: ' + str(self.event_id) + ', user_id: ' + str(self.user_id) + ', text: ' + str(self.text)  +', likes: ' + str(LikePost.query.filter_by(post_id=self.id).count()) + ').'

    # To DELETE a row from the table
    def delete(self):
        db.session.delete(self)
        db.session.commit()

    # To SAVE a row from the table
    def save(self):
        db.session.add(self)
        db.session.commit()

    @staticmethod
    # To GET ALL ROWS of the table
    def get_all():
        return EventPosts.query.all()

    # To CONVERT a EventPosts object to a dictionary
    def toJSON(self):
        return {
            "id": self.id,
            "parent_post_id": self.parent_post_id,
            "event_id": self.event_id,
            "user_id": self.user_id,
            "datetime": self.datetime,
            "text": self.text,
            "likes": LikePost.query.filter_by(post_id=self.id).count(),
            "post_image_uris": [post_image.post_image_uri for post_image in PostImages.query.filter_by(post_id=self.id).all()]
        }
# defining the post images table
class PostImages(db.Model):
    __tablename__ = 'post_images'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    # Event id
    post_id = db.Column(db.Integer, db.ForeignKey(
        'event_posts.id'))
    # Image of event (can be null)
    post_image_uri = db.Column(db.String, default="", nullable=True)

    def __init__(self, post_id, post_image_uri):
        self.post_id = post_id
        self.post_image_uri = post_image_uri

    # To FORMAT a PostImages in a readable string format
    def __repr__(self):
        return 'PostImages(id: ' + str(self.id) + ', post_id: ' + str(self.post_id)+ ', post_image_uri: ' + str(self.post_image_uri) +  ').'

    # To DELETE a row from the table
    def delete(self):
        db.session.delete(self)
        db.session.commit()

    # To SAVE a row from the table
    def save(self):
        db.session.add(self)
        db.session.commit()

    @staticmethod
    # To GET ALL ROWS of the table
    def get_all():
        return PostImages.query.all()

    # To CONVERT a PostImages object to a dictionary
    def toJSON(self):
        return {
            "id": self.id,
            "post_id": self.post_id,
            "post_image_uri": self.post_image_uri,
        }


# Define the like class model
class LikePost(db.Model):

    __tablename__ = 'likes_post'

    # Event id
    post_id = db.Column(db.Integer, db.ForeignKey(
        'event_posts.id'), primary_key=True)
    # User id
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey(
        'users.id'), primary_key=True)

    # To create an instance of Like

    def __init__(self, user_id, post_id):

        self.user_id = user_id
        self.post_id = post_id

    # To FORMAT an Like in a readable string format
    def __repr__(self):
        return 'LikePost(user_id: ' + str(self.user_id) + ', post_id: ' + str(self.post_id) + ').'

    # To DELETE a row from the table
    def delete(self):
        db.session.delete(self)
        db.session.commit()

    # To SAVE a row from the table
    def save(self):
        db.session.add(self)
        db.session.commit()

    # To GET ALL ROWS of the table
    def get_all():
        return Like.query.all()

    # To CONVERT an Eent objecto to a dictionary
    def toJSON(self):
        return{
            "user_id": self.user_id,
            "post_id": self.post_id
        }
# class BannedEvents(db.Model):
#     __tablename__ = 'banned_events'

#     event_id = db.Column(UUID(as_uuid=True), db.ForeignKey('events.id'), primary_key=True)
#     date = db.Column(db.DateTime, nullable=False)
#     reason = db.Column(db.String)

#     def __init__(self, event_id, date, reason):
#         self.event_id = event_id
#         self.date = date
#         self.reason = reason
    
#     def __repr__(self):
#         return f'BannedEmail({self.event_id}, {self.date}, {self.reason})'
    
#     # To DELETE a row from the table
#     def delete(self):
#         db.session.delete(self)
#         db.session.commit()
    
#     # To SAVE a row from the table
#     def save(self):
#         db.session.add(self)
#         db.session.commit()
    
#     def toJSON(self):
#         return {
#             'event_id': self.event_id,
#             'date': self.date,
#             'reason': self.reason
#         }
# # Define Event Fee model
# class EventFee(db.Model):

#     __tablename__ = 'event_fee'

#     # id of event
#     event_id = db.Column(UUID(as_uuid=True), db.ForeignKey('events.id'), nullable=False)

#     # type of fee
#     fee_type = db.Column(db.Enum(FeeType), nullable=False, default=FeeType.SPLIT_COST)

#     # price of fee
#     # if fee_type == SPLIT_COST, price is the total price
#     # if fee_type == FIXED_ENTRANCE_FEE, price is the price per person
#     entrance_fee = db.Column(db.Float, nullable=True)  
    

#     # To CREATE an instance of a PaidEvent

#     def __init__(self, event_id, user_id, price, date):
#         self.event_id = event_id
#         self.user_id = user_id
#         self.price = price
#         self.date = date

#     # To FORMAT a PaidEvent in a readable string format
#     def __repr__(self):
#         return 'PaidEvent(event_id: ' + str(self.event_id) + ', user_id: ' + str(self.user_id) + ', price: ' + str(self.price) + ', date: ' + str(self.date) + ').'

#     # To DELETE a row from the table
#     def delete(self):
#         db.session.delete(self)
#         db.session.commit()

#     # To SAVE a row from the table
#     def save(self):
#         db.session.add(self)
#         db.session.commit()

#     @staticmethod
#     # To GET ALL ROWS of the table
#     def get_all():
#         return EventFee.query.all()

#     # To CONVERT a PaidEvent object to a dictionary
#     def toJSON(self):
#         return {
#             "event_id": self.event_id,
#             "user_id": self.user_id,
#             "price": self.price,
#             "date": self.date
#         }
    
class BannedEvents(db.Model):
    __tablename__ = 'banned_events'

    event_id = db.Column(UUID(as_uuid=True), db.ForeignKey('events.id'), primary_key=True)
    date = db.Column(db.DateTime, nullable=False)
    reason = db.Column(db.String)
    #admin who banned the user
    id_admin = db.Column(UUID(as_uuid=True), db.ForeignKey(User.id), nullable=False)

    def __init__(self, event_id, date, reason,id_admin):
        self.event_id = event_id
        self.date = date
        self.reason = reason
        self.id_admin = id_admin
    
    def __repr__(self):
        return f'BannedEvents({self.event_id}, {self.date}, {self.reason},{self.id_admin})'
    
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
            'event_id': self.event_id,
            'date': self.date,
            'reason': self.reason,
            'id_admin': self.id_admin
        }