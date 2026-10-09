# Contributing / 贡献指南

Thanks for helping keep this list accurate! 感谢帮助维护这份清单！

## Rules

1. **Official sources only.** Every new offer or change needs a link to the provider's own pricing page, docs, official blog, or official X account. Third-party posts, KOL threads and aggregator lists are not accepted on their own (they're welcome as a hint, but we list the offer only after confirming it officially).
2. **No guessing.** If the official page doesn't give a number, we write `Not published` (中文 `未公布`) or `Not stated on the official page.` (`官方页面未说明`).
3. **No gray-hat content.** No multi-account tricks, bulk farming, invite farming, reselling, relay/reseller links or ways to bypass region restrictions.

## How

- **Report an offer / change / ended offer:** [open an issue](../../issues/new?template=new-offer.md) with the official link. The maintainer verifies it, updates [freeai.alexai.top](https://freeai.alexai.top), and the next weekly sync brings it into this repo.
- **Why not edit `data/` directly?** `data/offers.json` mirrors the site's public feed (https://freeai.alexai.top/offers.json) and the CSVs and README tables are generated from it by `python3 scripts/gen_readme.py --fetch`, so manual edits to `data/` or the README tables would be overwritten. Pull requests are welcome for `scripts/`, docs and the issue template.

## 中文简要说明

- 只接受**官方来源**（厂商定价页/文档、官方博客、官方 X 账号）；仅有第三方或 KOL 来源的不收录。
- 官方没给的数字写“未公布”，不猜测。
- 不收录多开账号、批量注册、刷邀请、倒卖额度、中转/转售链接或绕过地区限制的内容。
- 新活动/变更/已结束请 [提 Issue](../../issues/new?template=new-offer.md) 并附官方链接。`data/` 和 README 表格由脚本从网站数据自动生成，请不要手改；欢迎对脚本和文档提 PR。
