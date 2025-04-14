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
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///instance/test.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 配置 OpenAI
api_key = os.getenv('DEEPSEEK_API_KEY')
print(f"API Key 是否设置: {'是' if api_key else '否'}")
openai.api_key = api_key
openai.api_base = "https://api.deepseek.com/v1"

# 可用的项目领域
AVAILABLE_FIELDS = ['医疗健康', '区块链', '人工智能', '物联网', '大数据', '云计算', '网络安全']

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
    
    # 如果用户只是询问有哪些项目，返回空要求
    if any(keyword in user_input for keyword in ['有什么项目', '有哪些项目', '所有项目', '查看项目']):
        print("用户在询问所有项目，返回 None")
        return None
        
    messages = [
        {
            "role": "system",
            "content": """#### 定位
- 智能助手名称：项目需求分析专家
- 主要任务：分析学生的项目需求，提取关键信息并匹配到预定义的项目领域

#### 能力
- 需求分析：能够准确理解学生表达的项目兴趣和需求
- 领域匹配：将需求精确匹配到预定义的项目领域
- 关键词提取：识别需求中的技术关键词
- 特点总结：提取用户明确表达的项目特点要求

#### 知识储备
- 项目领域：
  - 医疗健康
  - 区块链
  - 人工智能
  - 物联网
  - 大数据
  - 云计算
  - 网络安全

#### 输出格式
必须输出合法的 JSON 格式：
{
    "fields": ["领域1"],  // 数组，1-2个最相关的领域
    "keywords": ["关键词1", "关键词2"],  // 数组，最多3个关键词
    "features": ["特点1"]  // 数组，用户明确提到的特点要求
}

#### 匹配规则
1. 领域：必须从预定义领域中选择
2. 关键词：优先技术相关词汇
3. 特点：只提取用户明确表达的要求"""
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
        return result
    except Exception as e:
        print(f"需求分析失败: {str(e)}")
        print(f"API 返回内容: {response}")
        return None

def rank_projects(requirements, projects):
    """根据用户需求对项目进行排序"""
    print(f"\n开始项目排序...")
    print(f"用户需求: {json.dumps(requirements, ensure_ascii=False)}")
    print(f"可用项目: {[{'id': p.id, 'name': p.name, 'field': p.field} for p in projects]}")
    
    # 如果没有要求，返回所有项目
    if not requirements:
        print("没有具体需求，返回所有项目")
        return projects
    
    messages = [
        {
            "role": "system",
            "content": """#### 定位
- 智能助手名称：项目匹配专家
- 主要任务：根据学生需求对项目进行评分和排序

#### 能力
- 需求理解：理解学生的领域兴趣和具体需求
- 项目分析：分析项目描述和特点
- 相关度评分：计算项目与需求的匹配程度

#### 评分规则
总分10分，由以下三部分组成：
1. 领域匹配（0-5分）：
   - 完全匹配：5分（需求和项目领域完全一致）
   - 相关领域：3分（领域紧密相关）
   - 无关：0分

2. 关键词匹配（0-3分）：
   - 每个关键词完全匹配：1分
   - 每个关键词相关词匹配：0.5分

3. 特点匹配（0-2分）：
   - 完全满足特点：2分
   - 部分满足：1分
   - 不满足：0分

#### 输出格式
必须输出合法的 JSON 格式：
{
    "ranked_projects": [
        {
            "id": 项目ID,
            "score": 分数,
            "reasoning": "得分理由"
        }
    ]
}"""
        },
        {
            "role": "user",
            "content": f"""学生需求：{json.dumps(requirements, ensure_ascii=False)}
项目列表：{json.dumps([{'id': p.id, 'name': p.name, 'description': p.description, 'field': p.field} for p in projects], ensure_ascii=False)}"""
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
        # 只返回匹配度大于等于3分的项目（降低匹配门槛）
        ranked_ids = [item['id'] for item in result['ranked_projects'] if item.get('score', 0) >= 3]
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
    projects = db.relationship('Project', backref='teacher', lazy=True)

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    field = db.Column(db.String(50), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    interested_students = db.relationship('StudentInterest', backref='project', lazy=True)

class StudentInterest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

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
                flash('无权以该身份登录')
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
            flash('邮箱或密码错误')
            
    return render_template('login.html', role=role)

@app.route('/teacher/dashboard')
@login_required
def teacher_dashboard():
    if not current_user.is_teacher:
        flash('无权访问')
        return redirect(url_for('student_dashboard'))
    projects = Project.query.filter_by(teacher_id=current_user.id).all()
    return render_template('teacher_dashboard.html', projects=projects)

@app.route('/student/dashboard')
@login_required
def student_dashboard():
    if current_user.is_teacher:
        flash('无权访问')
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
    if not current_user.is_teacher:
        flash('只有教师可以创建项目')
        return redirect(url_for('index'))

    if request.method == 'GET':
        return render_template('create_project.html')
        
    # POST 请求处理
    name = request.form.get('name')
    description = request.form.get('description')
    field = request.form.get('field')
    
    if not all([name, description, field]):
        flash('所有字段都是必填的')
        return redirect(url_for('create_project'))
        
    project = Project(
        name=name,
        description=description,
        field=field,
        teacher_id=current_user.id
    )
    db.session.add(project)
    db.session.commit()
    
    flash('项目创建成功！')
    return redirect(url_for('teacher_dashboard'))

@app.route('/api/projects', methods=['POST'])
@login_required
def api_create_project():
    if not current_user.is_teacher:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    project = Project(
        name=data['name'],
        description=data['description'],
        field=data['field'],
        teacher_id=current_user.id
    )
    db.session.add(project)
    db.session.commit()
    
    return jsonify({
        'id': project.id,
        'name': project.name,
        'description': project.description,
        'field': project.field
    })

@app.route('/edit_project/<int:project_id>', methods=['GET', 'POST'])
@login_required
def edit_project(project_id):
    if not current_user.is_teacher:
        return redirect(url_for('student_dashboard'))
        
    project = Project.query.get_or_404(project_id)
    if project.teacher_id != current_user.id:
        flash('您没有权限编辑这个项目')
        return redirect(url_for('teacher_dashboard'))
        
    if request.method == 'POST':
        project.name = request.form['name']
        project.description = request.form['description']
        project.field = request.form['field']
        db.session.commit()
        flash('项目更新成功！')
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
            return jsonify({'message': '您已经选择了这个项目'}), 400
        else:
            return jsonify({'message': '您已经选择了其他项目，请先取消之前的选择'}), 400
            
    interest = StudentInterest(student_id=current_user.id, project_id=project_id)
    db.session.add(interest)
    db.session.commit()
    return jsonify({'message': '已成功表达兴趣！'})

@app.route('/cancel_interest/<int:project_id>', methods=['GET', 'POST'])
@login_required
def cancel_interest(project_id):
    if current_user.is_teacher:
        flash('无权操作')
        return redirect(url_for('teacher_dashboard'))
        
    interest = StudentInterest.query.filter_by(
        student_id=current_user.id,
        project_id=project_id
    ).first_or_404()
    
    db.session.delete(interest)
    db.session.commit()
    
    if request.method == 'GET':
        flash('已成功取消选择项目')
        return redirect(url_for('student_dashboard'))
    
    return jsonify({'message': '已取消选择'})

def init_db():
    with app.app_context():
        # 删除所有表并重新创建
        db.drop_all()
        db.create_all()
        
        # 创建测试账号
        teacher = User(
            email='teacher@test.com',
            password_hash=generate_password_hash('teacher123'),
            is_teacher=True
        )
        db.session.add(teacher)
        db.session.commit()  # 立即提交以获取teacher.id
        
        # 添加测试项目
        projects = [
            {
                'name': 'AI图像识别项目',
                'description': '使用深度学习和计算机视觉技术进行医疗图像分析，包括X光片分析和病变检测。项目将使用PyTorch框架，并开发交互式可视化界面展示分析结果。',
                'field': '医疗健康'
            },
            {
                'name': '智能医疗诊断助手',
                'description': '基于自然语言处理和机器学习的智能问诊系统，能够理解患者描述并提供初步诊断建议。项目使用BERT模型处理医疗文本数据。',
                'field': '医疗健康'
            },
            {
                'name': '区块链医疗数据系统',
                'description': '使用区块链技术构建安全、透明的医疗数据共享平台，确保患者数据的隐私和安全。包含智能合约开发和Web界面实现。',
                'field': '医疗健康'
            },
            {
                'name': '区块链应用开发',
                'description': '开发基于以太坊的去中心化应用，实现智能合约的部署和调用。项目包括DApp前端开发和智能合约编写。',
                'field': '区块链'
            },
            {
                'name': '智能家居控制系统',
                'description': '基于物联网技术的智能家居控制系统，实现远程控制、自动化场景和语音交互。使用 MQTT 协议和 ESP32 开发板，打造完整的智能家居解决方案。',
                'field': '物联网'
            },
            {
                'name': '网络安全漏洞检测平台',
                'description': '自动化网络安全漏洞扫描与检测平台，能够对企业内网进行安全评估和风险分析。使用 Python 和开源安全工具，构建完整的安全测试框架。',
                'field': '网络安全'
            },
            {
                'name': '大数据分析与可视化平台',
                'description': '企业级大数据处理与分析平台，提供直观的数据可视化界面和预测分析功能。使用 Hadoop 生态系统和 D3.js 可视化库，实现数据的存储、处理和展示。',
                'field': '大数据'
            }
        ]
        
        for p in projects:
            project = Project(
                name=p['name'],
                description=p['description'],
                field=p['field'],
                teacher_id=teacher.id
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
