"""统计计算模块 — 均值、ICC、Krippendorff's Alpha、分差标记"""

import numpy as np
import pandas as pd


def compute_mean_scores(scores_df):
    """
    计算每篇报告各维度的均值和跨审稿人平均分。
    只对有多人评分的报告计算。

    参数:
        scores_df: DataFrame, columns = [report_id, reviewer_id, nov, sig, eff, cla, fea]

    返回:
        DataFrame: 每篇报告的均分
    """
    if scores_df.empty:
        return pd.DataFrame(columns=['report_id', 'reviewer_count', 'nov_mean', 'sig_mean', 'eff_mean', 'cla_mean', 'fea_mean', 'overall_mean'])

    dims = ['nov', 'sig', 'eff', 'cla', 'fea']

    grouped = scores_df.groupby('report_id').agg(
        reviewer_count=('reviewer_id', 'count'),
        **{f'{d}_mean': (d, 'mean') for d in dims},
        **{f'{d}_std': (d, 'std') for d in dims}
    ).reset_index()

    # 计算综合均分
    for d in dims:
        grouped[f'{d}_mean'] = grouped[f'{d}_mean'].round(2)
        grouped[f'{d}_std'] = grouped[f'{d}_std'].round(2)

    grouped['overall_mean'] = grouped[[f'{d}_mean' for d in dims]].mean(axis=1).round(2)

    return grouped


def compute_icc(scores_df):
    """
    使用 pingouin 计算每个维度的 ICC(2,1) —— 双向随机效应，单次测量。

    返回:
        dict: {dimension: icc_value} 或空字典（数据不足时）
    """
    try:
        import pingouin as pg
    except ImportError:
        return {'error': 'pingouin 未安装。请运行: pip install pingouin'}

    if scores_df.empty:
        return {}

    results = {}
    for dim in ['nov', 'sig', 'eff', 'cla', 'fea']:
        # 准备数据：report_id, reviewer_id, score
        dim_data = scores_df[['report_id', 'reviewer_id', dim]].dropna()
        dim_data = dim_data.rename(columns={dim: 'rating'})

        # 只保留至少被 2 人评过的报告
        report_counts = dim_data.groupby('report_id').size()
        valid_reports = report_counts[report_counts >= 2].index
        dim_data = dim_data[dim_data['report_id'].isin(valid_reports)]

        if len(dim_data) < 5 or dim_data['report_id'].nunique() < 3:
            results[dim] = None
            continue

        try:
            icc_result = pg.intraclass_corr(
                data=dim_data,
                targets='report_id',
                raters='reviewer_id',
                ratings='rating'
            )
            # 获取 ICC2 (two-way random, single rater)
            icc_row = icc_result[icc_result['Type'] == 'ICC2']
            if not icc_row.empty:
                results[dim] = round(icc_row['ICC'].values[0], 4)
            else:
                results[dim] = None
        except Exception:
            results[dim] = None

    return results


def compute_krippendorff_alpha(scores_df):
    """
    按维度计算 Krippendorff's Alpha。

    返回:
        dict: {dimension: alpha_value}
    """
    try:
        import krippendorff
    except ImportError:
        return {'error': 'krippendorff 未安装。请运行: pip install krippendorff'}

    if scores_df.empty:
        return {}

    results = {}
    for dim in ['nov', 'sig', 'eff', 'cla', 'fea']:
        # 构建 reliability matrix: rows=reports, cols=reviewers
        pivot = scores_df.pivot_table(
            index='report_id', columns='reviewer_id', values=dim
        )

        # 只保留至少被 2 人评过的行
        pivot = pivot.dropna(thresh=2)

        if pivot.shape[0] < 3 or pivot.shape[1] < 2:
            results[dim] = None
            continue

        try:
            alpha = krippendorff.alpha(
                reliability_data=pivot.values.T,
                level_of_measurement='interval'
            )
            results[dim] = round(alpha, 4) if not np.isnan(alpha) else None
        except Exception:
            results[dim] = None

    return results


def flag_disagreements(scores_df, threshold=3):
    """
    标记任何维度分差超过阈值的报告。

    返回:
        list[dict]: 每个元素包含 report_id, dimension, scores_detail, diff
    """
    if scores_df.empty:
        return []

    flags = []
    dims = ['nov', 'sig', 'eff', 'cla', 'fea']

    for report_id in sorted(scores_df['report_id'].unique()):
        report_scores = scores_df[scores_df['report_id'] == report_id]

        if len(report_scores) < 2:
            continue

        for dim in dims:
            vals = report_scores[dim].dropna()
            if len(vals) < 2:
                continue

            diff = vals.max() - vals.min()
            if diff > threshold:
                # 收集详细的评分信息
                detail = report_scores[['reviewer_id', dim]].dropna()
                flags.append({
                    'report_id': int(report_id),
                    'dimension': dim,
                    'diff': int(diff),
                    'reviewer_scores': [
                        {'reviewer_id': int(r['reviewer_id']), 'score': int(r[dim])}
                        for _, r in detail.iterrows()
                    ]
                })

    return flags


def get_dimension_distribution(scores_df):
    """
    计算每个维度的分数分布（0-10 的频数）。

    返回:
        dict: {dimension: {score: count}}
    """
    if scores_df.empty:
        return {}

    dims = ['nov', 'sig', 'eff', 'cla', 'fea']
    dist = {}
    for dim in dims:
        counts = scores_df[dim].value_counts().sort_index()
        dist[dim] = {int(k): int(v) for k, v in counts.items()}

    return dist


def get_all_statistics(scores_df):
    """汇总所有统计指标"""
    return {
        'mean_scores': compute_mean_scores(scores_df).to_dict('records') if not scores_df.empty else [],
        'icc': compute_icc(scores_df),
        'krippendorff_alpha': compute_krippendorff_alpha(scores_df),
        'disagreements': flag_disagreements(scores_df),
        'distribution': get_dimension_distribution(scores_df),
        'total_scores': len(scores_df),
        'unique_reports_scored': scores_df['report_id'].nunique() if not scores_df.empty else 0,
        'unique_reviewers': scores_df['reviewer_id'].nunique() if not scores_df.empty else 0,
    }
