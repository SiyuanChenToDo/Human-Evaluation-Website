"""数据库模块 — SQLite 初始化与 CRUD 操作"""

import sqlite3
import os

DB_PATH = None  # 由 app.py 在初始化时设置


def get_db():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path):
    """初始化数据库，创建所有表"""
    global DB_PATH
    DB_PATH = db_path

    conn = get_db()
    cursor = conn.cursor()

    cursor.executescript('''
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT UNIQUE NOT NULL,
            research_topic TEXT NOT NULL,
            generated_date TEXT,
            content TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS reviewers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id INTEGER NOT NULL REFERENCES reports(id),
            reviewer_id INTEGER NOT NULL REFERENCES reviewers(id),
            status TEXT DEFAULT 'pending',
            UNIQUE(report_id, reviewer_id)
        );

        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id INTEGER NOT NULL REFERENCES reports(id),
            reviewer_id INTEGER NOT NULL REFERENCES reviewers(id),
            nov INTEGER CHECK(nov BETWEEN 0 AND 10),
            sig INTEGER CHECK(sig BETWEEN 0 AND 10),
            eff INTEGER CHECK(eff BETWEEN 0 AND 10),
            cla INTEGER CHECK(cla BETWEEN 0 AND 10),
            fea INTEGER CHECK(fea BETWEEN 0 AND 10),
            notes TEXT,
            domain_familiarity INTEGER CHECK(domain_familiarity BETWEEN 1 AND 5),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(report_id, reviewer_id)
        );
    ''')

    conn.commit()
    conn.close()


# ---- 报告操作 ----

def insert_report(filename, research_topic, generated_date, content):
    conn = get_db()
    conn.execute(
        "INSERT OR REPLACE INTO reports (filename, research_topic, generated_date, content) VALUES (?, ?, ?, ?)",
        (filename, research_topic, generated_date, content)
    )
    conn.commit()
    conn.close()


def get_all_reports():
    conn = get_db()
    rows = conn.execute("SELECT * FROM reports ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_report(report_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


# ---- 审稿人操作 ----

def create_reviewer(name):
    conn = get_db()
    try:
        conn.execute("INSERT INTO reviewers (name) VALUES (?)", (name,))
        conn.commit()
    except sqlite3.IntegrityError:
        pass  # 已存在则忽略
    finally:
        conn.close()


def get_all_reviewers():
    conn = get_db()
    rows = conn.execute("SELECT * FROM reviewers ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_reviewer(reviewer_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM reviewers WHERE id = ?", (reviewer_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


# ---- 分配操作 ----

def create_assignment(report_id, reviewer_id):
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO assignments (report_id, reviewer_id) VALUES (?, ?)",
            (report_id, reviewer_id)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    finally:
        conn.close()


def get_assignments_for_reviewer(reviewer_id):
    conn = get_db()
    rows = conn.execute("""
        SELECT a.*, r.research_topic, r.generated_date
        FROM assignments a
        JOIN reports r ON a.report_id = r.id
        WHERE a.reviewer_id = ?
        ORDER BY a.status, r.id
    """, (reviewer_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_assignments():
    conn = get_db()
    rows = conn.execute("""
        SELECT a.*, r.research_topic, rv.name as reviewer_name
        FROM assignments a
        JOIN reports r ON a.report_id = r.id
        JOIN reviewers rv ON a.reviewer_id = rv.id
        ORDER BY a.reviewer_id, r.id
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def clear_assignments():
    conn = get_db()
    conn.execute("DELETE FROM assignments")
    conn.commit()
    conn.close()


# ---- 打回操作 ----

def reject_assignment(report_id, reviewer_id):
    """将已完成评分的分配打回为待评状态，同时清除旧评分记录"""
    conn = get_db()
    conn.execute("""
        UPDATE assignments SET status = 'pending'
        WHERE report_id = ? AND reviewer_id = ?
    """, (report_id, reviewer_id))
    # 删除旧的评分记录，避免重复计数
    conn.execute("""
        DELETE FROM scores WHERE report_id = ? AND reviewer_id = ?
    """, (report_id, reviewer_id))
    conn.commit()
    conn.close()


# ---- 评分操作 ----

def save_score(report_id, reviewer_id, scores_dict):
    """保存或更新评分"""
    conn = get_db()
    conn.execute("""
        INSERT INTO scores (report_id, reviewer_id, nov, sig, eff, cla, fea, notes, domain_familiarity, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(report_id, reviewer_id) DO UPDATE SET
            nov = excluded.nov,
            sig = excluded.sig,
            eff = excluded.eff,
            cla = excluded.cla,
            fea = excluded.fea,
            notes = excluded.notes,
            domain_familiarity = excluded.domain_familiarity,
            updated_at = CURRENT_TIMESTAMP
    """, (
        report_id, reviewer_id,
        scores_dict.get('nov'), scores_dict.get('sig'), scores_dict.get('eff'),
        scores_dict.get('cla'), scores_dict.get('fea'),
        scores_dict.get('notes'), scores_dict.get('domain_familiarity')
    ))

    # 同时更新 assignment 状态为 completed
    conn.execute("""
        UPDATE assignments SET status = 'completed'
        WHERE report_id = ? AND reviewer_id = ?
    """, (report_id, reviewer_id))

    conn.commit()
    conn.close()


def get_score(report_id, reviewer_id):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM scores WHERE report_id = ? AND reviewer_id = ?",
        (report_id, reviewer_id)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_scores():
    """获取所有评分，用于统计"""
    conn = get_db()
    rows = conn.execute("""
        SELECT s.*, rv.name as reviewer_name, r.research_topic
        FROM scores s
        JOIN reviewers rv ON s.reviewer_id = rv.id
        JOIN reports r ON s.report_id = r.id
        ORDER BY s.report_id, s.reviewer_id
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_scores_as_dataframe():
    """将评分数据转为 pandas DataFrame，用于统计计算"""
    import pandas as pd
    scores = get_all_scores()
    if not scores:
        return pd.DataFrame(columns=['report_id', 'reviewer_id', 'nov', 'sig', 'eff', 'cla', 'fea'])
    return pd.DataFrame(scores)


def get_progress_summary():
    """获取总体进度"""
    conn = get_db()
    total_assignments = conn.execute("SELECT COUNT(*) FROM assignments").fetchone()[0]
    completed = conn.execute("SELECT COUNT(*) FROM assignments WHERE status = 'completed'").fetchone()[0]
    conn.close()
    return {
        'total_assignments': total_assignments,
        'completed': completed,
        'pending': total_assignments - completed,
        'completion_rate': round(completed / total_assignments * 100, 1) if total_assignments > 0 else 0
    }


def get_reviewer_progress(reviewer_id):
    """获取某位审稿人的进度"""
    conn = get_db()
    total = conn.execute(
        "SELECT COUNT(*) FROM assignments WHERE reviewer_id = ?", (reviewer_id,)
    ).fetchone()[0]
    completed = conn.execute(
        "SELECT COUNT(*) FROM assignments WHERE reviewer_id = ? AND status = 'completed'", (reviewer_id,)
    ).fetchone()[0]
    conn.close()
    return {
        'total': total,
        'completed': completed,
        'pending': total - completed,
        'completion_rate': round(completed / total * 100, 1) if total > 0 else 0
    }
