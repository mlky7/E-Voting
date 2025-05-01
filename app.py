from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_from_directory
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from pymongo import MongoClient
from datetime import datetime, timedelta
from config import Config
from models import User, Election
import os
import logging
from bson.objectid import ObjectId
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask_session import Session
import random
import string

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(Config)
Session(app)

client = MongoClient(app.config['MONGO_URI'])
db = client.evoting

db.vote_records.create_index([("user_id", 1), ("election_id", 1)], unique=True)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

UPLOAD_FOLDER = os.path.join('static', 'uploads')
DEFAULT_IMAGE_DIR = os.path.join('static', 'images')

for directory in [UPLOAD_FOLDER, DEFAULT_IMAGE_DIR]:
    if not os.path.exists(directory):
        os.makedirs(directory)
        logger.debug(f"Created directory: {os.path.abspath(directory)}")

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@login_manager.user_loader
def load_user(user_id):
    try:
        user_data = db.users.find_one({'_id': ObjectId(user_id)})
        if user_data:
            return User(
                username=user_data['username'],
                email=user_data['email'],
                password_hash=user_data['password_hash'],
                role=user_data.get('role', 'voter'),
                voted_elections=user_data.get('voted_elections', []),
                _id=user_data['_id'],
                temp_password_flag=user_data.get('temp_password_flag', False)
            )
    except Exception as e:
        logger.error(f"Error loading user: {str(e)}")
    return None

@app.route('/')
def index():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            dob = datetime.strptime(request.form['date_of_birth'], '%Y-%m-%d')
            today = datetime.now()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            
            if age < 18:
                flash('You must be at least 18 years old to register')
                return redirect(url_for('register'))
                
            user_data = {
                'username': request.form['username'],
                'email': request.form['email'],
                'password_hash': generate_password_hash(request.form['password']),
                'full_name': request.form['full_name'],
                'address': request.form['address'],
                'phone': request.form['phone'],
                'date_of_birth': dob,
                'voter_id': request.form['voter_id'],
                'role': 'voter',
                'voted_elections': [],
                'registration_date': datetime.now()
            }

            if db.users.find_one({'email': user_data['email']}):
                flash('Email already registered')
                return redirect(url_for('register'))
            result = db.users.insert_one(user_data)

            user = User(
                username=user_data['username'],
                email=user_data['email'],
                password_hash=user_data['password_hash'],
                role='voter',
                voted_elections=[],
                _id=result.inserted_id
            )

            login_user(user)
            flash('Registration successful')
            return redirect(url_for('dashboard'))
        except ValueError:
            flash('Invalid date format')
            return redirect(url_for('register'))

    now = datetime.now()
    age18 = timedelta(days=365*18)
    
    return render_template('register.html', now=now, age18=age18)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        try:
            user_data = db.users.find_one({'email': email})
            
            if user_data and check_password_hash(user_data['password_hash'], password):
                user = User.from_dict(user_data)
                login_user(user)
                
      
                if user_data.get('temp_password_flag', False):
                    if 'temp_password_users' not in session:
                        session['temp_password_users'] = []
                    
                    user_id_str = str(user_data['_id'])
                    if user_id_str not in session['temp_password_users']:
                        session['temp_password_users'] = session.get('temp_password_users', []) + [user_id_str]
                    
                    flash('You are using a temporary password. Please change it now.')
                    return redirect(url_for('change_password'))
                
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid email or password')
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            flash('An error occurred during login')
            
    return render_template('login.html')

def update_election_status():
    now = datetime.now()

    ended_elections = db.elections.find({
        'status': 'active',
        'end_date': {'$lt': now}
    })
    
    for election in ended_elections:
        db.elections.update_one(
            {'_id': election['_id']},
            {'$set': {'status': 'completed'}}
        )
        logger.info(f"Updated election {election['_id']} status to completed")

@app.route('/dashboard')
@login_required
def dashboard():
    update_election_status()
    
    elections = list(db.elections.find())  
    return render_template('dashboard.html', elections=elections)

@app.route('/create_election', methods=['GET', 'POST'])
@login_required
def create_election():
    if current_user.role != 'admin':
        flash('Access denied. Only administrators can create elections.')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        try:
            logger.debug(f"Form data received: {request.form}")
            
            if not request.form.get('title'):
                flash('Election title is required')
                return redirect(url_for('create_election'))

            if not request.form.get('description'):
                flash('Election description is required')
                return redirect(url_for('create_election'))

            if not request.form.get('start_date'):
                flash('Start date is required')
                return redirect(url_for('create_election'))

            if not request.form.get('end_date'):
                flash('End date is required')
                return redirect(url_for('create_election'))

            try:
                start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d')
            except ValueError:
                flash('Invalid start date format')
                return redirect(url_for('create_election'))
                
            try:
                end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d')
            except ValueError:
                flash('Invalid end date format')
                return redirect(url_for('create_election'))

            now = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            if start_date < now:
                flash('Start date cannot be in the past')
                return redirect(url_for('create_election'))

            if end_date <= start_date:
                flash('End date must be after start date')
                return redirect(url_for('create_election'))

            candidate_ids = request.form.getlist('candidates')
            logger.debug(f"Selected candidate IDs: {candidate_ids}")

            if not candidate_ids:
                flash('Please select at least one candidate')
                return redirect(url_for('create_election'))

            candidates_details = []
            for candidate_id in candidate_ids:
                candidate = db.candidates.find_one({'_id': ObjectId(candidate_id)})
                if candidate:
                    candidates_details.append({
                        'id': str(candidate['_id']),
                        'name': candidate['name'],
                        'party': candidate['party'],
                        'position': candidate.get('position', '')
                    })

            election = {
                'title': request.form['title'],
                'description': request.form['description'],
                'start_date': start_date,
                'end_date': end_date,
                'candidates': candidates_details,
                'created_by': str(current_user.id), 
                'created_at': datetime.now(),
                'status': 'active',
                'votes': {str(c['id']): 0 for c in candidates_details}
            }

            logger.debug(f"Attempting to insert election: {election}")
            result = db.elections.insert_one(election)

            if result.inserted_id:
                flash('Election created successfully')
                return redirect(url_for('admin_dashboard'))
            else:
                flash('Failed to create election')
                return redirect(url_for('create_election'))

        except Exception as e:
            logger.error(f"Error creating election: {str(e)}")
            flash(f'Error creating election: {str(e)}')
            return redirect(url_for('create_election'))

    try:
        candidates = list(db.candidates.find())
        logger.debug(f"Found {len(candidates)} candidates")
        return render_template('create_election.html', candidates=candidates)
    except Exception as e:
        logger.error(f"Error loading candidates: {str(e)}")
        flash('Error loading candidates')
        return redirect(url_for('admin_dashboard'))

@app.route('/vote/<election_id>', methods=['GET', 'POST'])
@login_required
def vote(election_id):
    try:
        election = db.elections.find_one({'_id': ObjectId(election_id)})
        if not election:
            flash('Election not found')
            return redirect(url_for('dashboard'))
        if election.get('status') == 'completed':
            flash('This election has ended and voting is no longer allowed')
            return redirect(url_for('dashboard'))

        now = datetime.now()
        start_date = election.get('start_date')
        end_date = election.get('end_date')
        
        if now < start_date:
            flash('This election has not started yet')
            return redirect(url_for('dashboard'))
            
        if now > end_date:
            flash('This election has ended')
            return redirect(url_for('dashboard'))

        candidates_with_details = []
        for candidate in election.get('candidates', []):
            candidate_id = candidate.get('id')
            if not candidate_id:
                continue
        
            candidate_details = db.candidates.find_one({'_id': ObjectId(candidate_id)})
            if candidate_details:
                candidate_details['id'] = str(candidate_details['_id'])
                candidates_with_details.append(candidate_details)
        
        election['candidates'] = candidates_with_details
        has_voted = str(election['_id']) in current_user.voted_elections
        previous_vote = None
        
        if has_voted:            
            vote_record = db.vote_records.find_one({
                'user_id': str(current_user.id),
                'election_id': election_id
            })
            if vote_record:
                previous_vote = vote_record.get('candidate_id')

        if request.method == 'POST':
            if 'candidate' not in request.form:
                flash('Please select a candidate')
                return render_template('vote.html', election=election, has_voted=has_voted, previous_vote=previous_vote)

            candidate_id = request.form['candidate']
            candidate_exists = any(c['id'] == candidate_id for c in election['candidates'])
            if not candidate_exists:
                flash('Invalid candidate selection')
                return render_template('vote.html', election=election, has_voted=has_voted, previous_vote=previous_vote)

            if has_voted:
                vote_record = db.vote_records.find_one({
                    'user_id': str(current_user.id),
                    'election_id': election_id
                })
                
                if vote_record:
                    previous_candidate_id = vote_record.get('candidate_id')
                    if previous_candidate_id:
                        db.elections.update_one(
                            {'_id': ObjectId(election_id)},
                            {'$inc': {f'votes.{previous_candidate_id}': -1}}
                        )
                    
                    db.vote_records.update_one(
                        {'_id': vote_record['_id']},
                        {'$set': {
                            'candidate_id': candidate_id,
                            'voted_at': datetime.now()
                        }}
                    )
                else:
                    db.vote_records.insert_one({
                        'user_id': str(current_user.id),
                        'election_id': election_id,
                        'candidate_id': candidate_id,
                        'voted_at': datetime.now()
                    })
            else:
                db.users.update_one(
                    {'_id': current_user.id},
                    {'$push': {'voted_elections': election_id}}
                )
                
                db.vote_records.insert_one({
                    'user_id': str(current_user.id),
                    'election_id': election_id,
                    'candidate_id': candidate_id,
                    'voted_at': datetime.now()
                })

            db.elections.update_one(
                {'_id': ObjectId(election_id)},
                {'$inc': {f'votes.{candidate_id}': 1}}
            )

            if has_voted:
                flash('Your vote has been updated successfully')
            else:
                flash('Vote recorded successfully')
            
            return redirect(url_for('dashboard'))

        return render_template('vote.html', election=election, has_voted=has_voted, previous_vote=previous_vote)

    except Exception as e:
        logger.error(f"Error in vote route: {str(e)}", exc_info=True)
        flash('An error occurred while loading the voting page')
        return redirect(url_for('dashboard'))

@app.route('/results/<election_id>')
@login_required
def results(election_id):
    try:
        election = db.elections.find_one({'_id': ObjectId(election_id)})

        if not election:
            flash('Election not found')
            return redirect(url_for('dashboard'))
            
        if election.get('status') != 'completed' and current_user.role != 'admin':
            flash('Results are only available after the election has ended')
            return redirect(url_for('dashboard'))

        if 'votes' not in election:
            election['votes'] = {str(c['id']): 0 for c in election.get('candidates', [])}

        total_votes = sum(election['votes'].values())
        
        return render_template('results.html', election=election, total_votes=total_votes)

    except Exception as e:
        logger.error(f"Error viewing results: {str(e)}")
        flash('An error occurred while loading the results')
        return redirect(url_for('dashboard'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Access denied. Only administrators can access this page.')
        return redirect(url_for('dashboard'))

    try:
        elections = list(db.elections.find())
        candidates = list(db.candidates.find())
        voters = list(db.users.find({'role': 'voter'}))

        logger.debug("Admin dashboard data loaded successfully")
        return render_template('admin_dashboard.html',
                             elections=elections,
                             candidates=candidates,
                             voters=voters)
    except Exception as e:
        logger.error(f"Error loading admin dashboard: {str(e)}")
        flash('An error occurred while loading the admin dashboard.')
        return redirect(url_for('dashboard'))

@app.route('/admin/candidate/add', methods=['GET', 'POST'])
@login_required
def add_candidate():
    if current_user.role != 'admin':
        flash('Access denied')
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        try:
            image_url = None
            if 'image' in request.files:
                candidate_name = request.form['name'].lower().replace(' ', '_')
                image_url = save_uploaded_file(
                    request.files['image'], 
                    name_prefix=f"candidate_{candidate_name}"
                )
            candidate = {
                'name': request.form['name'],
                'party': request.form['party'],
                'position': request.form.get('position', ''),
                'description': request.form.get('description', ''),
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            qualifications = request.form.get('qualifications', '').strip().split('\n')
            qualifications = [q.strip() for q in qualifications if q.strip()]
            candidate['qualifications'] = qualifications
            
            campaign_promises = request.form.get('campaign_promises', '').strip().split('\n')
            campaign_promises = [p.strip() for p in campaign_promises if p.strip()]
            candidate['campaign_promises'] = campaign_promises
            
            candidate['education'] = request.form.get('education', '')
            
            candidate['contact_info'] = {
                'email': request.form.get('email', ''),
                'phone': request.form.get('phone', ''),
                'website': request.form.get('website', '')
            }

            if image_url:
                candidate['image_url'] = image_url
            
            result = db.candidates.insert_one(candidate)
            
            flash('Candidate added successfully')
            return redirect(url_for('admin_dashboard'))
            
        except Exception as e:
            flash(f'Error adding candidate: {str(e)}')
            return redirect(url_for('add_candidate'))
    
    return render_template('add_candidate.html')

@app.route('/admin/candidate/delete/<candidate_id>', methods=['POST'])
@login_required
def delete_candidate(candidate_id):
    if not current_user.is_authenticated or current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403

    try:
        candidate_id_obj = ObjectId(candidate_id)
        candidate = db.candidates.find_one({'_id': candidate_id_obj})
        if not candidate:
            return jsonify({'error': 'Candidate not found'}), 404
            
        result = db.candidates.delete_one({'_id': candidate_id_obj})
        
        if result.deleted_count > 0:
            elections = db.elections.find({'candidates.id': str(candidate_id_obj)})
            
            for election in elections:
                updated_candidates = [c for c in election.get('candidates', []) if c['id'] != str(candidate_id_obj)]
                
                votes = election.get('votes', {})
                if str(candidate_id_obj) in votes:
                    del votes[str(candidate_id_obj)]
                
                db.elections.update_one(
                    {'_id': election['_id']},
                    {'$set': {'candidates': updated_candidates, 'votes': votes}}
                )
            
            logger.info(f"Candidate {candidate_id} deleted by admin {current_user.email}")
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Failed to delete candidate'}), 500
            
    except Exception as e:
        logger.error(f"Error deleting candidate: {str(e)}")
        return jsonify({'error': 'An error occurred while deleting the candidate'}), 500

@app.route('/election/<election_id>/manage_candidates', methods=['GET', 'POST'])
@login_required
def manage_election_candidates(election_id):
    if current_user.role != 'admin':
        flash('Access denied')
        return redirect(url_for('dashboard'))

    try:
        election = db.elections.find_one({'_id': ObjectId(election_id)})
        if not election:
            flash('Election not found')
            return redirect(url_for('admin_dashboard'))

        if request.method == 'POST':
            try:
                candidate_ids = request.form.getlist('candidates')
                
                candidates_details = []
                for candidate_id in candidate_ids:
                    if not ObjectId.is_valid(candidate_id):
                        logger.error(f"Invalid candidate ID format: {candidate_id}")
                        continue
                        
                    candidate = db.candidates.find_one({'_id': ObjectId(candidate_id)})
                    if candidate:
                        logger.debug(f"Adding candidate: {candidate.get('name')}")
                        candidates_details.append({
                            'id': str(candidate['_id']),
                            'name': candidate['name'],
                            'party': candidate['party'],
                            'position': candidate.get('position', ''),
                            'description': candidate.get('description', ''),
                            'image_url': candidate.get('image_url')
                        })
                    else:
                        logger.warning(f"Candidate not found with ID: {candidate_id}")
                        votes = {}
                for candidate in candidates_details:
                    votes[candidate['id']] = election.get('votes', {}).get(candidate['id'], 0)
                
    
                db.elections.update_one(
                    {'_id': ObjectId(election_id)},
                    {'$set': {
                        'candidates': candidates_details,
                        'votes': votes
                    }}
                )
                
                flash('Candidates updated successfully')
                return redirect(url_for('admin_dashboard'))
                
            except Exception as e:
                logger.error(f"Error updating candidates: {str(e)}")
                flash('An error occurred while updating candidates')
                return redirect(url_for('admin_dashboard'))
        
        try:
            all_candidates = list(db.candidates.find())
            
            selected_candidate_ids = [c['id'] for c in election.get('candidates', [])]
            
            return render_template(
                'manage_candidates.html',
                election=election,
                all_candidates=all_candidates,
                selected_candidate_ids=selected_candidate_ids
            )
        except Exception as e:
            logger.error(f"Error preparing template data: {str(e)}", exc_info=True)
            flash(f'Error loading candidates: {str(e)}')
            return redirect(url_for('admin_dashboard'))

    except Exception as e:
        logger.error(f"Error managing election candidates: {str(e)}", exc_info=True)
        flash('An error occurred while managing candidates')
        return redirect(url_for('admin_dashboard'))

@app.route('/api/election/<election_id>/candidates', methods=['GET'])
@login_required
def get_election_candidates(election_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403

    try:
        election = db.elections.find_one({'_id': ObjectId(election_id)})
        if not election:
            return jsonify({'error': 'Election not found'}), 404

        all_candidates = list(db.candidates.find())
        for candidate in all_candidates:
            candidate['_id'] = str(candidate['_id'])
        

        selected_candidate_ids = [c['id'] for c in election.get('candidates', [])]
        election['_id'] = str(election['_id'])
        
        return jsonify({
            'election': election,
            'all_candidates': all_candidates,
            'selected_candidate_ids': selected_candidate_ids
        })
        
    except Exception as e:
        logger.error(f"Error getting election candidates: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/election/<election_id>/update_candidates', methods=['POST'])
@login_required
def update_election_candidates(election_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403

    try:
        election = db.elections.find_one({'_id': ObjectId(election_id)})
        if not election:
            return jsonify({'error': 'Election not found'}), 404
        
        data = request.json
        candidate_ids = data.get('candidates', [])
        
        if not candidate_ids:
            return jsonify({'error': 'No candidates selected'}), 400
        
        candidates_details = []
        for candidate_id in candidate_ids:
            if not ObjectId.is_valid(candidate_id):
                logger.error(f"Invalid candidate ID format: {candidate_id}")
                continue
                
            candidate = db.candidates.find_one({'_id': ObjectId(candidate_id)})
            if candidate:
                logger.debug(f"Adding candidate: {candidate.get('name')}")
                candidates_details.append({
                    'id': str(candidate['_id']),
                    'name': candidate['name'],
                    'party': candidate['party'],
                    'position': candidate.get('position', ''),
                    'description': candidate.get('description', ''),
                    'image_url': candidate.get('image_url')
                })
            else:
                logger.warning(f"Candidate not found with ID: {candidate_id}")
        
        votes = {}
        for candidate in candidates_details:
            votes[candidate['id']] = election.get('votes', {}).get(candidate['id'], 0)
        
        db.elections.update_one(
            {'_id': ObjectId(election_id)},
            {'$set': {
                'candidates': candidates_details,
                'votes': votes
            }}
        )
        
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"Error updating election candidates: {str(e)}", exc_info=True)
        return jsonify({'error': str(e), 'success': False}), 500

@app.route('/election/<election_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_election(election_id):
    if current_user.role != 'admin':
        flash('Access denied')
        return redirect(url_for('dashboard'))

    try:
        election = db.elections.find_one({'_id': ObjectId(election_id)})
        if not election:
            flash('Election not found')
            return redirect(url_for('admin_dashboard'))

        if request.method == 'POST':
            start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d')
            end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d')

            update_data = {
                'title': request.form['title'],
                'description': request.form['description'],
                'start_date': start_date,
                'end_date': end_date,
                'status': request.form['status'],
                'updated_at': datetime.now()
            }

            result = db.elections.update_one(
                {'_id': ObjectId(election_id)},
                {'$set': update_data}
            )

            if result.modified_count > 0:
                flash('Election updated successfully')
                return redirect(url_for('admin_dashboard'))
            else:
                flash('No changes made to the election')
                return redirect(url_for('edit_election', election_id=election_id))

        return render_template('edit_election.html', election=election)

    except Exception as e:
        logger.error(f"Error editing election: {str(e)}")
        flash('An error occurred while editing the election')
        return redirect(url_for('admin_dashboard'))

@app.route('/api/election/<election_id>/results')
@login_required
def api_election_results(election_id):
    try:
        election = db.elections.find_one({'_id': ObjectId(election_id)})
        if not election:
            return jsonify({'error': 'Election not found'}), 404
            
        if election.get('status') != 'completed' and current_user.role != 'admin':
            return jsonify({'error': 'Results are only available after the election has ended'}), 403

        if 'votes' not in election:
            election['votes'] = {str(c['id']): 0 for c in election.get('candidates', [])}

        response_data = {
            'title': election.get('title', 'Untitled Election'),
            'description': election.get('description', 'No description'),
            'candidates': [{
                'id': str(c.get('id', '')),
                'name': c.get('name', 'Unknown'),
                'party': c.get('party', 'No Party')
            } for c in election.get('candidates', []) if 'id' in c],
            'votes': election.get('votes', {}),
            'status': election.get('status', 'unknown')
        }

        return jsonify(response_data)
    except Exception as e:
        logger.error(f"Error in API election results: {str(e)}")
        return jsonify({'error': 'An error occurred while fetching results'}), 500

@app.route('/admin/candidate/edit/<candidate_id>', methods=['GET', 'POST'])
@login_required
def edit_candidate(candidate_id):
    if current_user.role != 'admin':
        flash('Access denied')
        return redirect(url_for('dashboard'))

    try:
        candidate = db.candidates.find_one({'_id': ObjectId(candidate_id)})
        if not candidate:
            flash('Candidate not found')
            return redirect(url_for('admin_dashboard'))
            
        logger.debug(f"Candidate data: {candidate}")
        if request.method == 'POST':
            image_url = candidate.get('image_url')
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename:
                    if image_url:
                        old_file_path = os.path.join(app.config['UPLOAD_FOLDER'], image_url)
                        if os.path.exists(old_file_path):
                            os.remove(old_file_path)
                    
                    candidate_name = request.form['name'].lower().replace(' ', '_')
                    image_url = save_uploaded_file(
                        file, 
                        name_prefix=f"candidate_{candidate_name}"
                    )
            qualifications = request.form.get('qualifications', '').strip().split('\n')
            qualifications = [q.strip() for q in qualifications if q.strip()]
            
            campaign_promises = request.form.get('campaign_promises', '').strip().split('\n')
            campaign_promises = [p.strip() for p in campaign_promises if p.strip()]
            contact_info = {
                'email': request.form.get('email', ''),
                'phone': request.form.get('phone', ''),
                'website': request.form.get('website', '')
            }

            update_data = {
                'name': request.form['name'],
                'party': request.form['party'],
                'position': request.form.get('position', ''),
                'description': request.form.get('description', ''),
                'qualifications': qualifications,
                'campaign_promises': campaign_promises,
                'education': request.form.get('education', ''),
                'contact_info': contact_info,
                'updated_at': datetime.utcnow()
            }
            
            if image_url:
                update_data['image_url'] = image_url

            db.candidates.update_one(
                {'_id': ObjectId(candidate_id)},
                {'$set': update_data}
            )
            
            flash('Candidate updated successfully')
            return redirect(url_for('admin_dashboard'))
        candidate['_id'] = str(candidate['_id'])
        
        if 'qualifications' not in candidate:
            candidate['qualifications'] = []
        if 'campaign_promises' not in candidate:
            candidate['campaign_promises'] = []
        if 'education' not in candidate:
            candidate['education'] = ''
        if 'contact_info' not in candidate:
            candidate['contact_info'] = {'email': '', 'phone': '', 'website': ''}
        elif not isinstance(candidate['contact_info'], dict):
            candidate['contact_info'] = {'email': '', 'phone': '', 'website': ''}
            
        logger.debug(f"Candidate prepared for template: {candidate}")

        return render_template('edit_candidate.html', candidate=candidate)

    except Exception as e:
        logger.error(f"Error editing candidate: {str(e)}")
        flash('Error updating candidate')
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/voter/edit/<voter_id>', methods=['GET', 'POST'])
@login_required
def edit_voter(voter_id):
    if current_user.role != 'admin':
        flash('Access denied')
        return redirect(url_for('dashboard'))

    try:
        voter = db.users.find_one({'_id': ObjectId(voter_id), 'role': 'voter'})
        if not voter:
            flash('Voter not found')
            return redirect(url_for('admin_dashboard'))

        if request.method == 'POST':
            try:
                dob = datetime.strptime(request.form['date_of_birth'], '%Y-%m-%d')    
                today = datetime.now()
                age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                
                if age < 18:
                    flash('Voter must be at least 18 years old')
                    return redirect(url_for('edit_voter', voter_id=voter_id))
                
                update_data = {
                    'username': request.form['username'],
                    'email': request.form['email'],
                    'full_name': request.form['full_name'],
                    'address': request.form['address'],
                    'phone': request.form['phone'],
                    'date_of_birth': dob,
                    'voter_id': request.form['voter_id'],
                    'updated_at': datetime.now()
                }
                
                existing_user = db.users.find_one({
                    'email': update_data['email'], 
                    '_id': {'$ne': ObjectId(voter_id)}
                })
                
                if existing_user:
                    flash('Email already in use by another user')
                    return redirect(url_for('edit_voter', voter_id=voter_id))
                
                result = db.users.update_one(
                    {'_id': ObjectId(voter_id)},
                    {'$set': update_data}
                )
                
                if result.modified_count > 0:
                    flash('Voter updated successfully')
                else:
                    flash('No changes made to voter')
                
                return redirect(url_for('admin_dashboard'))
                
            except ValueError:
                flash('Invalid date format')
                return redirect(url_for('edit_voter', voter_id=voter_id))
            except Exception as e:
                logger.error(f"Error updating voter: {str(e)}")
                flash('An error occurred while updating the voter')
                return redirect(url_for('edit_voter', voter_id=voter_id))
        voted_elections = []
        for election_id in voter.get('voted_elections', []):
            try:
                election = db.elections.find_one({'_id': ObjectId(election_id)})
                if election:
                    voted_elections.append(election)
            except Exception as e:
                logger.error(f"Error fetching election {election_id}: {str(e)}")

        now = datetime.now()
        age18 = timedelta(days=365*18)
        
        return render_template('edit_voter.html', voter=voter, voted_elections=voted_elections, now=now, age18=age18)

    except Exception as e:
        logger.error(f"Error editing voter: {str(e)}")
        flash('An error occurred while editing the voter')
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/voter/view/<voter_id>')
@login_required
def view_voter(voter_id):
    if current_user.role != 'admin':
        flash('Access denied')
        return redirect(url_for('dashboard'))

    try:
        voter = db.users.find_one({'_id': ObjectId(voter_id), 'role': 'voter'})
        if not voter:
            flash('Voter not found')
            return redirect(url_for('admin_dashboard'))
            
        voted_elections = []
        for election_id in voter.get('voted_elections', []):
            try:
                election = db.elections.find_one({'_id': ObjectId(election_id)})
                if election:
                    voted_elections.append(election)
            except:
                pass
                
        return render_template('view_voter.html', voter=voter, voted_elections=voted_elections)
        
    except Exception as e:
        logger.error(f"Error viewing voter: {str(e)}")
        flash('An error occurred while viewing the voter')
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/voter/delete/<voter_id>', methods=['POST'])
@login_required
def delete_voter(voter_id):
    if not current_user.is_authenticated or current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403

    try:
        voter = db.users.find_one({'_id': ObjectId(voter_id), 'role': 'voter'})
        if not voter:
            return jsonify({'error': 'Voter not found'}), 404

        result = db.users.delete_one({'_id': ObjectId(voter_id)})
        
        if result.deleted_count > 0:
            logger.info(f"Voter {voter_id} deleted by admin {current_user.email}")
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Failed to delete voter'}), 500
            
    except Exception as e:
        logger.error(f"Error deleting voter: {str(e)}")
        return jsonify({'error': 'An error occurred while deleting the voter'}), 500

@app.route('/admin/voter/reset_password/<voter_id>', methods=['POST'])
@login_required
def reset_voter_password(voter_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403

    try:
        temp_password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        
        password_hash = generate_password_hash(temp_password)
        result = db.users.update_one(
            {'_id': ObjectId(voter_id)},
            {'$set': {
                'password_hash': password_hash,
                'temp_password_flag': True 
            }}
        )
        
        if result.modified_count > 0:
            logger.info(f"Password reset for voter {voter_id} by admin {current_user.email}")
            return jsonify({
                'success': True, 
                'temp_password': temp_password
            })
        else:
            return jsonify({'error': 'Failed to reset password'}), 500
            
    except Exception as e:
        logger.error(f"Error resetting password: {str(e)}")
        return jsonify({'error': 'An error occurred while resetting the password'}), 500

@app.route('/admin/election/delete/<election_id>', methods=['POST'])
@login_required
def delete_election(election_id):
    if not current_user.is_authenticated or current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403

    try:
        election = db.elections.find_one({'_id': ObjectId(election_id)})
        if not election:
            return jsonify({'error': 'Election not found'}), 404
        result = db.elections.delete_one({'_id': ObjectId(election_id)})
        
        if result.deleted_count > 0:
            db.users.update_many(
                {'voted_elections': election_id},
                {'$pull': {'voted_elections': election_id}}
            )
            
            logger.info(f"Election {election_id} deleted by admin {current_user.email}")
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Failed to delete election'}), 500
            
    except Exception as e:
        logger.error(f"Error deleting election: {str(e)}")
        return jsonify({'error': 'An error occurred while deleting the election'}), 500


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        
        if new_password != confirm_password:
            flash('New passwords do not match')
            return redirect(url_for('change_password'))
        user_data = db.users.find_one({'_id': current_user._id})
        
        if not user_data:
            flash('User not found')
            return redirect(url_for('dashboard'))
        
        if not check_password_hash(user_data['password_hash'], current_password):
            flash('Current password is incorrect')
            return redirect(url_for('change_password'))
        new_password_hash = generate_password_hash(new_password)
        result = db.users.update_one(
            {'_id': current_user._id},
            {'$set': {
                'password_hash': new_password_hash,
                'temp_password_flag': False 
            }}
        )
        
        if result.modified_count > 0:
            flash('Password changed successfully')
            return redirect(url_for('dashboard'))
        else:
            flash('Failed to change password')
            
    return render_template('change_password.html')

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        email = request.form['email']
        
        user = db.users.find_one({'email': email})
        
        if user:
            temp_password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
            
            password_hash = generate_password_hash(temp_password)
            result = db.users.update_one(
                {'_id': user['_id']},
                {'$set': {
                    'password_hash': password_hash,
                    'temp_password_flag': True  
                }}
            )
            
            if result.modified_count > 0:
                flash(f'Your temporary password is: {temp_password}')
                flash('Please use this password to login and then change your password immediately.')
                logger.info(f"Password reset for user {email}")
                return redirect(url_for('login'))
        
    return render_template('forgot_password.html')

def save_uploaded_file(file, name_prefix=None):
    if file and file.filename:
        filename = secure_filename(file.filename)
        if name_prefix:
            _, file_extension = os.path.splitext(filename)
            filename = f"{name_prefix}{file_extension}"
        
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        logger.debug(f"Saved file to {file_path}")
        return filename
    return None

@app.route('/admin/update_candidate_fields', methods=['GET'])
@login_required
def update_candidate_fields():
    if current_user.role != 'admin':
        flash('Access denied')
        return redirect(url_for('dashboard'))
        
    try:
        candidates = list(db.candidates.find())
        
        for candidate in candidates:
            update_data = {}
            
            if 'qualifications' not in candidate:
                update_data['qualifications'] = []
            elif not isinstance(candidate['qualifications'], list):
                update_data['qualifications'] = []
            if 'campaign_promises' not in candidate:
                update_data['campaign_promises'] = []
            elif not isinstance(candidate['campaign_promises'], list):
                update_data['campaign_promises'] = []
                
            if 'education' not in candidate:
                update_data['education'] = ''
            
            if 'contact_info' not in candidate:
                update_data['contact_info'] = {
                    'email': '',
                    'phone': '',
                    'website': ''
                }
            elif not isinstance(candidate['contact_info'], dict):
                update_data['contact_info'] = {
                    'email': '',
                    'phone': '',
                    'website': ''
                }
            else:
                contact_info = {}
                needs_update = False
                
                if 'email' not in candidate['contact_info']:
                    contact_info['email'] = ''
                    needs_update = True
                else:
                    contact_info['email'] = candidate['contact_info']['email']
                    
                if 'phone' not in candidate['contact_info']:
                    contact_info['phone'] = ''
                    needs_update = True
                else:
                    contact_info['phone'] = candidate['contact_info']['phone']
                    
                if 'website' not in candidate['contact_info']:
                    contact_info['website'] = ''
                    needs_update = True
                else:
                    contact_info['website'] = candidate['contact_info']['website']
                
                if needs_update:
                    update_data['contact_info'] = contact_info
                
            if update_data:
                db.candidates.update_one(
                    {'_id': candidate['_id']},
                    {'$set': update_data}
                )
                
        flash('All candidates updated successfully')
        return redirect(url_for('admin_dashboard'))
    except Exception as e:
        flash(f'Error updating candidates: {str(e)}')
        return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    if not os.path.exists(os.path.join('static', 'images')):
        os.makedirs(os.path.join('static', 'images'))
    
    app.run(debug=True)