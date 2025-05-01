# Secure E-Voting System

A comprehensive web-based electronic voting platform designed to facilitate secure, transparent, and accessible elections. This system allows administrators to create and manage elections while providing voters with a simple interface to cast their votes from anywhere.

## Features

- **User Authentication**: Secure login and registration system
- **Role-based Access Control**: Separate interfaces for voters and administrators
- **Election Management**: Create, edit, and manage election cycles
- **Candidate Management**: Add and manage candidate profiles with images
- **Real-time Results**: View election results with visual charts
- **Voter Management**: Administrators can manage voter accounts
- **Password Reset**: Admin can reset voter passwords

## Technology Stack

- **Backend**: Python with Flask
- **Database**: MongoDB
- **Frontend**: HTML, CSS, JavaScript, Bootstrap 5
- **Authentication**: Flask-Login
- **Data Visualization**: Chart.js

## Installation

1. Clone the repository
   ```
   git clone https://github.com/mlky7/E-Voting.git
   ```

2. Install dependencies
   ```
   pip install -r requirements.txt
   ```

3. Set up MongoDB and update the connection string in `.env` or `config.py`

4. Run the application
   ```
   python app.py
   ```

5. Initialize admin user (if running for the first time)
   ```
   python init_admin.py
   ```

## Admin Credentials

To access the admin dashboard, use the following credentials:

- **Username**: admin
- **Email**: admin@email.com
- **Password**: 1234


## Screenshots

![Voter Management](screenshots/screenshot-(1).png)
![Edit Candidate](screenshots/screenshot-(2).png)
![Vote for Candidate](screenshots/screenshot-(3).png)
![Election Results](screenshots/screenshot-(4).png)
