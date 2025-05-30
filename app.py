from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
import json
from datetime import datetime
from dotenv import load_dotenv
import openai

# 加载环境变量
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 配置 OpenAI
api_key = os.getenv('DEEPSEEK_API_KEY')
print(f"API Key 是否设置: {'是' if api_key else '否'}")
openai.api_key = api_key
openai.api_base = "https://api.deepseek.com/v1"

# 可用的项目领域
AVAILABLE_FIELDS = ['Medical and Healthy', 'Block Chain', 'AI', 'IOT', 'Big Data', 'Cloud Computing', 'Cyber Security']

def call_deepseek_api(messages):
    """调用DeepSeek API进行对话"""
    try:
        print("\n" + "="*50)
        print("开始调用 DeepSeek API")
        print(f"请求消息: {json.dumps(messages, ensure_ascii=False, indent=2)}")
        print("-"*50)
        
        response = openai.ChatCompletion.create(
            model="deepseek-chat",
            messages=messages,
            temperature=0.3,
            max_tokens=1000,
            top_p=0.9,
            frequency_penalty=0.0,
            presence_penalty=0.0,
            stream=False,
            response_format={"type": "json_object"}  # 强制返回 JSON 格式
        )
        content = response.choices[0].message.content
        print(f"API 响应: {content}")
        print("="*50 + "\n")
        return content
    except Exception as e:
        print(f"API 调用错误: {str(e)}")
        print("="*50 + "\n")
        return None

def analyze_user_requirements(user_input):
    """分析用户需求，提取关键字和领域"""
    print(f"\n开始分析用户需求: {user_input}")
    
    messages = [
        {
            "role": "system",
            "content": """#### 定位
- 智能助手名称：项目需求分析专家
- 主要任务：分析学生的项目需求，提取关键信息（包括领域、技术关键词、项目特点和所需技能）并匹配到预定义的项目领域

#### 能力
- 需求分析：能够准确理解学生表达的项目兴趣和需求
- 领域匹配：将需求精确匹配到预定义的项目领域
- 关键词提取：识别需求中的技术关键词
- 特点总结：提取用户明确表达的项目特点要求
- 技能识别：从用户描述中识别出他们拥有或希望使用的编程语言、框架、工具等技能

#### 知识储备
- 项目领域：
  - Medical and Healthy
  - Block Chain
  - AI
  - IOT
  - Big Data
  - Cloud Computing
  - Cyber Security
- 常见技能示例 (不限于此列表): Python, JavaScript, Java, C++, SQL, React, Angular, Vue, Node.js, Django, Flask, Spring, Machine Learning, Deep Learning, Data Analysis, AWS, Azure, Docker, Kubernetes, Git

#### 输出格式
必须输出合法的 JSON 格式：
{
    "fields": ["领域1"],  // 数组，1-2个最相关的领域
    "keywords": ["关键词1", "关键词2"],  // 数组，最多3个关键词
    "features": ["特点1"],  // 数组，用户明确提到的特点要求
    "skills": ["技能1", "技能2"] // 数组，用户提到或暗示的技能，如果未提及则为空数组 []
}

#### 匹配规则
1. 领域：必须从预定义领域中选择
2. 关键词：优先技术相关词汇
3. 特点：只提取用户明确表达的要求
4. 技能：识别用户直接提及的编程语言、软件、工具等技能，或从项目描述中合理推断的技能。如果用户说"我会编程"，可以尝试识别是否有更具体的编程语言被提及。"""
        },
        {
            "role": "user",
            "content": user_input
        }
    ]
    
    print("正在调用 DeepSeek API 进行需求分析...")
    response = call_deepseek_api(messages)
    if not response:
        print("API 调用失败，返回 None")
        return None
        
    try:
        result = json.loads(response)
        print(f"需求分析结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
        # Check if result is empty AND user input seems generic
        is_result_empty = not (result.get('fields') or result.get('keywords') or result.get('features') or result.get('skills'))
        is_input_generic = any(keyword in user_input for keyword in ['有什么项目', '有哪些项目', '所有项目', '查看项目', '项目推荐'])
        
        if is_result_empty and is_input_generic:
            print("AI未能提取具体需求，且用户输入像是通用查询，返回 None")
            return None
            
        return result
    except Exception as e:
        print(f"需求分析失败: {str(e)}")
        print(f"API 返回内容: {response}")
        return None

def rank_projects(requirements, projects):
    """根据用户需求对项目进行排序"""
    print(f"\n开始项目排序...")
    # Ensure requirements is a dict, even if some keys are missing
    req_data = requirements if isinstance(requirements, dict) else {}
    print(f"用户需求: {json.dumps(req_data, ensure_ascii=False)}")
    print(f"可用项目: {[{'id': p.id, 'name': p.name, 'field': p.field, 'skills': p.skill_requirements} for p in projects]}")
    
    # 如果没有要求 (或者没有 fields, keywords, skills 都为空), 返回所有项目
    if not req_data or (not req_data.get('fields') and not req_data.get('keywords') and not req_data.get('skills')):
        print("没有具体需求 (领域, 关键词, 技能均为空)，返回所有项目")
        return projects
    
    messages = [
        {
            "role": "system",
            "content": """#### 定位
- 智能助手名称：项目匹配专家
- 主要任务：根据学生需求（包括领域、关键词、特点和技能）对项目进行评分和排序

#### 能力
- 需求理解：理解学生的领域兴趣、技术关键词、项目特点和技能偏好
- 项目分析：分析项目描述、特点和技能要求
- 相关度评分：计算项目与需求的匹配程度

#### 评分规则
总分10分，由以下四部分组成：
1. 领域匹配（0-4分）：
   - 完全匹配：4分
   - 相关领域：2分
   - 无关：0分

2. 关键词匹配（0-2分）：
   - 每个关键词完全匹配：1分
   - 每个关键词相关词匹配：0.5分

3. 特点匹配（0-2分）：
   - 完全满足特点：2分
   - 部分满足：1分
   - 不满足：0分

4. 技能匹配（0-2分）：
   - 项目所需技能与学生技能高度重合：2分
   - 部分重合或相关：1分
   - 完全不符或学生无相关技能：0分

#### 输出格式
必须输出合法的 JSON 格式：
{
    "ranked_projects": [
        {
            "id": 项目ID,
            "score": 分数, // 0-10分
            "reasoning": "得分理由，简要说明各部分得分情况"
        }
    ]
}

#### 注意事项
- 如果学生未提供技能，则技能匹配部分得0分。
- 如果项目未列出技能要求，则技能匹配部分也视为0分，除非学生技能与项目描述中的技术高度相关。"""
        },
        {
            "role": "user",
            "content": f"""学生需求：{json.dumps(req_data, ensure_ascii=False)}
项目列表：{json.dumps([{'id': p.id, 'name': p.name, 'description': p.description, 'field': p.field, 'skill_requirements': p.skill_requirements or ''} for p in projects], ensure_ascii=False)}"""
        }
    ]
    
    print("正在调用 DeepSeek API 进行项目匹配...")
    response = call_deepseek_api(messages)
    if not response:
        print("API 调用失败，返回所有项目")
        return projects
        
    try:
        result = json.loads(response)
        print(f"项目匹配结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
        # 根据新的总分调整阈值，例如匹配度大于等于 3 或 4 分的项目
        ranked_ids = [item['id'] for item in result['ranked_projects'] if item.get('score', 0) >= 3] # 阈值可调整
        if not ranked_ids:
            print("没有找到匹配度足够高的项目，返回所有项目")
            return projects  # 如果没有匹配项目，返回所有项目
        matched_projects = sorted(
            [p for p in projects if p.id in ranked_ids],
            key=lambda p: ranked_ids.index(p.id)
        )
        print(f"匹配到的项目: {[p.name for p in matched_projects]}")
        return matched_projects
    except Exception as e:
        print(f"项目匹配过程出错: {str(e)}")
        print(f"API 返回内容: {response}")
        return projects  # 如果发生错误，返回所有项目

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'default_login'

# 数据库模型
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    is_teacher = db.Column(db.Boolean, default=False)
    quota = db.Column(db.Integer, nullable=True, default=None)# number of students that teacher can supervise
    projects = db.relationship('Project', backref='teacher', lazy=True, foreign_keys='Project.teacher_id')

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    field = db.Column(db.String(50), nullable=False)

    skill_requirements = db.Column(db.String(200), default='')

    status = db.Column(db.String(20), nullable=False, default='pending')
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True) # teacher who supervise this project
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # wsho created this project

    interested_students = db.relationship('StudentInterest', backref='project', lazy=True)

class StudentInterest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class ApprovedProject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

@app.route('/api/project/approve/<int:project_id>', methods=['POST'])
@login_required
def approve_project(project_id):
    if not current_user.is_teacher:
        return jsonify({'error': 'Unauthorized'}), 403
    project = Project.query.get_or_404(project_id)
    project.status = 'approved'
    db.session.commit()
    return jsonify({'message': 'Project approved'})

@app.route('/api/project/reject/<int:project_id>', methods=['POST'])
@login_required
def reject_project(project_id):
    if not current_user.is_teacher:
        return jsonify({'error': 'Unauthorized'}), 403
    project = Project.query.get_or_404(project_id)
    project.status = 'rejected'
    db.session.commit()
    return jsonify({'message': 'Project rejected'})

@app.route('/api/project/apply/<int:project_id>', methods=['POST'])
@login_required
def apply_to_project(project_id):
    if current_user.is_teacher:
        return jsonify({'error': 'Teachers cannot apply'}), 403

    project = Project.query.get_or_404(project_id)
    if project.status != 'approved':
        return jsonify({'error': 'Project not approved'}), 400

    #
    teacher = User.query.get(project.teacher_id)
    if teacher and teacher.quota is not None:
        #
        current_count = ApprovedProject.query \
            .join(Project, Project.id == ApprovedProject.project_id) \
            .filter(Project.teacher_id == teacher.id).count()

        if current_count >= teacher.quota:
            return jsonify({'error': 'Teacher has reached their supervision quota'}), 400

    #
    existing = ApprovedProject.query.filter_by(student_id=current_user.id, project_id=project_id).first()
    if existing:
        return jsonify({'message': 'Already applied'}), 400

    application = ApprovedProject(student_id=current_user.id, project_id=project_id)
    db.session.add(application)
    db.session.commit()
    return jsonify({'message': 'Application successful'})


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.context_processor
def utility_processor():
    def get_user(user_id):
        return User.query.get(user_id)
    return dict(get_user=get_user)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')  # 'teacher' or 'student'

        if not email or not password or not role:
            flash('All fields are required.')
            return redirect(url_for('register'))

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered.')
            return redirect(url_for('register'))

        new_user = User(
            email=email,
            password_hash=generate_password_hash(password),
            is_teacher=(role == 'teacher'),
            quota=3 if role == 'teacher' else None
        )
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful. Please log in.')
        return redirect(url_for('default_login'))

    return render_template('register.html')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def default_login():
    # 默认重定向到学生登录页面
    return redirect(url_for('login', role='student'))

@app.route('/login/<role>', methods=['GET', 'POST'])
def login(role):
    print(f"登录路由被访问 - 方法: {request.method}, 角色: {role}")
    
    if request.method == 'POST':
        print(f"登录表单数据: {request.form}")
        
        email = request.form.get('email')
        password = request.form.get('password')
        
        print(f"登录尝试 - 邮箱: {email}, 角色: {role}, 密码已提供: {'是' if password else '否'}")
        
        user = User.query.filter_by(email=email).first()
        print(f"用户存在: {'是' if user else '否'}")
        
        if user and check_password_hash(user.password_hash, password):
            print(f"密码验证通过")
            
            # 验证用户角色
            if (role == 'teacher' and not user.is_teacher) or (role == 'student' and user.is_teacher):
                print(f"角色不匹配 - 用户是否为教师: {user.is_teacher}, 请求角色: {role}")
                flash('Not authorized to login with this role.')
                return redirect(url_for('login', role=role))
            
            login_user(user)
            print(f"登录成功 - 用户是否为教师: {user.is_teacher}")
            
            if user.is_teacher:
                print(f"重定向到教师仪表板")
                return redirect(url_for('teacher_dashboard'))
            else:
                print(f"重定向到学生仪表板")
                return redirect(url_for('student_dashboard'))
        else:
            print(f"密码验证失败或用户不存在")
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
    
    # 获取学生已选择的项目
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
        user_input = request.json.get('message')
        print(f"\n用户输入: {user_input}")
        
        requirements = analyze_user_requirements(user_input)
        print(f"分析需求结果: {json.dumps(requirements, ensure_ascii=False)}")
        
        projects = Project.query.all()
        print(f"数据库中的项目: {[p.name for p in projects]}")
        
        ranked_projects = rank_projects(requirements, projects)
        print(f"匹配的项目: {[p.name for p in ranked_projects]}")
        
        return jsonify({
            'projects': [{
                'id': p.id,
                'name': p.name,
                'description': p.description,
                'field': p.field,
                'skill_requirements': p.skill_requirements or '',
                'teacher_email': User.query.get(p.teacher_id).email
            } for p in ranked_projects]
        })
    else:
        return jsonify({'message': 'Only POST method is supported'}), 405

@app.route('/api/project/interest', methods=['POST'])
@login_required
def express_interest():
    if current_user.is_teacher:
        return jsonify({'error': 'Unauthorized'}), 403
    
    project_id = request.json.get('project_id')
    if not project_id:
        return jsonify({'error': 'Project ID is required'}), 400
    
    existing_interest = StudentInterest.query.filter_by(
        student_id=current_user.id
    ).first()
    
    if existing_interest:
        return jsonify({'error': 'You have already expressed interest in a project'}), 400
    
    interest = StudentInterest(student_id=current_user.id, project_id=project_id)
    db.session.add(interest)
    db.session.commit()
    
    return jsonify({'message': 'Interest recorded successfully'})

@app.route('/create_project', methods=['GET', 'POST'])
@login_required
def create_project():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        field = request.form.get('field')
        skill_requirements = request.form.get('skill_requirements', '')

        if not all([name, description, field]):
            flash('Project Name, Description, and Field are required.')
            return redirect(url_for('create_project'))

        project = Project(
            name=name,
            description=description,
            field=field,
            skill_requirements=skill_requirements,
            teacher_id=current_user.id if current_user.is_teacher else None,
            creator_id=current_user.id
        )
        db.session.add(project)
        db.session.commit()

        flash('Project created successfully!')
        if current_user.is_teacher:
            return redirect(url_for('teacher_dashboard'))
        else:
            return redirect(url_for('student_dashboard'))

    return render_template('create_project.html')

@app.route('/api/projects', methods=['POST'])
@login_required
def api_create_project():
    data = request.json
    name = data.get('name')
    description = data.get('description')
    field = data.get('field')
    skill_requirements = data.get('skill_requirements', '')

    if not all([name, description, field]):
        return jsonify({'error': 'Project Name, Description, and Field are required.'}), 400

    project = Project(
        name=name,
        description=description,
        field=field,
        skill_requirements=skill_requirements,
        teacher_id=current_user.id if current_user.is_teacher else None,
        creator_id=current_user.id
    )
    db.session.add(project)
    db.session.commit()

    return jsonify({
        'id': project.id,
        'name': project.name,
        'description': project.description,
        'field': project.field,
        'skill_requirements': project.skill_requirements,
        'status': project.status
    }), 201

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

        db.session.commit()
        flash('Project updated successfully!')
        return redirect(url_for('teacher_dashboard'))
        
    return render_template('edit_project.html', project=project)

@app.route('/student_interest/<int:project_id>', methods=['POST'])
@login_required
def student_interest(project_id):
    if current_user.is_teacher:
        return jsonify({'error': 'Teachers cannot express interest'}), 403
        
    # 检查学生是否已经选择了其他项目
    existing_interest = StudentInterest.query.filter_by(student_id=current_user.id).first()
    if existing_interest:
        if existing_interest.project_id == project_id:
            return jsonify({'message': 'You have already selected this project.'}), 400
        else:
            return jsonify({'message': 'You have already selected another project. Please cancel your previous selection first.'}), 400
            
    interest = StudentInterest(student_id=current_user.id, project_id=project_id)
    db.session.add(interest)
    db.session.commit()
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
    
    db.session.delete(interest)
    db.session.commit()
    
    if request.method == 'GET':
        flash('Project selection cancelled successfully.')
        return redirect(url_for('student_dashboard'))
    
    return jsonify({'message': 'Selection cancelled.'})

def init_db():
    with app.app_context():
        # 删除所有表并重新创建
        db.drop_all()
        db.create_all()
        
        # 创建测试账号
        teacher = User(
            email='teacher@test.com',
            password_hash=generate_password_hash('teacher123'),
            is_teacher=True,
            quota=3
        )
        db.session.add(teacher)
        db.session.commit()  # 立即提交以获取teacher.id
        
        # 添加测试项目
        projects = [
            {
                'name': 'AI Image Recognition Project',
                'description': 'This project utilizes deep learning and computer vision techniques to perform medical image analysis, including X-ray interpretation and lesion detection. It will be developed using the PyTorch framework and feature an interactive visualization interface to present the analysis results.',
                'field': 'Medical and Healthy',
                'skill_requirements': 'Python, PyTorch, Computer Vision, Deep Learning'
            },
            {
                'name': 'Intelligent Medical Diagnosis Assistant',
                'description': 'An intelligent consultation system based on natural language processing and machine learning, capable of understanding patient descriptions and providing preliminary diagnostic suggestions. The project uses the BERT model to process medical text data.',
                'field': 'Medical and Healthy',
                'skill_requirements': 'Python, NLP, Machine Learning, BERT'
            },
            {
                'name': 'Blockchain-Based Medical Data System',
                'description': 'A secure and transparent medical data sharing platform built using blockchain technology, ensuring patient data privacy and security. The project includes smart contract development and web interface implementation.',
                'field': 'Medical and Healthy',
                'skill_requirements': 'Blockchain, Solidity, Smart Contracts, Web Development'
            },
            {
                'name': 'Blockchain Application Development',
                'description': 'Development of decentralized applications (DApps) based on Ethereum, enabling the deployment and interaction with smart contracts. The project includes DApp frontend development and smart contract programming.',
                'field': 'Block Chain',
                'skill_requirements': 'Ethereum, Solidity, Web3.js, JavaScript, DApp Development'
            },
            {
                'name': 'Smart Home Control System',
                'description': 'A smart home control system based on IoT technology, enabling remote control, automated scenarios, and voice interaction. The project utilizes the MQTT protocol and ESP32 development boards to deliver a comprehensive smart home solution.',
                'field': 'IOT',
                'skill_requirements': 'IoT, MQTT, ESP32, C++, Embedded Systems'
            },
            {
                'name': 'Cybersecurity Vulnerability Detection Platform',
                'description': 'An automated cybersecurity vulnerability scanning and detection platform capable of assessing internal enterprise networks for security risks and vulnerabilities. The project is built using Python and open-source security tools to establish a comprehensive security testing framework.',
                'field': 'Cyber Security',
                'skill_requirements': 'Python, Cybersecurity, Network Scanning, Linux'
            },
            {
                'name': 'Big Data Analytics and Visualization Platform',
                'description': 'An enterprise-level big data processing and analytics platform that offers intuitive data visualization and predictive analysis capabilities. The project leverages the Hadoop ecosystem for data storage and processing, and utilizes the D3.js library for dynamic data visualization.',
                'field': 'Big Data',
                'skill_requirements': 'Big Data, Hadoop, Spark, D3.js, Data Visualization, Python'
            },
            {
                'name': 'Decentralized Identity Verification System',
                'description': 'A blockchain-based identity verification system that enables users to securely control and share their identity credentials without relying on centralized authorities. The system uses smart contracts for credential issuance and verification, ensuring transparency and resistance to tampering.',
                'field': 'Block chain',
                'skill_requirements': 'Solidity, Ethereum, Smart Contracts, Web3.js, Cryptography'
            },
            {
                'name': 'Smart Agriculture Monitoring System',
                'description': 'An IoT-powered system for real-time monitoring of agricultural conditions such as soil moisture, temperature, and humidity. The project involves developing embedded firmware on microcontrollers and a cloud-based dashboard for farmers to receive alerts and optimize irrigation strategies.',
                'field': 'IoT',
                'skill_requirements': 'ESP32, MQTT, Sensors Integration, Python, Cloud Platforms'
            },
            {
                'name': 'AI-Driven Intrusion Detection System',
                'description': 'A machine learning–based intrusion detection system that analyzes network traffic to identify abnormal patterns and potential threats in real time. The system is trained using labeled network datasets and includes a dashboard for security alerts and reports.',
                'field': 'Cybersecurity',
                'skill_requirements': 'Python, Scikit-learn, Network Security, Packet Analysis (Wireshark), Flask/Django'
            },
            {
                'name': 'Real-Time Traffic Flow Prediction Using Big Data Analytics',
                'description': 'A big data platform that collects, processes, and analyzes real-time traffic data to predict congestion and optimize route planning. The system integrates multiple data sources such as GPS, weather, and traffic sensors, and visualizes results on an interactive map.',
                'field': 'Big Data',
                'skill_requirements': 'Apache Spark, Kafka, Hadoop, Scala/Python, D3.js or Leaflet.js'
            },
        ]
        
        for p_data in projects:  # Renamed loop variable to avoid conflict
            project = Project(
                name=p_data['name'],
                description=p_data['description'],
                field=p_data['field'],
                skill_requirements=p_data.get('skill_requirements', ''),
                teacher_id=teacher.id,
                creator_id=teacher.id
            )
            db.session.add(project)
        
        student = User(
            email='student@test.com',
            password_hash=generate_password_hash('student123'),
            is_teacher=False
        )
        db.session.add(student)
        
        db.session.commit()
        print("Database initialized successfully!")

if __name__ == '__main__':
    init_db()  # 每次启动时重新初始化数据库
    app.run(debug=True)
