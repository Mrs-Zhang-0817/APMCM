# 2026 APMCM B 题首版归档

这是团队用于复盘和后续复用的首版作品。英文 PDF 是当时的成品快照。团队在后续评估中决定重做，整理时没有重新运行全套实验。

| 内容 | 入口 |
| --- | --- |
| 题目和输入 | [题目 PDF](data/Problem%20B.pdf) · [修订后十炉数据](work_b/Data) · [旧版附件 1](work_b/legacy) |
| 原始输入审计 | [审计脚本](B_audit/audit_problem_b.py) · [修订前审计快照](B_audit/problem_b_data_audit.json) · [文件哈希检查](B_audit/inspect-inputs.ps1) |
| 第一、二问 | [炉次导出接口](q1_q2/heat_interface.md) · [重建与时延结果](q1_q2/results/README.md) |
| 第三问 | [十炉复现与诊断](question3/README.md) · [主分析汇总](q3/results/summary.csv) |
| 论文 | [英文正文与附录](paper/manuscript-en.md) · [成品 PDF](output/pdf/Bapmcm26315849.pdf) |

在仓库根目录运行 `python B_audit/audit_problem_b.py work_b/Data` 可重新检查修订后的输入。归档 JSON 对应旧版附件 1 加其余九炉。复用模型时应先核对输入版本、预测目标时刻及训练炉与测试炉划分。

较早的中文整合稿和第三问初稿可在提交 `775d3c8` 中查看。独立导出仓库的两笔提交和示例图保存在 `archive/problem-b-heat-interface` 分支，最新提交为 `2154aa5`。后续使用的导出接口位于本仓库的 `q1_q2/`。
