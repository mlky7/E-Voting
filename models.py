from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from bson.objectid import ObjectId

class User(UserMixin):
    def __init__(self, username, email, password_hash=None, role='voter', voted_elections=None, _id=None, 
                 temp_password_flag=False, **kwargs):
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self._role = role
        self.voted_elections = voted_elections or []
        self._id = _id if isinstance(_id, ObjectId) else ObjectId(_id) if _id else None
        self.temp_password_flag = temp_password_flag
        
        for key, value in kwargs.items():
            setattr(self, key, value)

    @classmethod
    def from_dict(cls, data):
        """Create a User instance from a dictionary (e.g., from MongoDB)"""
        return cls(
            username=data['username'],
            email=data['email'],
            password_hash=data['password_hash'],
            role=data.get('role', 'voter'),
            voted_elections=data.get('voted_elections', []),
            _id=data['_id'],
            temp_password_flag=data.get('temp_password_flag', False),
            full_name=data.get('full_name'),
            address=data.get('address'),
            phone=data.get('phone'),
            date_of_birth=data.get('date_of_birth'),
            voter_id=data.get('voter_id')
        )

    @property
    def role(self):
        return self._role

    @role.setter
    def role(self, value):
        self._role = value

    def get_id(self):
        return str(self._id)

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        self._id = value if isinstance(value, ObjectId) else ObjectId(value) if value else None

    def is_admin(self):
        return self._role == 'admin'

    @staticmethod
    def check_password(password_hash, password):
        return check_password_hash(password_hash, password)

class Election:
    def __init__(self, title, description, start_date, end_date, candidates, created_by):
        self.title = title
        self.description = description
        self.start_date = start_date
        self.end_date = end_date
        self.candidates = candidates
        self.created_by = created_by
        self.votes = {}
        self.status = 'active'
        self.created_at = datetime.now()

class Candidate:
    def __init__(self, name, party, description, image_url=None, qualifications=None, campaign_promises=None):
        self.name = name
        self.party = party
        self.description = description
        self.image_url = image_url
        self.qualifications = qualifications or []
        self.campaign_promises = campaign_promises or []
        self.created_at = datetime.now()



