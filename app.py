from flask import Flask, render_template, request, session, redirect, url_for, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix
from datetime import datetime
import json
import os
import logging
from functools import wraps
from dotenv import load_dotenv

load_dotenv()

# ------------------ ENVIRONMENT / CONFIG ------------------
# In production these MUST come from real environment variables, never from
# a default baked into source. We fail loudly instead of silently generating
# a throwaway key, because a rotating key would invalidate every session and
# a guessable one is a security hole.

IS_PRODUCTION = os.environ.get('FLASK_ENV', 'production') == 'production'

SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    if IS_PRODUCTION:
        raise RuntimeError(
            'SECRET_KEY environment variable is not set. Generate one with '
            '`python -c "import secrets; print(secrets.token_hex(32))"` and set it '
            'in your environment (never commit it to source control).'
        )
    # Local dev convenience only - never reached in production because of the raise above.
    import secrets as _secrets
    SECRET_KEY = _secrets.token_hex(32)

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///career_roadmap_pro.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'pool_pre_ping': True}

# Harden session cookies. SESSION_COOKIE_SECURE requires HTTPS - enable once
# you have a TLS cert in front of the app (see Dockerfile/deploy notes).
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = IS_PRODUCTION
app.config['REMEMBER_COOKIE_SECURE'] = IS_PRODUCTION

# Trust one proxy hop (nginx/Render/Railway etc.) for correct client IPs and https detection.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

logging.basicConfig(
    level=logging.INFO if IS_PRODUCTION else logging.DEBUG,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s'
)
logger = logging.getLogger('career_roadmap')

db = SQLAlchemy(app)
migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

csrf = CSRFProtect(app)

limiter = Limiter(get_remote_address, app=app, default_limits=['200 per hour'], storage_uri='memory://')

# ------------------ AI CLIENT ------------------
# Real AI is optional at the infra level: if ANTHROPIC_API_KEY isn't set, the
# app falls back to the original rule-based responses instead of crashing.
# This keeps local dev/demo usable without a key, while production should
# always set one for the real experience.
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
anthropic_client = None
if ANTHROPIC_API_KEY:
    from anthropic import Anthropic
    anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY)
else:
    logger.warning('ANTHROPIC_API_KEY not set - chatbot and roadmap generation will use basic fallback logic.')

# ------------------ MODELS ------------------

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_verified = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    
    profile = db.relationship('Profile', backref='user', uselist=False)
    roadmaps = db.relationship('Roadmap', backref='user', lazy=True)
    learning = db.relationship('UserLearning', backref='user', lazy=True)
    goals = db.relationship('Goal', backref='user', lazy=True)
    badges = db.relationship('UserBadge', backref='user', lazy=True)
    notifications = db.relationship('Notification', backref='user', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Profile(db.Model):
    __tablename__ = 'profile'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True)
    full_name = db.Column(db.String(100))
    bio = db.Column(db.Text)
    avatar = db.Column(db.String(200))
    skills = db.Column(db.Text)
    education = db.Column(db.Text)
    interests = db.Column(db.Text)
    career_goal = db.Column(db.String(200))
    certifications = db.Column(db.Text)
    experience_years = db.Column(db.Integer, default=0)
    location = db.Column(db.String(100))
    linkedin_url = db.Column(db.String(200))
    github_url = db.Column(db.String(200))
    portfolio_url = db.Column(db.String(200))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Roadmap(db.Model):
    __tablename__ = 'roadmap'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    career_title = db.Column(db.String(100))
    roadmap_data = db.Column(db.Text)
    skill_gaps = db.Column(db.Text)
    matched_skills = db.Column(db.Text)
    timeline = db.Column(db.String(50))
    progress = db.Column(db.Integer, default=0)
    is_completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class LearningResource(db.Model):
    __tablename__ = 'learning_resource'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    platform = db.Column(db.String(50))
    url = db.Column(db.String(500))
    category = db.Column(db.String(50))
    difficulty = db.Column(db.String(20))
    price = db.Column(db.String(20))
    rating = db.Column(db.Float)
    tags = db.Column(db.String(200))
    image_url = db.Column(db.String(500))
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    views = db.Column(db.Integer, default=0)
    
    learning = db.relationship('UserLearning', backref='resource', lazy=True)

class UserLearning(db.Model):
    __tablename__ = 'user_learning'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    resource_id = db.Column(db.Integer, db.ForeignKey('learning_resource.id'))
    status = db.Column(db.String(20), default='not_started')
    progress = db.Column(db.Integer, default=0)
    rating = db.Column(db.Integer)
    review = db.Column(db.Text)
    started_date = db.Column(db.DateTime)
    completed_date = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Goal(db.Model):
    __tablename__ = 'goal'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    target_date = db.Column(db.DateTime)
    progress = db.Column(db.Integer, default=0)
    is_completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Badge(db.Model):
    __tablename__ = 'badge'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True)
    description = db.Column(db.Text)
    icon = db.Column(db.String(50))
    points = db.Column(db.Integer, default=10)
    category = db.Column(db.String(50))
    
    users = db.relationship('UserBadge', backref='badge', lazy=True)

class UserBadge(db.Model):
    __tablename__ = 'user_badge'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    badge_id = db.Column(db.Integer, db.ForeignKey('badge.id'))
    earned_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_displayed = db.Column(db.Boolean, default=True)

class Notification(db.Model):
    __tablename__ = 'notification'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    type = db.Column(db.String(50))
    message = db.Column(db.Text)
    link = db.Column(db.String(200))
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class CareerTrend(db.Model):
    __tablename__ = 'career_trend'
    id = db.Column(db.Integer, primary_key=True)
    job_title = db.Column(db.String(100))
    industry = db.Column(db.String(50))
    demand_score = db.Column(db.Integer)
    avg_salary = db.Column(db.String(50))
    growth_rate = db.Column(db.String(20))
    required_skills = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# ------------------ DECORATORS ------------------

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Admin access required.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# ------------------ CONTEXT PROCESSOR ------------------

@app.context_processor
def utility_processor():
    def get_unread_notifications():
        if current_user.is_authenticated:
            return Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
        return 0
    return dict(get_unread_notifications=get_unread_notifications)

# ------------------ ROUTES ------------------

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

@app.route('/')
def home():
    featured_resources = LearningResource.query.limit(6).all()
    trends = CareerTrend.query.order_by(CareerTrend.demand_score.desc()).limit(5).all()
    return render_template('index.html', 
                         featured_resources=featured_resources,
                         trends=trends)

@app.route('/register', methods=['GET', 'POST'])
@limiter.limit('10 per hour')
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if not all([username, email, password]):
            flash('All fields are required.', 'danger')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html')
        
        if len(password) < 8:
            flash('Password must be at least 8 characters.', 'danger')
            return render_template('register.html')
        
        if User.query.filter_by(username=username).first():
            flash('Username already taken.', 'danger')
            return render_template('register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return render_template('register.html')
        
        user = User(username=username, email=email)
        user.set_password(password)
        user.is_verified = True
        
        db.session.add(user)
        db.session.commit()
        
        profile = Profile(
            user_id=user.id,
            skills=request.form.get('skills', ''),
            education=request.form.get('education', ''),
            interests=request.form.get('interests', ''),
            career_goal=request.form.get('career_goal', ''),
            certifications=request.form.get('certifications', '')
        )
        db.session.add(profile)
        db.session.commit()
        
        flash('Registration successful! You can now login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit('10 per minute')
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        
        user = User.query.filter_by(username=username).first()
        
        if not user or not user.check_password(password):
            flash('Invalid credentials.', 'danger')
            return render_template('login.html')
        
        login_user(user, remember=remember)
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        next_page = request.args.get('next')
        return redirect(next_page) if next_page else redirect(url_for('dashboard'))
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

@app.route('/dashboard')
@login_required
def dashboard():
    roadmap = Roadmap.query.filter_by(user_id=current_user.id).order_by(Roadmap.created_at.desc()).first()
    learning_count = UserLearning.query.filter_by(user_id=current_user.id).count()
    completed_count = UserLearning.query.filter_by(user_id=current_user.id, status='completed').count()
    goals = Goal.query.filter_by(user_id=current_user.id, is_completed=False).all()
    notifications = Notification.query.filter_by(user_id=current_user.id, is_read=False).limit(5).all()
    user_badges = UserBadge.query.filter_by(user_id=current_user.id).all()
    
    return render_template('dashboard.html',
                         roadmap=roadmap,
                         learning_count=learning_count,
                         completed_count=completed_count,
                         goals=goals,
                         notifications=notifications,
                         user_badges=user_badges)

@app.route('/generate_roadmap', methods=['POST'])
@login_required
def generate_roadmap():
    skills = request.form.get('skills', '')
    education = request.form.get('education', '')
    interests = request.form.get('interests', '')
    career_goal = request.form.get('career_goal', '')
    certifications = request.form.get('certifications', '')
    
    profile = Profile.query.filter_by(user_id=current_user.id).first()
    if profile:
        profile.skills = skills
        profile.education = education
        profile.interests = interests
        profile.career_goal = career_goal
        profile.certifications = certifications
        db.session.commit()
    
    FALLBACK_CAREER_PATHS = {
        'data_science': {
            'title': 'Data Scientist',
            'courses': ['Python', 'Statistics', 'Machine Learning', 'SQL', 'Data Visualization'],
            'projects': ['Sentiment Analysis', 'Recommendation System'],
            'certifications': ['IBM Data Science', 'Google Analytics'],
            'timeline': '8-12 months'
        },
        'web_dev': {
            'title': 'Full Stack Developer',
            'courses': ['HTML/CSS', 'JavaScript', 'React', 'Node.js', 'Python/Django'],
            'projects': ['Portfolio Website', 'E-commerce App'],
            'certifications': ['Meta Frontend', 'AWS Cloud Practitioner'],
            'timeline': '6-8 months'
        },
        'cybersecurity': {
            'title': 'Cybersecurity Analyst',
            'courses': ['Network Security', 'Ethical Hacking', 'Cryptography', 'Python'],
            'projects': ['Vulnerability Scanner', 'Security Audit'],
            'certifications': ['CompTIA Security+', 'CEH'],
            'timeline': '10-14 months'
        },
        'cloud_computing': {
            'title': 'Cloud Architect',
            'courses': ['AWS', 'Azure', 'Docker', 'Kubernetes', 'Terraform'],
            'projects': ['Cloud Migration', 'Kubernetes Cluster'],
            'certifications': ['AWS Solutions Architect', 'Google Cloud Engineer'],
            'timeline': '8-10 months'
        }
    }

    def fallback_roadmap():
        selected_path = 'web_dev'
        if 'data' in interests.lower() or 'science' in interests.lower():
            selected_path = 'data_science'
        elif 'security' in interests.lower() or 'cyber' in interests.lower():
            selected_path = 'cybersecurity'
        elif 'cloud' in interests.lower() or 'aws' in interests.lower():
            selected_path = 'cloud_computing'
        return FALLBACK_CAREER_PATHS[selected_path]

    roadmap_data = None
    if anthropic_client:
        try:
            prompt = (
                "Generate a personalized career roadmap as strict JSON only (no markdown fences, "
                "no commentary) with exactly these keys: "
                '"title" (string, a specific job title), '
                '"timeline" (string, e.g. "8-10 months"), '
                '"courses" (array of 4-6 short course/topic name strings), '
                '"projects" (array of 2-4 short project idea strings), '
                '"certifications" (array of 2-3 relevant certification name strings). '
                f"Base it on - skills: {skills or 'none listed'}; education: {education or 'none listed'}; "
                f"interests: {interests or 'none listed'}; career goal: {career_goal or 'none listed'}; "
                f"certifications already held: {certifications or 'none'}."
            )
            completion = anthropic_client.messages.create(
                model='claude-sonnet-4-6',
                max_tokens=600,
                messages=[{'role': 'user', 'content': prompt}]
            )
            text = ''.join(block.text for block in completion.content if block.type == 'text').strip()
            parsed = json.loads(text)
            if all(k in parsed for k in ('title', 'timeline', 'courses', 'projects', 'certifications')):
                roadmap_data = parsed
        except Exception:
            logger.exception('Anthropic API call failed in /generate_roadmap, falling back to templates')

    if roadmap_data is None:
        roadmap_data = fallback_roadmap()

    roadmap = Roadmap(
        user_id=current_user.id,
        career_title=roadmap_data['title'],
        roadmap_data=json.dumps(roadmap_data),
        skill_gaps=json.dumps([]),
        matched_skills=json.dumps([]),
        timeline=roadmap_data['timeline']
    )
    db.session.add(roadmap)
    db.session.commit()
    
    flash('Roadmap generated successfully!', 'success')
    return redirect(url_for('roadmap_view'))

@app.route('/roadmap')
@login_required
def roadmap_view():
    roadmap = Roadmap.query.filter_by(user_id=current_user.id).order_by(Roadmap.created_at.desc()).first()
    if roadmap and roadmap.roadmap_data:
        roadmap_data = json.loads(roadmap.roadmap_data)
    else:
        roadmap_data = {}
    
    return render_template('roadmap.html', roadmap=roadmap_data)

@app.route('/resources')
@login_required
def resources():
    resources = LearningResource.query.all()
    return render_template('resources.html', resources=resources)

@app.route('/recommendations')
@login_required
def recommendations():
    resources = LearningResource.query.order_by(LearningResource.rating.desc()).limit(10).all()
    return render_template('recommendations.html', recommendations=resources)

@app.route('/chatbot')
@login_required
def chatbot():
    return render_template('chatbot.html')

@app.route('/youtube')
@login_required
def youtube_resources():
    return render_template('youtube.html')

@app.route('/goals')
@login_required
def goals():
    user_goals = Goal.query.filter_by(user_id=current_user.id).order_by(Goal.created_at.desc()).all()
    return render_template('goals.html', goals=user_goals)

@app.route('/add_goal', methods=['POST'])
@login_required
def add_goal():
    title = request.form.get('title')
    description = request.form.get('description', '')
    target_date = request.form.get('target_date')
    
    if not title:
        flash('Goal title is required.', 'danger')
        return redirect(url_for('goals'))
    
    goal = Goal(
        user_id=current_user.id,
        title=title,
        description=description,
        target_date=datetime.strptime(target_date, '%Y-%m-%d') if target_date else None,
        progress=0
    )
    db.session.add(goal)
    db.session.commit()
    
    flash('Goal added successfully!', 'success')
    return redirect(url_for('goals'))

@app.route('/update_goal_progress', methods=['POST'])
@login_required
def update_goal_progress():
    data = request.get_json()
    goal_id = data.get('goal_id')
    progress = data.get('progress', 0)
    
    goal = Goal.query.filter_by(id=goal_id, user_id=current_user.id).first()
    if goal:
        goal.progress = min(progress, 100)
        if goal.progress >= 100:
            goal.is_completed = True
        db.session.commit()
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'error': 'Goal not found'}), 404

@app.route('/add_learning', methods=['POST'])
@login_required
def add_learning():
    data = request.get_json(silent=True) or {}
    resource_id = data.get('resource_id')
    status = data.get('status', 'not_started')

    resource = db.session.get(LearningResource, resource_id) if resource_id else None
    if not resource:
        return jsonify({'error': 'Resource not found'}), 404

    existing = UserLearning.query.filter_by(user_id=current_user.id, resource_id=resource_id).first()
    if existing:
        return jsonify({'message': 'Already in your learning list'})

    entry = UserLearning(
        user_id=current_user.id,
        resource_id=resource_id,
        status=status,
        started_date=datetime.utcnow() if status != 'not_started' else None
    )
    db.session.add(entry)
    db.session.commit()

    return jsonify({'message': 'Added to your learning list'})

FALLBACK_CHAT_RESPONSES = {
    'hello': '👋 Hello! I\'m your Career Assistant. How can I help you today?',
    'hi': '👋 Hi there! What career questions do you have?',
    'help': 'I can help with career advice, skill recommendations, courses, and more!',
    'career': 'I can help you find the right career path. What are you interested in?',
    'skill': 'Top skills: Python, JavaScript, SQL, Cloud Computing, AI/ML, Cybersecurity',
    'course': 'Check out the Resources page for curated courses from top platforms!',
    'roadmap': 'Go to Dashboard and click "Generate AI Roadmap" for a personalized plan!',
    'data scientist': 'Data Science requires Python, Statistics, ML, SQL. Start with Coursera!',
    'web developer': 'Web Dev: HTML/CSS, JavaScript, React, Node.js. Try The Odin Project!',
    'cybersecurity': 'Cybersecurity: Network Security, Ethical Hacking. Start with CompTIA Security+!',
    'cloud': 'Cloud Computing: AWS, Azure, GCP, Docker, Kubernetes. Start with AWS Training!'
}

def fallback_chat_response(user_message):
    for key, response in FALLBACK_CHAT_RESPONSES.items():
        if key in user_message:
            return response
    return 'I\'m here to help with your career! Try asking about skills, courses, careers, or roadmaps.'

CHAT_SYSTEM_PROMPT = (
    "You are the Career Assistant inside CareerRoadmap AI, a career-guidance web app. "
    "Give concise, practical, encouraging answers (2-5 sentences, occasional bullet points) "
    "about career paths, skills to learn, courses, interview prep, and resumes. "
    "If asked something totally unrelated to careers/learning, gently redirect. "
    "Do not invent specific company job openings or guarantee salaries/outcomes."
)

@app.route('/api/chat', methods=['POST'])
@login_required
@limiter.limit('30 per minute')
def chat():
    data = request.get_json(silent=True) or {}
    raw_message = (data.get('message') or '').strip()
    user_message = raw_message.lower()

    if not raw_message:
        return jsonify({'response': 'Please ask me something!'})

    # Keep messages bounded so a user can't send a huge payload to the LLM.
    if len(raw_message) > 1000:
        return jsonify({'response': 'That message is a bit long - could you shorten it?'})

    if anthropic_client:
        try:
            profile = current_user.profile
            profile_context = ''
            if profile:
                profile_context = (
                    f"User's profile - skills: {profile.skills or 'unknown'}; "
                    f"career goal: {profile.career_goal or 'unknown'}; "
                    f"interests: {profile.interests or 'unknown'}."
                )
            completion = anthropic_client.messages.create(
                model='claude-sonnet-4-6',
                max_tokens=400,
                system=CHAT_SYSTEM_PROMPT + (' ' + profile_context if profile_context else ''),
                messages=[{'role': 'user', 'content': raw_message}]
            )
            text = ''.join(block.text for block in completion.content if block.type == 'text').strip()
            if text:
                return jsonify({'response': text})
        except Exception:
            logger.exception('Anthropic API call failed in /api/chat, falling back to rule-based response')

    return jsonify({'response': fallback_chat_response(user_message)})

@app.route('/admin')
@login_required
@admin_required
def admin():
    users = User.query.all()
    return render_template('admin.html', users=users)

@app.route('/add_resources')
@login_required
@admin_required
def add_resources():
    if LearningResource.query.count() == 0:
        resources = [
            ('Python for Data Science', 'Coursera', 'https://www.coursera.org/specializations/python-data-science', 'Data Science', 'Beginner', 'Free', 4.8, 'Python,Data Science'),
            ('Machine Learning A-Z', 'Udemy', 'https://www.udemy.com/course/machinelearning/', 'Data Science', 'Intermediate', 'Paid', 4.6, 'ML,Python'),
            ('Data Science Bootcamp', 'Kaggle', 'https://www.kaggle.com/learn', 'Data Science', 'Beginner', 'Free', 4.9, 'Kaggle,Data'),
            ('The Web Developer Bootcamp', 'Udemy', 'https://www.udemy.com/course/the-web-developer-bootcamp/', 'Web Development', 'Beginner', 'Paid', 4.7, 'Full Stack,JavaScript'),
            ('React - The Complete Guide', 'Udemy', 'https://www.udemy.com/course/react-the-complete-guide/', 'Web Development', 'Intermediate', 'Paid', 4.8, 'React,Frontend'),
            ('Cybersecurity Fundamentals', 'Coursera', 'https://www.coursera.org/learn/cybersecurity-fundamentals', 'Cybersecurity', 'Beginner', 'Free', 4.6, 'Security,Fundamentals'),
            ('AWS Solutions Architect', 'AWS Training', 'https://aws.amazon.com/training/', 'Cloud Computing', 'Intermediate', 'Paid', 4.8, 'AWS,Cloud'),
            ('freeCodeCamp', 'freeCodeCamp', 'https://www.freecodecamp.org/', 'General', 'Beginner', 'Free', 4.9, 'Web Dev,General'),
        ]
        for res in resources:
            resource = LearningResource(
                title=res[0],
                platform=res[1],
                url=res[2],
                category=res[3],
                difficulty=res[4],
                price=res[5],
                rating=res[6],
                tags=res[7]
            )
            db.session.add(resource)
        db.session.commit()
        flash('Sample resources added!', 'success')
    else:
        flash('Resources already exist.', 'info')
    return redirect(url_for('resources'))

# ------------------ ERROR HANDLERS ------------------

@app.errorhandler(404)
def not_found(e):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(e):
    logger.exception('Unhandled server error')
    return render_template('errors/500.html'), 500

# ------------------ SEED DATABASE ------------------

def seed_database():
    if Badge.query.count() == 0:
        badges = [
            Badge(name='First Steps', description='Complete your first course', icon='🎯', points=10, category='Learning'),
            Badge(name='Course Master', description='Complete 5 courses', icon='🏆', points=50, category='Learning'),
            Badge(name='Roadmap Creator', description='Create your first career roadmap', icon='🗺️', points=20, category='Planning'),
            Badge(name='Goal Achiever', description='Achieve your first goal', icon='⭐', points=30, category='Goals'),
        ]
        for badge in badges:
            db.session.add(badge)
    
    if CareerTrend.query.count() == 0:
        trends = [
            CareerTrend(job_title='Data Scientist', industry='Technology', demand_score=95, 
                       avg_salary='$120,000', growth_rate='15%', 
                       required_skills='Python, SQL, Machine Learning, Statistics'),
            CareerTrend(job_title='Full Stack Developer', industry='Technology', demand_score=92,
                       avg_salary='$110,000', growth_rate='12%',
                       required_skills='JavaScript, React, Node.js, Python, SQL'),
            CareerTrend(job_title='Cybersecurity Analyst', industry='Security', demand_score=88,
                       avg_salary='$105,000', growth_rate='18%',
                       required_skills='Network Security, Ethical Hacking, Python'),
            CareerTrend(job_title='Cloud Architect', industry='Technology', demand_score=90,
                       avg_salary='$130,000', growth_rate='20%',
                       required_skills='AWS, Azure, Docker, Kubernetes'),
        ]
        for trend in trends:
            db.session.add(trend)
    
    db.session.commit()

# ------------------ RUN APP ------------------

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_database()
    # This block is for local development only. In production, run with
    # gunicorn (see wsgi.py / Dockerfile) - never with the Flask dev server.
    app.run(
        debug=not IS_PRODUCTION,
        host=os.environ.get('HOST', '127.0.0.1'),
        port=int(os.environ.get('PORT', 5000))
    )
else:
    # Imported by a WSGI server (gunicorn etc.) - make sure tables/seed data exist.
    with app.app_context():
        db.create_all()
        seed_database()