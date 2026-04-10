from flask import Flask, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tasks.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Task model
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(50), default='pending')
    priority = db.Column(db.Integer, default=0)
    sensitivity = db.Column(db.String(20), default='normal')
    assigned_to = db.Column(db.String(80))
    created_by = db.Column(db.String(80), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

# Helper function to check if user is admin
def is_admin(username):
    # This is a simple implementation - in production you'd want a more robust system
    return username == 'admin'

# Routes
@app.route('/')
def index():
    return jsonify({'message': 'Task Management API'})

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    
    if not data or not data.get('username') or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Username, email and password are required'}), 400
        
    # Check if user already exists
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already exists'}), 400
        
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already exists'}), 400
        
    # Create new user
    user = User(username=data['username'], email=data['email'])
    user.set_password(data['password'])
    
    try:
        db.session.add(user)
        db.session.commit()
        return jsonify({'message': 'User registered successfully'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to register user'}), 500

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'error': 'Username and password are required'}), 400
        
    user = User.query.filter_by(username=data['username']).first()
    
    if user and user.check_password(data['password']):
        session['username'] = user.username
        return jsonify({'message': 'Logged in successfully'})
    else:
        return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('username', None)
    return jsonify({'message': 'Logged out successfully'})

# Task routes
@app.route('/tasks', methods=['GET'])
def get_tasks():
    if 'username' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
        
    tasks = Task.query.order_by(Task.created_at.desc()).all()
    return jsonify([{
        'id': task.id,
        'title': task.title,
        'description': task.description,
        'status': task.status,
        'priority': task.priority,
        'sensitivity': task.sensitivity,
        'assigned_to': task.assigned_to,
        'created_by': task.created_by
    } for task in tasks])

@app.route('/tasks', methods=['POST'])
def create_task():
    if 'username' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
        
    data = request.get_json()
    
    if not data or not data.get('title'):
        return jsonify({'error': 'Title is required'}), 400
        
    task = Task(
        title=data['title'],
        description=data.get('description'),
        status=data.get('status', 'pending'),
        priority=data.get('priority', 0),
        sensitivity=data.get('sensitivity', 'normal'),
        assigned_to=data.get('assigned_to'),
        created_by=session['username']
    )
    
    try:
        db.session.add(task)
        db.session.commit()
        return jsonify({
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'status': task.status,
            'priority': task.priority,
            'sensitivity': task.sensitivity,
            'assigned_to': task.assigned_to,
            'created_by': task.created_by
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to create task'}), 500

@app.route('/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    if 'username' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
        
    task = Task.query.get_or_404(task_id)
    
    # Only allow the creator or admin to modify
    if task.created_by != session['username'] and not is_admin(session['username']):
        return jsonify({'error': 'Permission denied'}), 403
        
    data = request.get_json()
    
    task.title = data.get('title', task.title)
    task.description = data.get('description', task.description)
    task.status = data.get('status', task.status)
    task.priority = data.get('priority', task.priority)
    task.sensitivity = data.get('sensitivity', task.sensitivity)
    task.assigned_to = data.get('assigned_to', task.assigned_to)
    
    try:
        db.session.commit()
        return jsonify({
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'status': task.status,
            'priority': task.priority,
            'sensitivity': task.sensitivity,
            'assigned_to': task.assigned_to,
            'created_by': task.created_by
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to update task'}), 500

@app.route('/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    if 'username' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
        
    task = Task.query.get_or_404(task_id)
    
    # Only allow the creator or admin to delete
    if task.created_by != session['username'] and not is_admin(session['username']):
        return jsonify({'error': 'Permission denied'}), 403
        
    try:
        db.session.delete(task)
        db.session.commit()
        return jsonify({'message': 'Task deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to delete task'}), 500

if __name__ == '__main__':
    # Create the database tables
    from flask import Flask
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tasks.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    from flask_sqlalchemy import SQLAlchemy
    db = SQLAlchemy(app)
    
    with app.app_context():
        db.create_all()
        
    print("Database initialized successfully")