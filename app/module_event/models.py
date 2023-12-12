# Import the database object (db) from the main application module
# We will define this inside /app/__init__.py in the next sections.
from enum import Enum
from sqlalchemy import ForeignKey, Integer
from app import db
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

# Define an Event model


class Event(db.Model):

    __tablename__ = 'events'

    # Event id
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4())
    # Event name
    name = db.Column(db.String, nullable=False)
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
    # Image of event (can be null)
    event_image_uri = db.Column(db.String, default="", nullable=True)
    
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
    def __init__(self, id, name, description, date_started, date_end, user_creator, longitud, latitude, max_participants, event_image_uri,is_event_free,amount_event,chat_id):
        self.id = id
        self.name = name
        self.description = description
        self.date_started = date_started
        self.date_end = date_end
        self.user_creator = user_creator
        self.longitud = longitud
        self.latitude = latitude
        self.max_participants = max_participants
        self.event_image_uri = event_image_uri
        self.is_event_free = is_event_free
        self.amount_event = amount_event
        self.chat_id = chat_id

    # To FORMAT an Event in a readable string format

    def __repr__(self):
        return '''Event(id: ' + str(self.id) + ', name: ' + str(self.name) + ', description: ' + str(self.description) +
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
            "description": self.description,
            "date_started": self.date_started,
            "date_end": self.date_end,
            "date_creation": self.date_creation,
            "user_creator": self.user_creator,
            "longitud": self.longitud,
            "latitude": self.latitude,
            "max_participants": self.max_participants,
            "event_image_uri": self.event_image_uri,
            "is_event_free": self.is_event_free,
            "amount_event": self.amount_event,
            "chat_id": self.chat_id
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

    # To CREATE an instance of a Participant

    def __init__(self, event_id, user_id):

        self.event_id = event_id
        self.user_id = user_id

    # To FORMAT a Participant in a readable string format
    def __repr__(self):
        return 'Participant(event_id: ' + str(self.event_id) + ', user_id: ' + str(self.user_id) + ').'

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

    # To CREATE an instance of a Review

    def __init__(self, event_id, user_id, rating, comment):
        self.event_id = event_id
        self.user_id = user_id
        self.rating = rating
        self.comment = comment

    # To FORMAT a Review in a readable string format
    def __repr__(self):
        return 'Review(event_id: ' + str(self.event_id) + ', user_id: ' + str(self.user_id) + ', rating: ' + str(self.rating) + ', comment: ' + str(self.comment) + ').'

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
            "comment": self.comment
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
    # amount of payment
    amount = db.Column(db.Float, nullable=False)
    # status of payment
    status = db.Column(db.Enum(PaymentStatus), nullable=False, default=PaymentStatus.NOT_PAID)

    event = db.relationship('Event', backref='payments', lazy=True)
    user = db.relationship('User', backref='payments', lazy=True)

    def __init__(self, event_id, user_id, payment_type, amount):
        self.event_id = event_id
        self.user_id = user_id
        self.payment_type = payment_type
        self.amount = amount

    # To FORMAT a Review in a readable string format
    def __repr__(self):
        return 'Payment(id: ' + str(self.id) + ', event_id: ' + str(self.event_id) + ', user_id: ' + str(self.user_id) + ', payment_type: ' + str(self.payment_type) + ', amount: ' + str(self.amount)+ ', status: ' + str(self.status)+').'


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
            "amount": self.amount,
            "status": self.status,
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