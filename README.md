# APMCM B 题合作

题目见 data/Problem B.pdf，已有审计见 B_audit/分析报告.md。两人先以附件 2 联调。

队友负责第一、二问的数据重构、时延、图表与初稿。另一人负责第三问预测、逐炉验证和论文整合。共享接口和具体任务见 docs/队友提示词.md。

## 数据与运行

原始十炉文件已包含在仓库的 work_b/Data/。安装依赖 python -m pip install -r requirements.txt 后，依次运行：

    python B_audit/extract.py
    python B_audit/analyze.py
    python B_audit/sensitivity.py
    python B_audit/spectra.py
    python B_audit/report.py

生成的 .npy、逐炉 JSON 和本地依赖不纳入 Git。运行脚本会覆盖 B_audit 中同名结果，执行前先检查本地修改。

## 第三问复现

从仓库根目录使用同一 Python 环境运行以下命令。第一条从十份原始 XLSB 生成逐炉预测和验证表，第二条生成十炉对照图。

    python -m q3.predict
    python -m q3.plot_results

已有炉次接口导出时，可用 `python -m q3.predict --exports PATH` 直接读取该目录。第一问的新导出可沿用相同字段，供预测使用的信号必须能在对应时刻仅凭当前及过去观测计算。脚本默认使用 `B_audit/signed_lags.csv` 的逐炉候选时延，并在每轮只汇总训练炉。后续第二问若交付同结构的新表，可用 `--lags PATH` 重跑。结果默认写入 `q3/results/`，可用 `--output PATH` 指定新目录。

第三问的建模口径、逐炉结果和限制见 [第三问论文稿](q3/第三问论文稿.md)，三问的正文衔接见 [论文整合稿](docs/论文整合稿.md)。`summary.csv` 为分气体宏平均，`validation.csv` 为逐炉指标，`weights.csv` 为各折组合权重及时延，`contrasts.csv` 为配对误差比较，`predictions.csv` 为逐时刻预测。

## 共同约定

- 保留原始数据。附件 1 两列烟气全零且与题面示例不一致，原因待核实，暂排除其监督标签。
- 跨炉光谱按真实波长对齐。附件 5 记录较短，单独分析。
- 九炉逐炉留出，标准化、降维和调参仅用训练炉。预测特征仅用当前及过去信息。
- 同刻和提前 10 秒实验使用同一目标时刻。时延相关峰不直接视为输运时间真值。
- 修改不同文件，提交前检查 git status，拉取远端变更后再推送。
