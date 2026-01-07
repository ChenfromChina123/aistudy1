// 创建学习进度图表
function createProgressCharts(stats) {
    // 每日学习单词量图表 - 添加DOM元素存在性检查
    const dailyWordsChart = document.getElementById('daily-words-chart');
    if (dailyWordsChart) {
        const dailyWordsCtx = dailyWordsChart.getContext('2d');
        new Chart(dailyWordsCtx, {
            type: 'bar',
            data: {
                labels: stats.daily_words?.labels || ['周一', '周二', '周三', '周四', '周五', '周六', '周日'],
                datasets: [{
                    label: '学习单词数',
                    data: stats.daily_words?.data || [45, 63, 78, 52, 91, 105, 68],
                    backgroundColor: 'rgba(52, 152, 219, 0.6)',
                    borderColor: 'rgba(52, 152, 219, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }
    
    // 单词掌握程度图表 - 添加DOM元素存在性检查
    const masteryChart = document.getElementById('mastery-chart');
    if (masteryChart) {
        const masteryCtx = masteryChart.getContext('2d');
        new Chart(masteryCtx, {
            type: 'pie',
            data: {
                labels: ['已掌握', '学习中', '未掌握'],
                datasets: [{
                    data: [
                        stats.mastered_words || 87,
                        stats.learning_words || 10,
                        stats.unmastered_words || 3
                    ],
                    backgroundColor: [
                        'rgba(39, 174, 96, 0.7)',
                        'rgba(243, 156, 18, 0.7)',
                        'rgba(231, 76, 60, 0.7)'
                    ],
                    borderColor: [
                        'rgba(39, 174, 96, 1)',
                        'rgba(243, 156, 18, 1)',
                        'rgba(231, 76, 60, 1)'
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        });
    }
    
    // 学习趋势图表 - 添加DOM元素存在性检查
    const trendChart = document.getElementById('learning-trend-chart');
    if (trendChart) {
        const trendCtx = trendChart.getContext('2d');
        new Chart(trendCtx, {
            type: 'line',
            data: {
                labels: stats.weekly_trend?.labels || ['第1周', '第2周', '第3周', '第4周', '第5周', '第6周'],
                datasets: [{
                    label: '累计学习单词',
                    data: stats.weekly_trend?.data || [250, 480, 690, 850, 1020, 1254],
                    borderColor: 'rgba(52, 152, 219, 1)',
                    backgroundColor: 'rgba(52, 152, 219, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }
}