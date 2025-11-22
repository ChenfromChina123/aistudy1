# 静态文件目录

## Chart.js 本地文件

如果网络环境无法访问 CDN，请下载 Chart.js 文件到此处：

### 下载步骤

1. 访问以下链接下载 Chart.js 4.4.0 版本：
   - https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js
   - 或访问：https://github.com/chartjs/Chart.js/releases/tag/v4.4.0

2. 将下载的文件重命名为 `chart.umd.min.js`

3. 将文件放置到 `html/static/js/` 目录下

4. 完整路径应为：`html/static/js/chart.umd.min.js`

### 验证

文件放置后，访问 `/html/static/js/chart.umd.min.js` 应该能够正常加载。

如果本地文件不存在，系统会自动尝试使用 CDN。

