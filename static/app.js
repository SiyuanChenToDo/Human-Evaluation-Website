/**
 * 科学猜想报告评估系统 — 前端交互脚本
 */

// 评分滑块交互 — 在 report.html 中使用
// 由内联脚本直接处理

// 通用：表单提交确认
document.addEventListener('DOMContentLoaded', function() {
    // 自动隐藏 flash 消息
    const flashMessages = document.querySelectorAll('.flash');
    flashMessages.forEach(msg => {
        setTimeout(() => {
            msg.style.transition = 'opacity 0.5s';
            msg.style.opacity = '0';
            setTimeout(() => msg.remove(), 500);
        }, 5000);
    });

    // 滚动时显示/隐藏 "跳转到评分" 按钮
    const jumpBtn = document.querySelector('.jump-to-score');
    const scoreSection = document.getElementById('scoreSection');
    if (jumpBtn && scoreSection) {
        window.addEventListener('scroll', function() {
            const rect = scoreSection.getBoundingClientRect();
            if (rect.top < window.innerHeight) {
                jumpBtn.style.opacity = '0';
                jumpBtn.style.pointerEvents = 'none';
            } else {
                jumpBtn.style.opacity = '1';
                jumpBtn.style.pointerEvents = 'auto';
            }
        });
    }
});
