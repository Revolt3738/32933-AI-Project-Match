# mypy: ignore-errors
# type: ignore
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
import json
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', f'sqlite:///{os.path.abspath("instance/test.db")}')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configure OpenAI
api_key = os.getenv('DEEPSEEK_API_KEY')
print(f"API Key configured: {'Yes' if api_key else 'No'}")
client = OpenAI(
    api_key=api_key,
    base_url="https://api.deepseek.com/v1"
)

# Available project fields
AVAILABLE_FIELDS = ['Healthcare', 'Blockchain', 'Artificial Intelligence', 'IoT', 'Big Data', 'Cloud Computing', 'Cybersecurity']

def call_deepseek_api(messages):
    """Call DeepSeek API for conversation"""
    try:
        print("\n" + "="*50)
        print("Starting DeepSeek API call")
        print(f"Request messages: {json.dumps(messages, ensure_ascii=False, indent=2)}")
        print("-"*50)
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=0.3,
            max_tokens=1000,
            top_p=0.9,
            frequency_penalty=0.0,
            presence_penalty=0.0,
            stream=False,
            response_format={"type": "json_object"}  # Force JSON format return
        )
        # New API response format
        if response.choices and len(response.choices) > 0:
            content = response.choices[0].message.content
            print(f"API response: {content}")
            print("="*50 + "\n")
            return content
        else:
            print("API response format error")
            print("="*50 + "\n")
            return None
    except Exception as e:
        print(f"API call error: {str(e)}")
        print("="*50 + "\n")
        return None

def analyze_user_requirements(user_input):
    """Analyze user requirements, extract keywords and fields"""
    print(f"\nStarting user requirement analysis: {user_input}")
    
    messages = [
        {
            "role": "system",
            "content": """#### Role
- AI Assistant Name: Project Requirements Analysis Expert
- Main Task: Analyze student project requirements, extract key information (including fields, technical keywords, project features, and required skills) and match to predefined project domains

#### Capabilities
- Requirement Analysis: Accurately understand student project interests and requirements
- Domain Matching: Precisely match requirements to predefined project domains
- Keyword Extraction: Identify technical keywords from requirements
- Feature Summarization: Extract specific project feature requirements mentioned by users
- Skill Identification: Identify programming languages, frameworks, tools mentioned or implied by users

#### Knowledge Base
- Project Domains:
  - Healthcare
  - Blockchain
  - Artificial Intelligence
  - IoT
  - Big Data
  - Cloud Computing
  - Cybersecurity
- Common Skills Examples (not limited to): Python, JavaScript, Java, C++, SQL, React, Angular, Vue, Node.js, Django, Flask, Spring, Machine Learning, Deep Learning, Data Analysis, AWS, Azure, Docker, Kubernetes, Git

#### Output Format
Must output valid JSON format:
{
    "fields": ["Field1"],  // Array, 1-2 most relevant domains
    "keywords": ["Keyword1", "Keyword2"],  // Array, max 3 keywords
    "features": ["Feature1"],  // Array, specific feature requirements mentioned by user
    "skills": ["Skill1", "Skill2"] // Array, skills mentioned or implied by user, empty array [] if none
}

#### Matching Rules
1. Fields: Must select from predefined domains
2. Keywords: Prioritize technology-related terms
3. Features: Only extract explicitly stated requirements
4. Skills: Identify directly mentioned programming languages, software, tools, or reasonably inferred skills from project descriptions."""
        },
        {
            "role": "user",
            "content": user_input
        }
    ]
    
    print("Calling DeepSeek API for requirement analysis...")
    response = call_deepseek_api(messages)
    if not response:
        print("API call failed, returning None")
        return None
        
    try:
        result = json.loads(response)
        print(f"Requirement analysis result: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
        # Check if result is empty AND user input seems generic
        is_result_empty = not (result.get('fields') or result.get('keywords') or result.get('features') or result.get('skills'))
        is_input_generic = any(keyword in user_input for keyword in ['what projects', 'show projects', 'all projects', 'view projects', 'project recommendations'])
        
        if is_result_empty and is_input_generic:
            print("AI failed to extract specific requirements, and user input seems like generic query, returning None")
            return None
            
        return result
    except Exception as e:
        print(f"Requirement analysis failed: {str(e)}")
        print(f"API response content: {response}")
        return None

def rank_projects(requirements, projects):
    """Rank projects based on user requirements"""
    print(f"\nStarting project ranking...")
    # Ensure requirements is a dict, even if some keys are missing
    req_data = requirements if isinstance(requirements, dict) else {}
    print(f"User requirements: {json.dumps(req_data, ensure_ascii=False)}")
    print(f"Available projects: {[{'id': p.id, 'name': p.name, 'field': p.field, 'skills': p.skill_requirements} for p in projects]}")
    
    # If no requirements (or fields, keywords, skills are all empty), return all projects
    if not req_data or (not req_data.get('fields') and not req_data.get('keywords') and not req_data.get('skills')):
        print("No specific requirements (fields, keywords, skills all empty), returning all projects")
        return projects
    
    messages = [
        {
            "role": "system",
            "content": """#### Role
- AI Assistant Name: Project Matching Expert
- Main Task: Score and rank projects based on student requirements (including fields, keywords, features, and skills)

#### Capabilities
- Requirement Understanding: Understand student field interests, technical keywords, project features, and skill preferences
- Project Analysis: Analyze project descriptions, features, and skill requirements
- Relevance Scoring: Calculate matching degree between projects and requirements

#### Scoring Rules
Total 10 points, composed of four parts:
1. Field Matching (0-4 points):
   - Perfect match: 4 points
   - Related field: 2 points
   - Unrelated: 0 points

2. Keyword Matching (0-2 points):
   - Each keyword perfect match: 1 point
   - Each keyword related match: 0.5 points

3. Feature Matching (0-2 points):
   - Fully satisfies features: 2 points
   - Partially satisfies: 1 point
   - Does not satisfy: 0 points

4. Skill Matching (0-2 points):
   - Project required skills highly overlap with student skills: 2 points
   - Partial overlap or related: 1 point
   - Completely unmatched or student has no relevant skills: 0 points

#### Output Format
Must output valid JSON format:
{
    "ranked_projects": [
        {
            "id": ProjectID,
            "score": Score, // 0-10 points
            "reasoning": "Scoring rationale, brief explanation of each part's score"
        }
    ]
}

#### Notes
- If student provides no skills, skill matching part gets 0 points.
- If project lists no skill requirements, skill matching part is also considered 0 points, unless student skills highly relate to technologies in project description."""
        },
        {
            "role": "user",
            "content": f"""Student Requirements: {json.dumps(req_data, ensure_ascii=False)}
Project List: {json.dumps([{'id': p.id, 'name': p.name, 'description': p.description, 'field': p.field, 'skill_requirements': p.skill_requirements or ''} for p in projects], ensure_ascii=False)}"""
        }
    ]
    
    print("Calling DeepSeek API for project matching...")
    response = call_deepseek_api(messages)
    if not response:
        print("API call failed, returning all projects")
        return projects
        
    try:
        result = json.loads(response)
        print(f"Project matching result: {json.dumps(result, ensure_ascii=False, indent=2)}")
        # Adjust threshold based on new total score, e.g., projects with matching score >= 3 or 4
        ranked_ids = [item['id'] for item in result['ranked_projects'] if item.get('score', 0) >= 3] # Threshold adjustable
        if not ranked_ids:
            print("No projects found with sufficient matching score, returning all projects")
            return projects  # If no matching projects, return all projects
        matched_projects = sorted(
            [p for p in projects if p.id in ranked_ids],
            key=lambda p: ranked_ids.index(p.id)
        )
        print(f"Matched projects: {[p.name for p in matched_projects]}")
        return matched_projects
    except Exception as e:
        print(f"Error in project matching process: {str(e)}")
        print(f"API response content: {response}")
        return projects  # If error occurs, return all projects

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'default_login'  # type: ignore

# 数据库模型
class User(UserMixin, db.Model):  # type: ignore
    id = db.Column(db.Integer, primary_key=True)  # type: ignore
    email = db.Column(db.String(120), unique=True, nullable=False)  # type: ignore
    password_hash = db.Column(db.String(128))  # type: ignore
    is_teacher = db.Column(db.Boolean, default=False)  # type: ignore
    projects = db.relationship('Project', backref='teacher', lazy=True)  # type: ignore

class Project(db.Model):  # type: ignore
    id = db.Column(db.Integer, primary_key=True)  # type: ignore
    name = db.Column(db.String(100), nullable=False)  # type: ignore
    description = db.Column(db.Text, nullable=False)  # type: ignore
    field = db.Column(db.String(50), nullable=False)  # type: ignore
    skill_requirements = db.Column(db.Text, nullable=True)  # type: ignore
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # type: ignore
    interested_students = db.relationship('StudentInterest', backref='project', lazy=True)  # type: ignore

class StudentInterest(db.Model):  # type: ignore
    id = db.Column(db.Integer, primary_key=True)  # type: ignore
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # type: ignore
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)  # type: ignore
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)  # type: ignore

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.context_processor
def utility_processor():
    def get_user(user_id):
        return User.query.get(user_id)
    return dict(get_user=get_user)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def default_login():
    # Default redirect to student login page
    return redirect(url_for('login', role='student'))

@app.route('/login/<role>', methods=['GET', 'POST'])
def login(role):
    print(f"Login route accessed - Method: {request.method}, Role: {role}")
    
    if request.method == 'POST':
        print(f"Login form data: {request.form}")
        
        email = request.form.get('email')
        password = request.form.get('password')
        
        print(f"Login attempt - Email: {email}, Role: {role}, Password provided: {'Yes' if password else 'No'}")
        
        user = User.query.filter_by(email=email).first()
        print(f"User exists: {'Yes' if user else 'No'}")
        
        if user and password and check_password_hash(user.password_hash, password):
            print(f"Password verification passed")
            
            # Verify user role
            if (role == 'teacher' and not user.is_teacher) or (role == 'student' and user.is_teacher):
                print(f"Role mismatch - User is teacher: {user.is_teacher}, Requested role: {role}")
                flash('Not authorized to login with this role.')
                return redirect(url_for('login', role=role))
            
            login_user(user)
            print(f"Login successful - User is teacher: {user.is_teacher}")
            
            if user.is_teacher:
                print(f"Redirecting to teacher dashboard")
                return redirect(url_for('teacher_dashboard'))
            else:
                print(f"Redirecting to student dashboard")
                return redirect(url_for('student_dashboard'))
        else:
            print(f"Password verification failed or user not found")
            flash('Incorrect email or password.')
            
    return render_template('login.html', role=role)

@app.route('/teacher/dashboard')
@login_required
def teacher_dashboard():
    if not current_user.is_teacher:
        flash('Unauthorized access.')
        return redirect(url_for('student_dashboard'))
    projects = Project.query.filter_by(teacher_id=current_user.id).all()
    return render_template('teacher_dashboard.html', projects=projects)

@app.route('/student/dashboard')
@login_required
def student_dashboard():
    if current_user.is_teacher:
        flash('Unauthorized access.')
        return redirect(url_for('teacher_dashboard'))
    
    # Get student's selected projects
    interests = StudentInterest.query.filter_by(student_id=current_user.id).all()
    return render_template('student_dashboard.html', interests=interests)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/api/chat', methods=['POST', 'GET'])
@login_required
def chat():
    if current_user.is_teacher:
        return jsonify({'error': 'Unauthorized'}), 403
    
    if request.method == 'POST':
        # Safely get JSON data
        json_data = request.get_json()
        if not json_data:
            return jsonify({'error': 'Invalid JSON data'}), 400
            
        user_input = json_data.get('message')
        print(f"\nUser input: {user_input}")
        
        requirements = analyze_user_requirements(user_input)
        print(f"Requirement analysis result: {json.dumps(requirements, ensure_ascii=False)}")
        
        projects = Project.query.all()
        print(f"Projects in database: {[p.name for p in projects]}")
        
        ranked_projects = rank_projects(requirements, projects)
        print(f"Matched projects: {[p.name for p in ranked_projects]}")
        
        return jsonify({
            'projects': [{
                'id': p.id,
                'name': p.name,
                'description': p.description,
                'field': p.field,
                'skill_requirements': p.skill_requirements or '',
                'teacher_email': User.query.get(p.teacher_id).email  # type: ignore
            } for p in ranked_projects]
        })
    else:
        return jsonify({'message': 'Only POST method is supported'}), 405

@app.route('/api/project/interest', methods=['POST'])
@login_required
def express_interest():
    if current_user.is_teacher:
        return jsonify({'error': 'Unauthorized'}), 403
    
    json_data = request.get_json()
    if not json_data:
        return jsonify({'error': 'Invalid JSON data'}), 400
        
    project_id = json_data.get('project_id')
    if not project_id:
        return jsonify({'error': 'Project ID is required'}), 400
    
    existing_interest = StudentInterest.query.filter_by(
        student_id=current_user.id
    ).first()
    
    if existing_interest:
        return jsonify({'error': 'You have already expressed interest in a project'}), 400
    
    interest = StudentInterest(student_id=current_user.id, project_id=project_id)  # type: ignore
    db.session.add(interest)  # type: ignore
    db.session.commit()  # type: ignore
    
    return jsonify({'message': 'Interest recorded successfully'})

@app.route('/create_project', methods=['GET', 'POST'])
@login_required
def create_project():
    if not current_user.is_teacher:
        flash('Only teachers can create projects.')
        return redirect(url_for('index'))

    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        field = request.form.get('field')
        skill_requirements = request.form.get('skill_requirements', '') # Get skill_requirements
        
        if not all([name, description, field]): # Skill requirements can be optional
            flash('Project Name, Description, and Field are required.') # Updated flash message
            return redirect(url_for('create_project'))
            
        project = Project(  # type: ignore
            name=name,
            description=description,
            field=field,
            skill_requirements=skill_requirements, # Save skill_requirements
            teacher_id=current_user.id
        )
        db.session.add(project)  # type: ignore
        db.session.commit()  # type: ignore
        
        flash('Project created successfully!')
        return redirect(url_for('teacher_dashboard'))
        
    return render_template('create_project.html')

@app.route('/api/projects', methods=['POST'])
@login_required
def api_create_project(): # This is used by the modal in teacher_dashboard
    if not current_user.is_teacher:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid JSON data'}), 400
        
    name = data.get('name')
    description = data.get('description')
    field = data.get('field')
    skill_requirements = data.get('skill_requirements', '')

    if not all([name, description, field]):
        return jsonify({'error': 'Project Name, Description, and Field are required.'}), 400

    project = Project(  # type: ignore
        name=name,
        description=description,
        field=field,
        skill_requirements=skill_requirements,
        teacher_id=current_user.id
    )
    db.session.add(project)  # type: ignore
    db.session.commit()  # type: ignore
    
    return jsonify({
        'id': project.id,
        'name': project.name,
        'description': project.description,
        'field': project.field,
        'skill_requirements': project.skill_requirements
    }), 201 # Return 201 Created status

@app.route('/edit_project/<int:project_id>', methods=['GET', 'POST'])
@login_required
def edit_project(project_id):
    if not current_user.is_teacher:
        return redirect(url_for('student_dashboard'))
        
    project = Project.query.get_or_404(project_id)
    if project.teacher_id != current_user.id:
        flash('You do not have permission to edit this project.')
        return redirect(url_for('teacher_dashboard'))
        
    if request.method == 'POST':
        project.name = request.form['name']
        project.description = request.form['description']
        project.field = request.form['field']
        project.skill_requirements = request.form.get('skill_requirements', '') # Get and update skill_requirements
        
        # Validate required fields again (name, description, field)
        if not all([project.name, project.description, project.field]):
            flash('Project Name, Description, and Field are required.')
            # Pass project object back to template to repopulate form
            return render_template('edit_project.html', project=project) 

        db.session.commit()  # type: ignore
        flash('Project updated successfully!')
        return redirect(url_for('teacher_dashboard'))
        
    return render_template('edit_project.html', project=project)

@app.route('/student_interest/<int:project_id>', methods=['POST'])
@login_required
def student_interest(project_id):
    if current_user.is_teacher:
        return jsonify({'error': 'Teachers cannot express interest'}), 403
        
    # Check if student has already selected another project
    existing_interest = StudentInterest.query.filter_by(student_id=current_user.id).first()
    if existing_interest:
        if existing_interest.project_id == project_id:
            return jsonify({'message': 'You have already selected this project.'}), 400
        else:
            return jsonify({'message': 'You have already selected another project. Please cancel your previous selection first.'}), 400
            
    interest = StudentInterest(student_id=current_user.id, project_id=project_id)  # type: ignore
    db.session.add(interest)  # type: ignore
    db.session.commit()  # type: ignore
    return jsonify({'message': 'Interest expressed successfully!'})

@app.route('/cancel_interest/<int:project_id>', methods=['GET', 'POST'])
@login_required
def cancel_interest(project_id):
    if current_user.is_teacher:
        flash('Operation not permitted.')
        return redirect(url_for('teacher_dashboard'))
        
    interest = StudentInterest.query.filter_by(
        student_id=current_user.id,
        project_id=project_id
    ).first_or_404()
    
    db.session.delete(interest)  # type: ignore
    db.session.commit()  # type: ignore
    
    if request.method == 'GET':
        flash('Project selection cancelled successfully.')
        return redirect(url_for('student_dashboard'))
    
    return jsonify({'message': 'Selection cancelled.'})

def init_db():
    with app.app_context():
        # Drop all tables and recreate
        db.drop_all()
        db.create_all()
        
        # Create test accounts
        teacher = User(**{  # type: ignore
            'email': 'teacher@test.com',
            'password_hash': generate_password_hash('teacher123'),
            'is_teacher': True
        })
        db.session.add(teacher)  # type: ignore
        db.session.commit()  # type: ignore
        
        # Add test projects
        projects = [
            {
                'name': 'AI Image Recognition Project',
                'description': 'Medical image analysis using deep learning and computer vision technologies, including X-ray analysis and lesion detection. The project will use PyTorch framework and develop interactive visualization interfaces to display analysis results.',
                'field': 'Healthcare',
                'skill_requirements': 'Python, PyTorch, Computer Vision, Deep Learning'
            },
            {
                'name': 'Smart Medical Diagnosis Assistant',
                'description': 'Intelligent consultation system based on natural language processing and machine learning, capable of understanding patient descriptions and providing preliminary diagnostic recommendations. The project uses BERT model to process medical text data.',
                'field': 'Healthcare',
                'skill_requirements': 'Python, NLP, Machine Learning, BERT'
            },
            {
                'name': 'Blockchain Medical Data System',
                'description': 'Build a secure and transparent medical data sharing platform using blockchain technology to ensure patient data privacy and security. Includes smart contract development and web interface implementation.',
                'field': 'Healthcare',
                'skill_requirements': 'Blockchain, Solidity, Smart Contracts, Web Development'
            },
            {
                'name': 'Blockchain Application Development',
                'description': 'Develop Ethereum-based decentralized applications, implementing smart contract deployment and invocation. The project includes DApp frontend development and smart contract programming.',
                'field': 'Blockchain',
                'skill_requirements': 'Ethereum, Solidity, Web3.js, JavaScript, DApp Development'
            },
            {
                'name': 'Smart Home Control System',
                'description': 'IoT-based smart home control system enabling remote control, automation scenarios, and voice interaction. Uses MQTT protocol and ESP32 development board to create a complete smart home solution.',
                'field': 'IoT',
                'skill_requirements': 'IoT, MQTT, ESP32, C++, Embedded Systems'
            },
            {
                'name': 'Network Security Vulnerability Detection Platform',
                'description': 'Automated network security vulnerability scanning and detection platform capable of security assessment and risk analysis for enterprise internal networks. Uses Python and open-source security tools to build a complete security testing framework.',
                'field': 'Cybersecurity',
                'skill_requirements': 'Python, Cybersecurity, Network Scanning, Linux'
            },
            {
                'name': 'Big Data Analysis and Visualization Platform',
                'description': 'Enterprise-level big data processing and analysis platform providing intuitive data visualization interface and predictive analysis functions. Uses Hadoop ecosystem and D3.js visualization library to implement data storage, processing, and display.',
                'field': 'Big Data',
                'skill_requirements': 'Big Data, Hadoop, Spark, D3.js, Data Visualization, Python'
            }
        ]
        
        for p_data in projects:  # Renamed loop variable to avoid conflict
            project = Project(  # type: ignore
                name=p_data['name'],
                description=p_data['description'],
                field=p_data['field'],
                skill_requirements=p_data.get('skill_requirements', ''),  # Add skill requirements
                teacher_id=teacher.id
            )
            db.session.add(project)  # type: ignore
        
        student = User(**{  # type: ignore
            'email': 'student@test.com',
            'password_hash': generate_password_hash('student123'),
            'is_teacher': False
        })
        db.session.add(student)  # type: ignore
        
        db.session.commit()  # type: ignore
        print("Database initialized successfully!")

if __name__ == '__main__':
    init_db()  # Reinitialize database on each startup
    app.run(debug=True)
