"""重叠分配算法 — 为审稿人生成报告评估任务

设计原则：
- 5 位审稿人，150 份报告
- 每位审稿人评 40 篇（20 独评 + 20 共评）
- 33% 重叠率：50 篇报告由 2 人共评
- 每对审稿人之间共享 5 篇报告
- 每篇报告最多被评 2 次
"""

import random


def generate_assignments(report_ids, reviewer_ids, seed=42):
    """
    生成重叠分配方案。

    数学验证:
        150 报告, 5 审稿人, 每人 40 篇 → 200 评估次数
        独评: 100 篇 × 1 人 = 100 次
        共评:  50 篇 × 2 人 = 100 次
        合计: 200 次 ✓

        每位审稿人: 20 独评 + 20 共评 = 40 ✓
        10 对审稿人, 每对共享 5 篇: 10 × 5 = 50 重叠报告 ✓
        每人在 4 对中: 4 × 5 = 20 共评 ✓

    返回:
        list[tuple]: [(report_id, reviewer_id), ...]
    """
    random.seed(seed)
    n_reviewers = len(reviewer_ids)

    if n_reviewers < 2:
        return [(rid, reviewer_ids[0]) for rid in report_ids]

    # 150 报告
    shuffled = report_ids[:]
    random.shuffle(shuffled)

    # 100 篇独评 + 50 篇共评
    unique_reports = shuffled[:100]
    overlap_reports = shuffled[100:150]

    # 每位审稿人 20 篇独评
    unique_per = 20
    assignments = []

    for i, rev_id in enumerate(reviewer_ids):
        start = i * unique_per
        end = start + unique_per
        for rid in unique_reports[start:end]:
            assignments.append((rid, rev_id))

    # 生成 10 对审稿人
    pairs = []
    for i in range(n_reviewers):
        for j in range(i + 1, n_reviewers):
            pairs.append((reviewer_ids[i], reviewer_ids[j]))

    # 每对共享 5 篇
    shared_per_pair = 5
    overlap_idx = 0

    for rev_a, rev_b in pairs:
        for _ in range(shared_per_pair):
            if overlap_idx < len(overlap_reports):
                rid = overlap_reports[overlap_idx]
                assignments.append((rid, rev_a))
                assignments.append((rid, rev_b))
                overlap_idx += 1

    # 验证
    for rev_id in reviewer_ids:
        count = sum(1 for a in assignments if a[1] == rev_id)
        assert count == 40, f"Reviewer {rev_id} has {count} assignments, expected 40"

    return assignments


def get_assignment_summary(assignments, reviewer_ids):
    """Generate assignment summary text"""
    lines = []
    lines.append(f"Total assignments: {len(assignments)}")
    lines.append(f"Total reports: {len(set(a[0] for a in assignments))}")
    lines.append(f"Total reviewers: {len(reviewer_ids)}")
    lines.append("")

    for rev_id in reviewer_ids:
        count = sum(1 for a in assignments if a[1] == rev_id)
        lines.append(f"  Reviewer {rev_id}: {count} reports")

    lines.append("")

    # Calculate overlap
    report_reviewers = {}
    for rid, rev_id in assignments:
        report_reviewers.setdefault(rid, []).append(rev_id)

    overlap_count = sum(1 for v in report_reviewers.values() if len(v) > 1)
    lines.append(f"Overlapped reports (>1 reviewer): {overlap_count}")

    for i, rev_a in enumerate(reviewer_ids):
        for rev_b in reviewer_ids[i+1:]:
            shared = sum(
                1 for v in report_reviewers.values()
                if rev_a in v and rev_b in v
            )
            lines.append(f"  R{rev_a} <-> R{rev_b}: {shared} shared")

    return "\n".join(lines)
