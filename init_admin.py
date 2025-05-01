from pymongo import MongoClient
from werkzeug.security import generate_password_hash
from datetime import datetime
from config import Config

def create_admin():
    client = MongoClient(Config.MONGO_URI)
    db = client.evoting
    if db.users.find_one({'email': 'admin@email.com'}):
        print("Admin already exists")
        return

    admin_user = {
        'username': 'admin',
        'email': 'admin@email.com',
        'password_hash': generate_password_hash('1234'),
        'full_name': 'Admin User',
        'role': 'admin',
        'voted_elections': [],
        'registration_date': datetime.now()
    }

    db.users.insert_one(admin_user)
    print("Admin user created successfully")

if __name__ == "__main__":
    create_admin()
