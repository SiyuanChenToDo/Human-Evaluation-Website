"""报告解析模块 — 去除 AI agent 评分元数据，提取报告正文和关键信息"""

import os
import re


def extract_field(lines, field_name, default='Unknown'):
    """从元数据行中提取字段值，如 '**Research Topic**: ...'"""
    for line in lines:
        match = re.search(rf'\*\*{field_name}\*\*:\s*(.+)', line)
        if match:
            return match.group(1).strip()
    return default


def parse_report(filepath):
    """
    解析单份报告文件。

    AI 评估元数据在文件开头（第 1-32 行左右），
    实际报告从第二个 '---' 分隔线之后开始。

    返回:
        dict: {
            'research_topic': str,
            'generated_date': str,
            'content': str  (清洗后的 markdown)
        }
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # 提取元数据
    research_topic = extract_field(lines, 'Research Topic')
    generated_date = extract_field(lines, 'Generated')

    # 找到第一个 --- 分隔线，之后就是报告正文
    # 所有报告的 AI 元数据都在第一个 --- 之前
    content_start = 0
    for i, line in enumerate(lines):
        if line.strip() == '---' and i > 10:  # 第一个 --- 在元数据末尾
            content_start = i + 1
            break

    # 跳过 content 开头的空行和主标题装饰线（如多余的 --- + 空行）
    while content_start < len(lines) and (
        lines[content_start].strip() == '' or lines[content_start].strip() == '---'
    ):
        content_start += 1

    content = ''.join(lines[content_start:])

    return {
        'research_topic': research_topic,
        'generated_date': generated_date,
        'content': content
    }


def parse_all_reports(reports_dir):
    """
    解析 reports 目录下所有 .md 报告（排除人工评估细则等文件）。

    返回:
        list[dict]: 每份报告的解析结果，含 filename 字段
    """
    reports = []
    for fname in sorted(os.listdir(reports_dir)):
        if not fname.endswith('.md'):
            continue
        if '人工评估' in fname or '评估细则' in fname:
            continue

        filepath = os.path.join(reports_dir, fname)
        try:
            parsed = parse_report(filepath)
            parsed['filename'] = fname
            reports.append(parsed)
        except Exception as e:
            print(f"[WARNING] 无法解析 {fname}: {e}")

    return reports
