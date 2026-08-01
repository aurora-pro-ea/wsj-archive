# 武书剑文章档案

静态站点：[wushujian.pages.dev](https://wushujian.pages.dev/)

## 一键发布

在 Windows 中双击 `publish.cmd`。脚本会依次：

1. 根据三份年度 Markdown 重新生成网站；
2. 检查文章数量、空正文和内部链接；
3. 提交并推送到 GitHub；
4. 由 GitHub Actions 自动部署到现有 Cloudflare Pages 项目。

## GitHub Secrets

仓库的 `Settings → Secrets and variables → Actions` 中需要配置：

- `CLOUDFLARE_ACCOUNT_ID`
- `CLOUDFLARE_API_TOKEN`

Cloudflare API Token 权限：`Account → Cloudflare Pages → Edit`。

敏感值只存放在 GitHub Secrets 中，不要写入仓库文件。
