from flask import Flask, render_template, request, session, redirect, url_for, jsonify
import sqlite3
import hashlib
import json
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key_123456789'

# Database connection
def get_db():
    conn = sqlite3.connect('career_roadmap.db')
    conn.row_factory = sqlite3.Row
    return conn

# Create tables
def init_db():
    db = get_db()
    c = db.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        email TEXT UNIQUE,
        password_hash TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Profiles table
    c.execute('''CREATE TABLE IF NOT EXISTS profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        skills TEXT,
        education TEXT,
        interests TEXT,
        career_goal TEXT,
        certifications TEXT,
        skill_levels TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Roadmaps table
    c.execute('''CREATE TABLE IF NOT EXISTS roadmaps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        career_title TEXT,
        roadmap_data TEXT,
        skill_gaps TEXT,
        matched_skills TEXT,
        timeline TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Learning Resources table
    c.execute('''CREATE TABLE IF NOT EXISTS learning_resources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        platform TEXT,
        url TEXT,
        category TEXT,
        difficulty TEXT,
        price TEXT,
        rating REAL,
        tags TEXT,
        image_url TEXT
    )''')
    
    # User Learning table
    c.execute('''CREATE TABLE IF NOT EXISTS user_learning (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        resource_id INTEGER,
        status TEXT,
        progress INTEGER DEFAULT 0,
        started_date TEXT,
        completed_date TEXT,
        notes TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # User Skills table
    c.execute('''CREATE TABLE IF NOT EXISTS user_skills (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        skill_name TEXT,
        level INTEGER DEFAULT 1,
        years_experience INTEGER DEFAULT 0,
        is_learning BOOLEAN DEFAULT 0
    )''')
    
    # Insert sample learning resources
    c.execute("SELECT COUNT(*) FROM learning_resources")
    count = c.fetchone()[0]
    
    if count == 0:
        resources = [
            # Data Science
            ('Python for Data Science', 'Coursera', 'https://www.coursera.org/specializations/python-data-science', 'Data Science', 'Beginner', 'Free', 4.8, 'Python,Data Science'),
            ('Machine Learning A-Z', 'Udemy', 'https://www.udemy.com/course/machinelearning/', 'Data Science', 'Intermediate', 'Paid', 4.6, 'ML,Python'),
            ('Data Science Bootcamp', 'Kaggle', 'https://www.kaggle.com/learn', 'Data Science', 'Beginner', 'Free', 4.9, 'Kaggle,Data'),
            ('Deep Learning Specialization', 'Coursera', 'https://www.coursera.org/specializations/deep-learning', 'Data Science', 'Advanced', 'Paid', 4.9, 'Deep Learning,AI'),
            ('Statistics for Data Science', 'YouTube', 'https://www.youtube.com/watch?v=xxc6', 'Data Science', 'Beginner', 'Free', 4.5, 'Statistics'),
            
            # Web Development
            ('The Web Developer Bootcamp', 'Udemy', 'https://www.udemy.com/course/the-web-developer-bootcamp/', 'Web Development', 'Beginner', 'Paid', 4.7, 'Full Stack,JavaScript'),
            ('React - The Complete Guide', 'Udemy', 'https://www.udemy.com/course/react-the-complete-guide/', 'Web Development', 'Intermediate', 'Paid', 4.8, 'React,Frontend'),
            ('Django for Beginners', 'YouTube', 'https://www.youtube.com/watch?v=rHux0gMZ3Eg', 'Web Development', 'Beginner', 'Free', 4.6, 'Django,Python'),
            ('HTML/CSS Crash Course', 'YouTube', 'https://www.youtube.com/watch?v=UB1O30fR-EE', 'Web Development', 'Beginner', 'Free', 4.8, 'HTML,CSS'),
            ('Full Stack Web Development', 'Coursera', 'https://www.coursera.org/professional-certificates/meta-frontend-developer', 'Web Development', 'Intermediate', 'Paid', 4.7, 'Full Stack'),
            
            # Cybersecurity
            ('Cybersecurity Fundamentals', 'Coursera', 'https://www.coursera.org/learn/cybersecurity-fundamentals', 'Cybersecurity', 'Beginner', 'Free', 4.6, 'Security,Fundamentals'),
            ('Ethical Hacking - Complete Course', 'Udemy', 'https://www.udemy.com/course/ethical-hacking/', 'Cybersecurity', 'Intermediate', 'Paid', 4.5, 'Hacking,Penetration'),
            ('CompTIA Security+', 'Cybrary', 'https://www.cybrary.it/course/comptia-security-plus/', 'Cybersecurity', 'Intermediate', 'Free', 4.7, 'Security,CompTIA'),
            ('Network Security', 'YouTube', 'https://www.youtube.com/watch?v=9Gc9I', 'Cybersecurity', 'Beginner', 'Free', 4.4, 'Networking'),
            
            # Cloud Computing
            ('AWS Solutions Architect', 'AWS Training', 'https://aws.amazon.com/training/', 'Cloud Computing', 'Intermediate', 'Paid', 4.8, 'AWS,Cloud'),
            ('Docker & Kubernetes', 'Udemy', 'https://www.udemy.com/course/docker-kubernetes/', 'Cloud Computing', 'Intermediate', 'Paid', 4.6, 'Docker,Kubernetes'),
            ('DevOps Bootcamp', 'Coursera', 'https://www.coursera.org/learn/devops', 'Cloud Computing', 'Intermediate', 'Free', 4.5, 'DevOps,CI/CD'),
            ('Google Cloud Engineer', 'Google Cloud', 'https://cloud.google.com/learn', 'Cloud Computing', 'Intermediate', 'Paid', 4.7, 'GCP,Cloud'),
            
            # Free Learning Platforms
            ('freeCodeCamp', 'freeCodeCamp', 'https://www.freecodecamp.org/', 'General', 'Beginner', 'Free', 4.9, 'Web Dev,General'),
            ('The Odin Project', 'The Odin Project', 'https://www.theodinproject.com/', 'General', 'Beginner', 'Free', 4.8, 'Full Stack,Open Source'),
            ('Codecademy', 'Codecademy', 'https://www.codecademy.com/', 'General', 'Beginner', 'Free', 4.6, 'Various'),
            ('W3Schools', 'W3Schools', 'https://www.w3schools.com/', 'General', 'Beginner', 'Free', 4.5, 'Web Dev,Reference'),
        ]
        
        for res in resources:
            c.execute("""INSERT INTO learning_resources 
                        (title, platform, url, category, difficulty, price, rating, tags) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", res)
    
    db.commit()
    db.close()

init_db()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_user_by_username(username):
    db = get_db()
    c = db.cursor()
    c.execute("SELECT id, username, email, password_hash FROM users WHERE username = ?", (username,))
    user = c.fetchone()
    db.close()
    return user

def get_user_profile(user_id):
    db = get_db()
    c = db.cursor()
    c.execute("SELECT * FROM profiles WHERE user_id = ?", (user_id,))
    profile = c.fetchone()
    db.close()
    return profile

def get_user_roadmap(user_id):
    db = get_db()
    c = db.cursor()
    c.execute("SELECT * FROM roadmaps WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,))
    roadmap = c.fetchone()
    db.close()
    return roadmap

def get_all_categories():
    db = get_db()
    c = db.cursor()
    c.execute("SELECT DISTINCT category FROM learning_resources")
    categories = [row['category'] for row in c.fetchall()]
    db.close()
    return categories

# AI Recommendation Engine
def generate_ai_roadmap(profile_data):
    skills = profile_data.get('skills', '').split(',') if profile_data.get('skills') else []
    interests = profile_data.get('interests', '').lower() if profile_data.get('interests') else ''
    
    career_paths = {
        'data_science': {
            'title': 'Data Scientist',
            'courses': ['Python', 'Statistics', 'Machine Learning', 'SQL', 'Data Visualization'],
            'projects': ['Sentiment Analysis', 'Recommendation System', 'Customer Churn'],
            'certifications': ['IBM Data Science', 'Google Analytics'],
            'timeline': '8-12 months'
        },
        'web_dev': {
            'title': 'Full Stack Developer',
            'courses': ['HTML/CSS', 'JavaScript', 'React', 'Node.js', 'Python/Django'],
            'projects': ['Portfolio Website', 'E-commerce App', 'Task Manager'],
            'certifications': ['Meta Frontend', 'AWS Cloud Practitioner'],
            'timeline': '6-8 months'
        },
        'cybersecurity': {
            'title': 'Cybersecurity Analyst',
            'courses': ['Network Security', 'Ethical Hacking', 'Cryptography', 'Python'],
            'projects': ['Vulnerability Scanner', 'Security Audit'],
            'certifications': ['CompTIA Security+', 'CEH'],
            'timeline': '10-14 months'
        }
    }
    
    selected_path = 'web_dev'
    if 'data' in interests or 'science' in interests:
        selected_path = 'data_science'
    elif 'security' in interests or 'cyber' in interests:
        selected_path = 'cybersecurity'
    
    roadmap = career_paths[selected_path]
    
    user_skills_lower = [s.strip().lower() for s in skills if s.strip()]
    required_skills = [s.lower() for s in roadmap['courses']]
    
    skill_gaps = [s for s in required_skills if s not in user_skills_lower]
    matched_skills = [s for s in required_skills if s in user_skills_lower]
    
    return {
        'career_title': roadmap['title'],
        'courses': roadmap['courses'],
        'projects': roadmap['projects'],
        'certifications': roadmap['certifications'],
        'skill_gaps': skill_gaps,
        'matched_skills': matched_skills,
        'timeline': roadmap['timeline']
    }

# ------------------ ROUTES ------------------
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = hash_password(request.form['password'])
        
        db = get_db()
        c = db.cursor()
        try:
            c.execute("INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                     (username, email, password))
            user_id = c.lastrowid
            
            c.execute("""INSERT INTO profiles (user_id, skills, education, interests, career_goal, certifications) 
                        VALUES (?, ?, ?, ?, ?, ?)""",
                     (user_id, 
                      request.form.get('skills', ''),
                      request.form.get('education', ''),
                      request.form.get('interests', ''),
                      request.form.get('career_goal', ''),
                      request.form.get('certifications', '')))
            db.commit()
            db.close()
            return redirect(url_for('login'))
        except:
            db.close()
            return render_template('register.html', error='Username or email already exists')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = hash_password(request.form['password'])
        
        db = get_db()
        c = db.cursor()
        c.execute("SELECT id, username FROM users WHERE username = ? AND password_hash = ?", (username, password))
        user = c.fetchone()
        db.close()
        
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error='Invalid credentials')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    db = get_db()
    c = db.cursor()
    c.execute("SELECT * FROM profiles WHERE user_id = ?", (session['user_id'],))
    profile = c.fetchone()
    
    c.execute("SELECT * FROM roadmaps WHERE user_id = ? ORDER BY id DESC LIMIT 1", (session['user_id'],))
    roadmap = c.fetchone()
    db.close()
    
    roadmap_data = None
    if roadmap:
        roadmap_data = {
            'career_title': roadmap['career_title']
        }
    
    return render_template('dashboard.html', 
                         username=session['username'],
                         profile=profile,
                         roadmap=roadmap_data)

@app.route('/generate_roadmap', methods=['POST'])
def generate_roadmap():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    skills = request.form.get('skills', '')
    education = request.form.get('education', '')
    interests = request.form.get('interests', '')
    career_goal = request.form.get('career_goal', '')
    certifications = request.form.get('certifications', '')
    
    db = get_db()
    c = db.cursor()
    c.execute("SELECT id FROM profiles WHERE user_id = ?", (session['user_id'],))
    existing = c.fetchone()
    
    if existing:
        c.execute("""UPDATE profiles 
                    SET skills = ?, education = ?, interests = ?, career_goal = ?, certifications = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?""",
                 (skills, education, interests, career_goal, certifications, session['user_id']))
    else:
        c.execute("""INSERT INTO profiles (user_id, skills, education, interests, career_goal, certifications) 
                    VALUES (?, ?, ?, ?, ?, ?)""",
                 (session['user_id'], skills, education, interests, career_goal, certifications))
    
    db.commit()
    
    profile_data = {
        'skills': skills,
        'education': education,
        'interests': interests,
        'career_goal': career_goal,
        'certifications': certifications
    }
    
    roadmap_result = generate_ai_roadmap(profile_data)
    
    c.execute("""INSERT INTO roadmaps (user_id, career_title, roadmap_data, skill_gaps, matched_skills, timeline)
                VALUES (?, ?, ?, ?, ?, ?)""",
             (session['user_id'], 
              roadmap_result['career_title'],
              json.dumps(roadmap_result),
              json.dumps(roadmap_result['skill_gaps']),
              json.dumps(roadmap_result['matched_skills']),
              roadmap_result['timeline']))
    db.commit()
    db.close()
    
    return redirect(url_for('roadmap_view'))

@app.route('/roadmap')
def roadmap_view():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    db = get_db()
    c = db.cursor()
    c.execute("SELECT * FROM roadmaps WHERE user_id = ? ORDER BY id DESC LIMIT 1", (session['user_id'],))
    roadmap = c.fetchone()
    db.close()
    
    if roadmap:
        roadmap_data = json.loads(roadmap['roadmap_data'])
    else:
        roadmap_data = {}
    
    return render_template('roadmap.html', roadmap=roadmap_data)

@app.route('/admin')
def admin():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    db = get_db()
    c = db.cursor()
    c.execute("SELECT * FROM users")
    users = c.fetchall()
    db.close()
    
    return render_template('admin.html', users=users)

# ------------------ LEARNING RESOURCES ROUTES ------------------
@app.route('/resources')
def resources():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    category = request.args.get('category', 'All')
    search = request.args.get('search', '')
    difficulty = request.args.get('difficulty', 'All')
    
    db = get_db()
    c = db.cursor()
    
    query = "SELECT * FROM learning_resources WHERE 1=1"
    params = []
    
    if category != 'All':
        query += " AND category = ?"
        params.append(category)
    
    if search:
        query += " AND (title LIKE ? OR tags LIKE ?)"
        params.append(f'%{search}%')
        params.append(f'%{search}%')
    
    if difficulty != 'All':
        query += " AND difficulty = ?"
        params.append(difficulty)
    
    query += " ORDER BY rating DESC"
    
    c.execute(query, params)
    resources = c.fetchall()
    
    c.execute("SELECT resource_id, status, progress FROM user_learning WHERE user_id = ?", (session['user_id'],))
    user_learning = c.fetchall()
    user_learning_dict = {r['resource_id']: r for r in user_learning}
    
    db.close()
    
    categories = get_all_categories()
    
    return render_template('resources.html', 
                         resources=resources,
                         categories=categories,
                         user_learning=user_learning_dict,
                         selected_category=category,
                         search_query=search,
                         selected_difficulty=difficulty)

@app.route('/add_learning', methods=['POST'])
def add_learning():
    if 'user_id' not in session:
        return jsonify({'error': 'Please login'}), 401
    
    data = request.get_json()
    resource_id = data.get('resource_id')
    status = data.get('status', 'not_started')
    
    db = get_db()
    c = db.cursor()
    
    c.execute("SELECT id FROM user_learning WHERE user_id = ? AND resource_id = ?", 
             (session['user_id'], resource_id))
    existing = c.fetchone()
    
    if existing:
        c.execute("""UPDATE user_learning 
                    SET status = ?, updated_at = CURRENT_TIMESTAMP 
                    WHERE user_id = ? AND resource_id = ?""",
                 (status, session['user_id'], resource_id))
    else:
        c.execute("""INSERT INTO user_learning (user_id, resource_id, status, progress) 
                    VALUES (?, ?, ?, ?)""",
                 (session['user_id'], resource_id, status, 0))
    
    db.commit()
    db.close()
    
    return jsonify({'message': 'Learning status updated!'})

@app.route('/update_progress', methods=['POST'])
def update_progress():
    if 'user_id' not in session:
        return jsonify({'error': 'Please login'}), 401
    
    data = request.get_json()
    resource_id = data.get('resource_id')
    progress = data.get('progress', 0)
    
    db = get_db()
    c = db.cursor()
    
    status = 'in_progress'
    if progress >= 100:
        status = 'completed'
    
    c.execute("""UPDATE user_learning 
                SET progress = ?, status = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE user_id = ? AND resource_id = ?""",
             (progress, status, session['user_id'], resource_id))
    db.commit()
    db.close()
    
    return jsonify({'message': 'Progress updated!', 'status': status})

@app.route('/dashboard_stats')
def dashboard_stats():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    db = get_db()
    c = db.cursor()
    
    c.execute("""SELECT COUNT(*) as total, 
                        SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                        SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END) as in_progress
                FROM user_learning WHERE user_id = ?""", (session['user_id'],))
    stats = c.fetchone()
    
    db.close()
    
    return jsonify({
        'total_courses': stats['total'] if stats else 0,
        'completed_courses': stats['completed'] if stats else 0,
        'in_progress_courses': stats['in_progress'] if stats else 0
    })

@app.route('/recommendations')
def recommendations():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    db = get_db()
    c = db.cursor()
    c.execute("SELECT interests FROM profiles WHERE user_id = ?", (session['user_id'],))
    profile = c.fetchone()
    db.close()
    
    interests = profile['interests'].lower() if profile and profile['interests'] else ''
    
    db = get_db()
    c = db.cursor()
    
    if interests:
        interest_keywords = [k.strip() for k in interests.split(',') if len(k.strip()) > 2]
        query = "SELECT * FROM learning_resources WHERE "
        conditions = []
        for keyword in interest_keywords:
            conditions.append(f"tags LIKE '%{keyword}%' OR category LIKE '%{keyword}%'")
        query += " OR ".join(conditions) if conditions else "1=1"
        query += " ORDER BY rating DESC LIMIT 10"
        c.execute(query)
        recommendations = c.fetchall()
    else:
        c.execute("SELECT * FROM learning_resources ORDER BY rating DESC LIMIT 10")
        recommendations = c.fetchall()
    
    db.close()
    
    return render_template('recommendations.html', recommendations=recommendations)
# ------------------ CHATBOT ROUTES ------------------

@app.route('/chatbot')
def chatbot():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('chatbot.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    if 'user_id' not in session:
        return jsonify({'error': 'Please login first'}), 401
    
    data = request.get_json()
    user_message = data.get('message', '').lower().strip()
    
    if not user_message:
        return jsonify({'response': 'Please ask me something!'})
    
    # Get user profile for personalized responses
    db = get_db()
    c = db.cursor()
    c.execute("SELECT skills, interests, career_goal FROM profiles WHERE user_id = ?", (session['user_id'],))
    profile = c.fetchone()
    db.close()
    
    user_skills = profile['skills'] if profile and profile['skills'] else ''
    user_interests = profile['interests'] if profile and profile['interests'] else ''
    user_goal = profile['career_goal'] if profile and profile['career_goal'] else ''
    
    # ------------------ CHATBOT INTELLIGENCE ------------------
    response = ""
    
    # 1. GREETINGS
    if any(word in user_message for word in ['hi', 'hello', 'hey', 'greetings', 'good morning', 'good evening']):
        response = f"""👋 Hello! I'm your AI Career Assistant!

I can help you with:
• 📚 **Career Guidance** - Find the right career path
• 🎓 **Learning Resources** - Recommended courses and platforms
• 💡 **Skill Development** - Identify skill gaps and improvements
• 🗺️ **Roadmap Planning** - Create personalized career roadmaps
• 📊 **Progress Tracking** - Monitor your learning journey

What would you like to know about your career today?"""

    # 2. ABOUT THE USER
    elif 'who am i' in user_message or 'my profile' in user_message or 'tell me about myself' in user_message:
        if profile:
            response = f"""📋 **Your Profile Summary:**

👤 **Username:** {session['username']}
🛠️ **Skills:** {user_skills if user_skills else 'Not added yet'}
🎯 **Interests:** {user_interests if user_interests else 'Not added yet'}
🚀 **Career Goal:** {user_goal if user_goal else 'Not added yet'}

💡 **Tip:** Go to your Dashboard to update your profile for better recommendations!"""
        else:
            response = "📋 You haven't set up your profile yet. Go to your Dashboard and add your skills, interests, and career goals!"

    # 3. ROADMAP HELP
    elif 'roadmap' in user_message or 'career path' in user_message or 'how to become' in user_message:
        response = """🗺️ **Career Roadmap Guide**

To create your personalized roadmap:
1. Go to your **Dashboard**
2. Fill in your **skills**, **interests**, and **career goal**
3. Click **"Generate AI Roadmap"**
4. Get a complete plan with:
   - Recommended courses
   - Suggested projects
   - Certifications to pursue
   - Timeline estimate

**Popular Career Paths:**
• Data Scientist → Python, ML, Statistics, SQL
• Web Developer → HTML/CSS, JavaScript, React, Node.js
• Cybersecurity Analyst → Network Security, Ethical Hacking
• Cloud Engineer → AWS, Docker, Kubernetes, DevOps

Which career path interests you? I can give you more details!"""

    # 4. SKILLS HELP
    elif 'skill' in user_message or 'learn' in user_message or 'course' in user_message:
        response = """📚 **Learning & Skills Guide**

**Top Skills in Demand (2026):**
💻 **Programming:** Python, JavaScript, Java, C++
☁️ **Cloud:** AWS, Azure, GCP, Docker, Kubernetes
🤖 **AI/ML:** TensorFlow, PyTorch, NLP, Computer Vision
🔐 **Security:** Ethical Hacking, Cryptography, Network Security
📊 **Data:** SQL, Tableau, Power BI, Excel

**Best Learning Platforms:**
• 🎓 **Coursera** - University courses
• 📺 **YouTube** - Free tutorials
• 🏫 **Udemy** - Affordable courses
• 💻 **freeCodeCamp** - Free coding bootcamp
• 📖 **The Odin Project** - Full stack curriculum

**Want to know about a specific skill? Just ask!**"""

    # 5. JOB & CAREER HELP
    elif 'job' in user_message or 'career' in user_message or 'salary' in user_message:
        response = """💼 **Career & Job Information**

**Current Market Trends:**
• 📈 **Data Science** - High demand, avg salary: $120K+
• 🌐 **Web Development** - Always in demand, avg salary: $90K+
• 🔒 **Cybersecurity** - Growing rapidly, avg salary: $110K+
• ☁️ **Cloud Computing** - Hot market, avg salary: $130K+
• 🤖 **AI/ML Engineering** - Future proof, avg salary: $140K+

**Tips for Job Search:**
1. Build a strong GitHub portfolio
2. Get relevant certifications
3. Network on LinkedIn
4. Practice coding interviews
5. Apply to internships first

**What specific career are you interested in?**"""

    # 6. CHATBOT HELP
    elif 'help' in user_message or 'what can you do' in user_message:
        response = """🤖 **I can help you with:**

💬 **Career Advice**
• Ask about any career path
• Get skill recommendations
• Understand industry trends

📚 **Learning Resources**
• Find courses for any skill
• Get learning platform recommendations
• Track your learning progress

🗺️ **Roadmap Planning**
• Create personalized career roadmaps
• Identify skill gaps
• Get timeline estimates

📊 **Progress Tracking**
• Monitor your course completions
• Track skill development
• See your overall progress

**Just ask me anything about your career!**"""

    # 7. RESOURCES HELP
    elif 'resource' in user_message or 'course' in user_message or 'platform' in user_message:
        response = """📖 **Learning Resources Available**

**On This Website:**
• 🎓 **22+ curated courses** from top platforms
• 🏷️ **Categories:** Data Science, Web Dev, Cybersecurity, Cloud
• 💰 **Filter by:** Free/Paid, Difficulty, Platform
• 📊 **Track progress** for each course

**Popular Courses:**
• Python for Data Science (Coursera)
• The Web Developer Bootcamp (Udemy)
• Cybersecurity Fundamentals (Coursera)
• AWS Solutions Architect (AWS Training)

**Go to the Resources page to explore all courses!**"""

    # 8. PROGRESS HELP
    elif 'progress' in user_message or 'track' in user_message:
        response = """📊 **Track Your Progress**

**How to Track:**
1. Go to **Resources** page
2. Click **+** on any course to add it
3. Mark courses as **Completed** when done
4. View stats on your **Dashboard**

**Your Stats:**
• Total courses added
• Completed courses
• In-progress courses
• Overall progress percentage

**Keep learning and watch your progress grow! 🚀**"""

    # 9. MOTIVATION
    elif 'motivate' in user_message or 'inspire' in user_message or 'encourage' in user_message:
        responses = [
            "🌟 **Stay motivated!** Every expert was once a beginner. Keep learning, keep growing!",
            "💪 **You've got this!** Small steps every day lead to big achievements!",
            "🚀 **Your future is bright!** The skills you're learning today will shape your tomorrow!",
            "🎯 **Keep going!** Consistency beats intensity. You're doing great!",
            "🌈 **Believe in yourself!** You have the power to achieve anything you set your mind to!"
        ]
        import random
        response = random.choice(responses)

    # 10. DEFAULT - SMART RESPONSE
    else:
        # Check if message contains any career keywords
        career_keywords = {
            'python': 'Python is a versatile programming language used in web dev, data science, AI, and automation. Start with freeCodeCamp or Coursera!',
            'javascript': 'JavaScript is essential for web development. Learn React, Node.js, and modern JS frameworks. Try The Odin Project!',
            'data science': 'Data Science combines statistics, programming, and domain knowledge. Start with Python, SQL, and ML basics on Kaggle!',
            'web development': 'Web Development has two paths: Frontend (HTML/CSS/JS) and Backend (Python/Node.js). Both are in high demand!',
            'cybersecurity': 'Cybersecurity is critical for protecting systems. Start with CompTIA Security+ and learn ethical hacking!',
            'cloud': 'Cloud computing is the future! Start with AWS, Azure, or GCP certifications. Docker and Kubernetes are also valuable!',
            'ai': 'Artificial Intelligence is transforming every industry. Learn ML, Deep Learning, and NLP. Start with Coursera\'s Deep Learning specialization!',
            'interview': 'For interviews: practice coding problems, study system design, prepare behavioral answers, and research the company!',
            'resume': 'Create a strong resume: highlight projects, list relevant skills, include certifications, and quantify achievements!',
            'github': 'GitHub is essential for developers. Create projects, contribute to open source, and build your portfolio!',
            'linkedin': 'LinkedIn is the best platform for professional networking. Keep your profile updated and connect with industry professionals!'
        }
        
        matched = False
        for keyword, advice in career_keywords.items():
            if keyword in user_message:
                response = f"💡 **{keyword.title()} Advice:**\n\n{advice}\n\nWant more details or have another question?"
                matched = True
                break
        
        if not matched:
            response = """🤔 **I'm not sure about that specific topic.**

But I can help you with:
• Career paths and job roles
• Skills to learn for specific careers
• Recommended courses and platforms
• Roadmap planning
• Interview preparation
• Resume building

**Try asking:**
• "How to become a Data Scientist?"
• "What skills do I need for web development?"
• "How to learn Python?"
• "Give me career advice"

Or ask me anything about your career journey! 🚀"""
    
    return jsonify({'response': response, 'user_skills': user_skills, 'user_interests': user_interests})
if __name__ == '__main__':
    app.run(debug=True)