# APMCM B 题合作

题目见 data/Problem B.pdf，已有审计见 B_audit/分析报告.md。两人先以附件 2 联调。

队友负责第一、二问的数据重构、时延、图表与初稿。另一人负责第三问预测、逐炉验证和论文整合。共享接口和具体任务见 docs/队友提示词.md。

## 数据与运行

原始十炉文件各自放在仓库根目录 work_b/Data/，文件名保持官方原样。安装 Python 依赖 numpy、Pillow、pyxlsb 后，依次运行：

    python B_audit/extract.py
    python B_audit/analyze.py
    python B_audit/sensitivity.py
    python B_audit/spectra.py
    python B_audit/report.py

生成的 .npy、逐炉 JSON 和原始数据不纳入 Git。运行脚本会覆盖 B_audit 中同名结果，执行前先检查本地修改。

## 共同约定

- 保留原始数据。附件 1 两列烟气全零且与题面示例不一致，原因待核实，暂排除其监督标签。
- 跨炉光谱按真实波长对齐。附件 5 记录较短，单独分析。
- 九炉逐炉留出，标准化、降维和调参仅用训练炉。预测特征仅用当前及过去信息。
- 同刻和提前 10 秒实验使用同一目标时刻。时延相关峰不直接视为输运时间真值。
- 修改不同文件，提交前检查 git status，拉取远端变更后再推送。
