import os
import sys
import tempfile
import math
import pandas as pd
from pathlib import Path
from datetime import datetime

from flask import Flask, request, render_template, send_file, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from flask_bcrypt import Bcrypt
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError

# 添加项目根目录到 Python 路径，以便导入 src 模块
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src import import_data, classify, report, alert

# ------------------------------------------------------------
# 创建 Flask 应用
# ------------------------------------------------------------
app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # 用于 flash 消息

# 数据库配置
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:root123@localhost/finance_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

bcrypt = Bcrypt(app)

# 登录管理器
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = '请先登录'

# ------------------------------------------------------------
# 定义数据库模型
# ------------------------------------------------------------
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    transactions = db.relationship('Transaction', backref='user', lazy=True)
    
    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    
    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

class Transaction(db.Model):
    __tablename__ = 'transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    tx_time = db.Column(db.DateTime, nullable=False)
    tx_type = db.Column(db.String(50))
    counterparty = db.Column(db.String(200))
    product = db.Column(db.String(500))
    income_expense = db.Column(db.String(10))
    amount = db.Column(db.Numeric(10, 2))
    payment = db.Column(db.String(100))
    status = db.Column(db.String(50))
    tx_id = db.Column(db.String(100), unique=True)
    merchant_id = db.Column(db.String(100))
    remarks = db.Column(db.String(500))
    category = db.Column(db.String(50))
    source_file = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.now)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, default=1)  # 稍后迁移或重建数据库
    
    def __repr__(self):
        return f'<Transaction {self.tx_id}>'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ------------------------------------------------------------
# 表单类（必须在模型之后定义，因为引用了 User 模型）
# ------------------------------------------------------------
class RegistrationForm(FlaskForm):
    username = StringField('用户名', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('邮箱', validators=[DataRequired(), Email()])
    password = PasswordField('密码', validators=[DataRequired()])
    confirm_password = PasswordField('确认密码', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('注册')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('用户名已存在，请选择其他用户名')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('邮箱已被注册')

class LoginForm(FlaskForm):
    email = StringField('邮箱', validators=[DataRequired(), Email()])
    password = PasswordField('密码', validators=[DataRequired()])
    submit = SubmitField('登录')

# ------------------------------------------------------------
# 确保 output 目录存在
# ------------------------------------------------------------
OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'output'))
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ------------------------------------------------------------
# 路由定义
# ------------------------------------------------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('注册成功，请登录', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=True)
            next_page = request.args.get('next')
            flash('登录成功', 'success')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('邮箱或密码错误', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
def logout():
    logout_user()
    flash('您已退出登录', 'info')
    return redirect(url_for('index'))

@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    """处理上传的多个账单文件（支持微信.xlsx和支付宝.csv）"""
    if 'files' not in request.files:
        flash('没有选择文件')
        return redirect(url_for('index'))
    
    files = request.files.getlist('files')
    if not files or files[0].filename == '':
        flash('文件名为空')
        return redirect(url_for('index'))
    
    temp_files = []
    all_dfs = []
    
    try:
        processed_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'processed'))
        os.makedirs(processed_dir, exist_ok=True)
        
        for file in files:
            ext = os.path.splitext(file.filename)[1].lower()
            if ext not in ['.xlsx', '.csv']:
                flash(f'不支持的文件类型: {file.filename}（仅支持 .xlsx 和 .csv）')
                return redirect(url_for('index'))
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                file.save(tmp.name)
                tmp_path = tmp.name
                temp_files.append(tmp_path)
            
            if ext == '.xlsx':
                df = import_data.process_one_file(tmp_path, processed_dir)
            else:
                df = import_data.process_alipay_file(tmp_path, processed_dir)
            
            all_dfs.append(df)
        
        if not all_dfs:
            flash('没有成功导入任何文件')
            return redirect(url_for('index'))
        
        df_merged = pd.concat(all_dfs, ignore_index=True)
        if 'tx_id' in df_merged.columns:
            df_merged = df_merged.drop_duplicates(subset=['tx_id'], keep='first')
        
        merged_parquet = Path(processed_dir) / 'merged_cleaned.parquet'
        df_merged.to_parquet(merged_parquet, index=False)
        
        df_merged = classify.add_category_column(df_merged)
        
        # 存入数据库
        for _, row in df_merged.iterrows():
            row_dict = row.to_dict()
            for key, value in row_dict.items():
                if isinstance(value, float) and math.isnan(value):
                    row_dict[key] = None
            
            tx_id = row_dict.get('tx_id')
            if tx_id and isinstance(tx_id, str):
                tx_id = tx_id.strip().replace('\t', '')
                row_dict['tx_id'] = tx_id
            
            merchant_id = row_dict.get('merchant_id')
            if merchant_id and isinstance(merchant_id, str):
                merchant_id = merchant_id.strip().replace('\t', '')
                row_dict['merchant_id'] = merchant_id
            
            if not tx_id:
                continue
            
            existing = Transaction.query.filter_by(tx_id=tx_id).first()
            if existing:
                continue
            
            trans = Transaction(
                user_id=current_user.id,
                tx_time=row_dict['tx_time'],
                tx_type=row_dict.get('tx_type', ''),
                counterparty=row_dict.get('counterparty', ''),
                product=row_dict.get('product', ''),
                income_expense=row_dict.get('income_expense', ''),
                amount=row_dict['amount'],
                payment=row_dict.get('payment', ''),
                status=row_dict.get('status', ''),
                tx_id=tx_id,
                merchant_id=merchant_id,
                remarks=row_dict.get('remarks', ''),
                category=row_dict.get('category', '其他'),
                source_file=','.join([f.filename for f in files])
            )
            db.session.add(trans)
        
        try:
            db.session.commit()
            print(f"成功存入 {len(df_merged)} 条记录到数据库")
        except IntegrityError:
            db.session.rollback()
            print("部分数据已存在，跳过重复")
        
        df_merged.to_parquet(merged_parquet, index=False)
        
        for p in Path(processed_dir).glob('*_cleaned.parquet'):
            if p.name != 'merged_cleaned.parquet':
                p.unlink()
        
        report_gen = report.generate_monthly_report(processed_dir, OUTPUT_DIR)
        excel_paths = []
        df_expenses = []
        for path, df in report_gen:
            excel_paths.append(path)
            df_expenses.append(df)
        
        if not excel_paths:
            flash('报表生成失败')
            return redirect(url_for('index'))
        
        latest_report = os.path.basename(excel_paths[0])
        
        df_merged['month'] = df_merged['tx_time'].dt.to_period('M').astype(str)
        months = df_merged['month'].unique()
        budget = alert.load_budget()
        for month in months:
            df_month = df_merged[df_merged['month'] == month]
            over_items = alert.check_overbudget(df_month, budget, month)
            if over_items:
                alert.mark_excel_overbudget(os.path.join(OUTPUT_DIR, latest_report), over_items, month)
        
        df_expense_only = df_merged[df_merged['income_expense'] == '支出']
        pie_chart = report.plot_pie_chart(df_expense_only)
        trend_chart = report.plot_trend_chart(df_expense_only)
        
        return render_template('result.html',
                               report_file=latest_report,
                               pie_chart=pie_chart,
                               trend_chart=trend_chart)
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        flash(f'处理出错: {str(e)}\n请查看控制台（终端）中的详细错误信息。')
        return redirect(url_for('index'))
    
    finally:
        for tmp_path in temp_files:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

@app.route('/download/<filename>')
@login_required
def download_file(filename):
    return send_file(os.path.join(OUTPUT_DIR, filename), as_attachment=True)

@app.route('/history')
@login_required
def history():
    start_date = request.args.get('start')
    end_date = request.args.get('end')
    
    query = Transaction.query.filter_by(user_id=current_user.id)
    if start_date:
        query = query.filter(Transaction.tx_time >= start_date)
    if end_date:
        query = query.filter(Transaction.tx_time <= end_date + ' 23:59:59')
    
    transactions = query.order_by(Transaction.tx_time.desc()).all()
    
    if transactions:
        df = pd.DataFrame([{
            'tx_time': t.tx_time,
            'amount': float(t.amount),
            'category': t.category,
            'income_expense': t.income_expense
        } for t in transactions])
        
        df_expense = df[df['income_expense'] == '支出']
        if not df_expense.empty:
            pie_chart = report.plot_pie_chart(df_expense)
            trend_chart = report.plot_trend_chart(df_expense)
        else:
            pie_chart = trend_chart = None
    else:
        pie_chart = trend_chart = None
    
    return render_template('history.html',
                           transactions=transactions,
                           start=start_date,
                           end=end_date,
                           pie_chart=pie_chart,
                           trend_chart=trend_chart)

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)