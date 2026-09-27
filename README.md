# MuseAI 早报 · zaobao

每天早上自动生成的 AI 科技资讯早报网站，部署在 Cloudflare Pages。

- `content/digest-YYYY-MM-DD.md` — 每天的早报正文（Markdown）
- `build.py` — 静态站生成器（无第三方依赖，`python3 build.py` 即可）
- `dist/` — 生成好的静态页面，直接发布
- `style.css` — 刊式主题样式（米白纸面 + 衬线标题，自动跟随系统深色模式）

## 发布流程

每天早上定时任务生成新的 `content/digest-*.md` 后，运行 `python3 build.py`
重新生成 `dist/`，`git push` 到本仓库，Cloudflare Pages 自动重新部署。

Pages 配置：构建命令留空，输出目录 `dist`。
