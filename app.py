"""
科学猜想报告人工评估系统 — Flask 主应用

启动方式:
    python app.py              # 正常启动（需先 --init）
    python app.py --init       # 初始化数据库 + 导入报告 + 创建审稿人
    python app.py --port 8080  # 指定端口
"""

import os
import sys
import argparse
import markdown
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, make_response
from datetime import datetime

# ---- 应用初始化 ----
app = Flask(__name__)
app.secret_key = 'change-this-to-a-random-secret-key'

# 路径配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPORTS_DIR = os.path.abspath(os.path.join(BASE_DIR, '..', 'reports'))
DB_PATH = os.path.join(BASE_DIR, 'eval.db')

# 导入自定义模块
import db
from db import init_db, insert_report, get_all_reports, get_report, get_all_reviewers, get_reviewer, \
    create_reviewer, create_assignment, get_assignments_for_reviewer, get_all_assignments, \
    clear_assignments, save_score, get_score, get_all_scores, get_scores_as_dataframe, \
    get_progress_summary, get_reviewer_progress, reject_assignment

# 设置数据库路径
db.DB_PATH = DB_PATH
from parser import parse_all_reports
from assignment import generate_assignments, get_assignment_summary
from stats import get_all_statistics

# ---- Markdown 渲染器 ----
md_renderer = markdown.Markdown(extensions=['extra', 'codehilite', 'tables', 'fenced_code'])


def render_markdown(content):
    """
    将 markdown 内容转为 HTML，保护 LaTeX 公式不被 markdown 库破坏。

    Python markdown 库会将 _ 和 * 等字符解析为强调标记，
    破坏 LaTeX 公式。解决方式：先用占位符替换所有公式，
    markdown 转换后再换回来。
    """
    import re
    import uuid

    # 存储被保护的公式
    math_blocks = {}

    def protect(match):
        key = f'MATH{uuid.uuid4().hex[:12]}'
        math_blocks[key] = match.group(0)
        return key

    # 0. 修复表格格式：确保表格行前有空行（否则 markdown 不识别为表格）
    content = re.sub(r'([^\n|])\n(\|.*?\n\|[-| ]+\n)', r'\1\n\n\2', content)

    # 0.5. 保护 Unicode 数学公式中的 _{} 和 ^{} 下标/上标（不被 markdown 转成 <em>）
    content = re.sub(r'(_\{[^}]+\})', protect, content)
    content = re.sub(r'(\^\{[^}]+\})', protect, content)

    # 1. 保护 display math: $$ ... $$（跨行）和 \[ ... \]（跨行）
    content = re.sub(r'\$\$.*?\$\$', protect, content, flags=re.DOTALL)
    content = re.sub(r'\\\[.*?\\\]', protect, content, flags=re.DOTALL)

    # 2. 保护 inline math: $ ... $ 和 \( ... \)
    content = re.sub(r'(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)', protect, content)
    content = re.sub(r'\\\(.*?\\\)', protect, content)

    # 3. markdown 转换
    html = md_renderer.convert(content)

    # 4. 恢复公式
    for key, formula in math_blocks.items():
        html = html.replace(key, formula)

    # 5. 转义非数学用途的 $ 符号，避免 MathJax 误将其当作 LaTeX 数学分隔符。
    #    匹配货币/金额格式（有逗号、K/M/B后缀、/hr等），这些不可能是 LaTeX 公式。
    #    $25,000  |  $200K  |  $4.2B  |  $15/hr  |  $15/hour  |  $3.50
    html = re.sub(
        r'\$(\d{1,3}(?:,\d{3})*(?:\.\d+)?(?:[KMBkmb])?(?:/[a-zA-Z]+)?)',
        r'&#36;\1', html
    )

    # 6. 将所有 Unicode 下标/上标/数学字母转为标准 HTML，确保前端可读性
    SUB_MAP = {
        'ₐ':'a','ₑ':'e','ₒ':'o','ₓ':'x','ₔ':'schwa',
        'ₕ':'h','ₖ':'k','ₗ':'l','ₘ':'m','ₙ':'n',
        'ₚ':'p','ₛ':'s','ₜ':'t',
        'ⱼ':'j','ᵢ':'i','ᵣ':'r','ᵤ':'u','ᵥ':'v',
        # Greek subscript
        'ᵦ':'beta','ᵧ':'gamma','ᵨ':'rho','ᵩ':'phi','ᵪ':'chi',
    }
    SUP_MAP = {
        '²':'2','³':'3','¹':'1','⁰':'0',
        'ⁱ':'i','⁴':'4','⁵':'5','⁶':'6',
        '⁷':'7','⁸':'8','⁹':'9',
        '⁺':'+','⁻':'-','⁼':'=','⁽':'(','⁾':')',
        'ⁿ':'n',
    }
    # 生僻数学字母 -> 普通 ASCII（非 $...$ 公式内时 MathJax 无法渲染）
    MATH_ASCII = {
        # Double-struck
        '\U0001D538':'A','\U0001D539':'B','\U0001D53C':'E','\U0001D53D':'F',
        '\U0001D540':'I','\U0001D541':'J','\U0001D544':'M',
        '\U0001D546':'O','\U0001D54A':'S','\U0001D54B':'T',
        '\U0001D552':'a','\U0001D553':'b','\U0001D554':'c','\U0001D555':'d',
        '\U0001D556':'e','\U0001D557':'f','\U0001D55A':'i','\U0001D55B':'j',
        '\U0001D55D':'l','\U0001D55E':'m','\U0001D55F':'n','\U0001D560':'o',
        '\U0001D561':'p','\U0001D563':'r','\U0001D564':'s','\U0001D565':'t',
        # Script
        'ℒ':'L','ℓ':'l','℘':'P',
    }
    for uch, letter in SUB_MAP.items():
        if uch in html:
            html = html.replace(uch, f'<sub>{letter}</sub>')
    for uch, digit in SUP_MAP.items():
        if uch in html:
            html = html.replace(uch, f'<sup>{digit}</sup>')
    for uch, ascii_char in MATH_ASCII.items():
        if uch in html:
            html = html.replace(uch, ascii_char)

    # 7. 将简单的 _{word} / ^{word} 转为 HTML <sub>/<sup>（单层，无嵌套括号）
    #    只匹配 _{字母数字}，跳过 _{复杂表达式} 避免破坏嵌套结构
    html = re.sub(r'_\{(?=\w+\})', '<sub>', html)
    html = re.sub(r'\^\{(?=\w+\})', '<sup>', html)
    # 关闭对应的标签（匹配 <sub>xxx} 或 <sup>xxx}）
    html = re.sub(r'(<sub>\w+)\}', r'\1</sub>', html)
    html = re.sub(r'(<sup>\w+)\}', r'\1</sup>', html)

    return html


# ---- 初始化命令 ----
def do_init():
    """初始化数据库和导入数据"""
    print("=" * 60)
    print("  Scientific Hypothesis Evaluation System - Init")
    print("=" * 60)

    # 1. 初始化数据库
    print("\n[1/4] Initializing database...")
    init_db(DB_PATH)
    print(f"  Database created: {DB_PATH}")

    # 2. 导入报告
    print("\n[2/4] Importing reports...")
    if not os.path.isdir(REPORTS_DIR):
        print(f"  ERROR: Reports directory not found: {REPORTS_DIR}")
        sys.exit(1)

    reports = parse_all_reports(REPORTS_DIR)
    for r in reports:
        insert_report(r['filename'], r['research_topic'], r['generated_date'], r['content'])
    print(f"  Imported {len(reports)} reports")

    # 3. 创建审稿人
    print("\n[3/4] Creating reviewers...")
    default_reviewers = [
        "审稿人 A",
        "审稿人 B",
        "审稿人 C",
        "审稿人 D",
        "审稿人 E"
    ]
    for name in default_reviewers:
        create_reviewer(name)
    print(f"  Created {len(default_reviewers)} reviewers")

    # 4. 生成分配
    print("\n[4/4] Generating assignments...")
    all_reports = get_all_reports()
    all_reviewers = get_all_reviewers()
    report_ids = [r['id'] for r in all_reports]
    reviewer_ids = [r['id'] for r in all_reviewers]

    clear_assignments()
    pairs = generate_assignments(report_ids, reviewer_ids, seed=42)
    for report_id, reviewer_id in pairs:
        create_assignment(report_id, reviewer_id)

    print(f"  Generated {len(pairs)} assignment records")
    summary = get_assignment_summary(pairs, reviewer_ids)
    print(summary)

    print("\n" + "=" * 60)
    print("  Init complete!")
    print("  Run: python app.py")
    print("  Visit: http://localhost:5000")
    print("=" * 60)


# ---- 路由：认证 ----
@app.route('/')
def index():
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        reviewer_id = request.form.get('reviewer_id')
        if reviewer_id:
            reviewer = get_reviewer(int(reviewer_id))
            if reviewer:
                session['reviewer_id'] = reviewer['id']
                session['reviewer_name'] = reviewer['name']
                flash(f'欢迎, {reviewer["name"]}!', 'success')
                return redirect(url_for('dashboard'))
        flash('请选择有效的审稿人身份', 'error')

    reviewers = get_all_reviewers()
    return render_template('login.html', reviewers=reviewers, reviewer_count=len(reviewers))


@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form.get('password', '')
        import os as _os
        admin_pw = _os.environ.get('ADMIN_PASSWORD', 'admin')
        if password == admin_pw:
            session['reviewer_id'] = 'admin'
            session['reviewer_name'] = '管理员'
            flash('已进入管理后台', 'success')
            return redirect(url_for('admin'))
        flash('密码错误', 'error')
    return render_template('login.html', reviewers=[], reviewer_count=0, admin_mode=True)


@app.route('/logout')
def logout():
    session.clear()
    flash('已退出登录', 'info')
    return redirect(url_for('login'))


# ---- 路由：审稿人工作台 ----
@app.route('/dashboard')
def dashboard():
    if 'reviewer_id' not in session or session['reviewer_id'] == 'admin':
        return redirect(url_for('login'))

    reviewer_id = session['reviewer_id']
    progress = get_reviewer_progress(reviewer_id)
    assignments = get_assignments_for_reviewer(reviewer_id)

    pending = [a for a in assignments if a['status'] == 'pending']
    completed = [a for a in assignments if a['status'] == 'completed']

    return render_template(
        'dashboard.html',
        progress=progress,
        pending_assignments=pending,
        completed_assignments=completed
    )


# ---- 路由：报告查看与评分 ----
@app.route('/report/<int:report_id>')
def view_report(report_id):
    if 'reviewer_id' not in session:
        return redirect(url_for('login'))

    report = get_report(report_id)
    if not report:
        flash('报告不存在', 'error')
        return redirect(url_for('dashboard'))

    # 渲染 markdown 为 HTML
    content_html = render_markdown(report['content'])

    # 检查是否已有评分
    existing_score = None
    if session['reviewer_id'] != 'admin':
        existing_score = get_score(report_id, session['reviewer_id'])

    return render_template(
        'report.html',
        report=report,
        content_html=content_html,
        existing_score=existing_score
    )


@app.route('/report/<int:report_id>/score', methods=['POST'])
def submit_score(report_id):
    if 'reviewer_id' not in session or session['reviewer_id'] == 'admin':
        return jsonify({'success': False, 'error': '需要审稿人身份'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': '无效的请求数据'}), 400

    # 验证评分
    for dim in ['nov', 'sig', 'eff', 'cla', 'fea']:
        val = data.get(dim)
        if val is None or not isinstance(val, int) or val < 0 or val > 10:
            return jsonify({'success': False, 'error': f'{dim} 必须是 0-10 的整数'}), 400

    try:
        save_score(report_id, session['reviewer_id'], data)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ---- 路由：评分细则 ----
@app.route('/rubric')
def rubric():
    """评分细则页面"""
    rubric_path = os.path.join(BASE_DIR, 'static', 'rubric.md')
    if not os.path.exists(rubric_path):
        # 回退到 reports 目录下的细则
        rubric_path = os.path.abspath(os.path.join(BASE_DIR, '..', 'reports', '人工评估细则.md'))

    if os.path.exists(rubric_path):
        with open(rubric_path, 'r', encoding='utf-8') as f:
            content = f.read()
        html = render_markdown(content)
    else:
        html = '<p>评分细则文件未找到</p>'

    return render_template('rubric_page.html', content=html)


# ---- 路由：管理后台 ----
@app.route('/admin')
def admin():
    if session.get('reviewer_id') != 'admin':
        return redirect(url_for('admin_login'))

    summary_data = get_progress_summary()
    reviewers = get_all_reviewers()

    # 每位审稿人的进度
    reviewer_progress = []
    for r in reviewers:
        progress = get_reviewer_progress(r['id'])
        reviewer_progress.append({
            'name': r['name'],
            'completed': progress['completed'],
            'total': progress['total'],
            'completion_rate': progress['completion_rate']
        })

    return render_template(
        'admin.html',
        summary={
            'total_reports': len(get_all_reports()),
            'total_completed': summary_data['completed'],
            'completion_rate': summary_data['completion_rate'],
            'total_reviewers': len(reviewers)
        },
        reviewer_progress=reviewer_progress
    )


@app.route('/admin/assignments')
def admin_assignments():
    if session.get('reviewer_id') != 'admin':
        return redirect(url_for('admin_login'))

    assignments = get_all_assignments()

    # 生成分配摘要
    all_reviewers = get_all_reviewers()
    reviewer_ids = [r['id'] for r in all_reviewers]
    assignment_pairs = [(a['report_id'], a['reviewer_id']) for a in assignments
                        if isinstance(a['reviewer_id'], int)]
    summary = get_assignment_summary(assignment_pairs, reviewer_ids) if assignment_pairs else None

    return render_template(
        'admin_assignments.html',
        assignments=assignments,
        assignment_summary=summary
    )


@app.route('/admin/generate-assignments', methods=['POST'])
def admin_generate_assignments():
    if session.get('reviewer_id') != 'admin':
        return redirect(url_for('admin_login'))

    all_reports = get_all_reports()
    all_reviewers = get_all_reviewers()
    report_ids = [r['id'] for r in all_reports]
    reviewer_ids = [r['id'] for r in all_reviewers]

    clear_assignments()
    pairs = generate_assignments(report_ids, reviewer_ids, seed=42)
    for report_id, reviewer_id in pairs:
        create_assignment(report_id, reviewer_id)

    flash(f'已生成 {len(pairs)} 条分配记录', 'success')
    return redirect(url_for('admin_assignments'))


@app.route('/admin/reviewers', methods=['GET', 'POST'])
def admin_reviewers():
    if session.get('reviewer_id') != 'admin':
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        name = request.form.get('reviewer_name', '').strip()
        if name:
            create_reviewer(name)
            flash(f'已添加审稿人: {name}', 'success')
        else:
            flash('请输入审稿人姓名', 'error')
        return redirect(url_for('admin_reviewers'))

    reviewers_data = get_all_reviewers()
    reviewers_with_progress = []
    for r in reviewers_data:
        progress = get_reviewer_progress(r['id'])
        r['assignment_count'] = progress['total']
        r['completed_count'] = progress['completed']
        r['completion_rate'] = progress['completion_rate']
        reviewers_with_progress.append(r)

    return render_template('admin_reviewers.html', reviewers=reviewers_with_progress)


@app.route('/admin/stats')
def admin_stats():
    if session.get('reviewer_id') != 'admin':
        return redirect(url_for('admin_login'))

    scores_df = get_scores_as_dataframe()
    stats = get_all_statistics(scores_df) if not scores_df.empty else None

    return render_template('admin_stats.html', stats=stats)


@app.route('/admin/reject/<int:report_id>/<int:reviewer_id>', methods=['POST'])
def admin_reject(report_id, reviewer_id):
    """管理员打回评分，让审稿人重新评估"""
    if session.get('reviewer_id') != 'admin':
        return jsonify({'success': False, 'error': '需要管理员身份'}), 403

    reject_assignment(report_id, reviewer_id)
    flash(f'已打回报告 #{report_id} 的评分，审稿人需重新评估', 'success')
    return redirect(url_for('admin_scores'))


@app.route('/admin/scores')
def admin_scores():
    """查看所有评分详情，支持打回操作"""
    if session.get('reviewer_id') != 'admin':
        return redirect(url_for('admin_login'))

    scores = get_all_scores()
    return render_template('admin_scores.html', scores=scores)


@app.route('/admin/export')
def admin_export():
    """导出评分数据为 CSV"""
    if session.get('reviewer_id') != 'admin':
        return redirect(url_for('admin_login'))

    scores = get_all_scores()
    if not scores:
        flash('没有可导出的评分数据', 'warning')
        return redirect(url_for('admin_stats'))

    # 生成 CSV
    csv_lines = ['report_id,research_topic,reviewer_name,nov,sig,eff,cla,fea,domain_familiarity,notes,created_at']
    for s in scores:
        csv_lines.append(
            f'{s["report_id"]},"{s.get("research_topic", "")}","{s.get("reviewer_name", "")}",'
            f'{s["nov"]},{s["sig"]},{s["eff"]},{s["cla"]},{s["fea"]},'
            f'{s.get("domain_familiarity", "")},"{s.get("notes", "")}","{s.get("created_at", "")}"'
        )

    csv_content = '\n'.join(csv_lines)
    response = make_response(csv_content)
    response.headers['Content-Type'] = 'text/csv; charset=utf-8-sig'
    response.headers['Content-Disposition'] = f'attachment; filename=scores_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    return response


# ---- 入口 ----
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='科学猜想报告评估系统')
    parser.add_argument('--init', action='store_true', help='初始化数据库、导入报告、创建审稿人、生成分配')
    parser.add_argument('--port', type=int, default=5000, help='服务端口 (默认: 5000)')
    parser.add_argument('--host', type=str, default='127.0.0.1', help='绑定地址 (默认: 127.0.0.1)')
    args = parser.parse_args()

    if args.init:
        do_init()
    else:
        # 检查数据库是否存在
        if not os.path.exists(DB_PATH):
            print("[WARNING] Database not initialized!")
            print("  Run first: python app.py --init")
            print("  Then: python app.py")
            sys.exit(1)

        print("=" * 50)
        print("  Scientific Hypothesis Evaluation System")
        print(f"  URL: http://{args.host}:{args.port}")
        print(f"  Set admin password via: set ADMIN_PASSWORD=yourpassword")
        print("=" * 50)
        app.run(host=args.host, port=args.port, debug=True)
