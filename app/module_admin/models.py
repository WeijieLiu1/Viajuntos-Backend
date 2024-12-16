from app import db
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.module_users.models import User

class Admin(db.Model):
    __tablename__ = 'admin'

    # User id
    id = db.Column(UUID(as_uuid=True), db.ForeignKey(User.id), primary_key=True, default=uuid.uuid4())

    def __init__(self, id):
        self.id = id

    def __repr__(self):
        return f'Admin({self.id})'

    # To DELETE a row from the table
    def delete(self):
        db.session.delete(self)
        db.session.commit()
    
    # To SAVE a row from the table
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    @staticmethod
    def exists(id):
        if type(id) == str:
            id = uuid.UUID(id)
        return Admin.query.filter_by(id = id).first() != None

    def toJSON(self):
        return { 'id': self.id }
    
class ReportedUser(db.Model):
    __tablename__ = 'reported_user'
    __table_args__ = (
        db.CheckConstraint('id_user <> id_user_reported'),
    )

    # User who report, id
    id_user = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), primary_key=True, default=uuid.uuid4())
    # User who has been reported, id
    id_user_reported = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), primary_key=True, default=uuid.uuid4())
    comment = db.Column(db.String(1000), nullable=False)

    def __init__(self, id_user,id_user_reported, comment):
        self.id_user = id_user
        self.id_user_reported = id_user_reported
        self.comment = comment

    def __repr__(self):
        return f'ReportedUser(id_user: {self.id_user},id_user_reported: {self.id_user_reported}, comment: {self.comment})'

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
            'id_user': self.id_user,
            'id_user_reported': self.id_user_reported,
            'comment': self.comment,
            }
    
class ReportedEvent(db.Model):
    __tablename__ = 'reported_event'

    # User id
    id_user = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), primary_key=True, default=uuid.uuid4())
    id_event_reported = db.Column(UUID(as_uuid=True), db.ForeignKey('events.id'), primary_key=True, default=uuid.uuid4())
    comment = db.Column(db.String(1000), nullable=False)

    def __init__(self, id_user, id_event_reported, comment):
        self.id_user = id_user
        self.id_event_reported = id_event_reported
        self.comment = comment

    def __repr__(self):
        return f'ReportedUser(id_user: {self.id_user}, id_event_reported: {self.id_event_reported}, comment: {self.comment})'

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
            'id_user': self.id_user,
            'id_event_reported': self.id_event_reported,
            'comment': self.comment,
            }