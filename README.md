# APMCM B 题合作

题目见 data/Problem B.pdf，已有审计见 B_audit/分析报告.md。两人先以附件 2 联调。

队友负责第一、二问的数据重构、时延、图表与初稿。另一人负责第三问预测、逐炉验证和论文整合。共享接口和具体任务见 docs/队友提示词.md。

## 数据与运行

当前十炉文件位于 `work_b/Data/`，其中附件 1 是主办方修订版。旧附件 1 保留在 `work_b/legacy/`，导出与核查见 [炉次接口](q1_q2/heat_interface.md)。第二问当前十炉图表与时延请使用下方独立命令。

`B_audit/` 中的分析报告和结果表对应附件修订前的数据。如需复现整套历史审计，在旧版提交（如 `a1006a1`）的独立工作目录中安装根目录依赖后运行：

    python B_audit/extract.py
    python B_audit/analyze.py
    python B_audit/sensitivity.py
    python B_audit/spectra.py
    python B_audit/report.py

生成的 .npy、逐炉 JSON 和本地依赖不纳入 Git。历史审计脚本会覆盖其工作目录下的同名结果，包括第三问原先使用的时延表。

## 前两问正式图表复现

从仓库根目录运行以下命令。默认从十份原始 XLSB 读取数据，生成第一问光谱重构及遮点验证、第二问六联图及流量和时延核查。

    python -m pip install -r q1_q2/requirements.txt
    python -m q1_q2.reconstruct

已有炉次接口导出时可加 `--exports PATH`。默认生成文件在 [前两问结果索引](q1_q2/results/README.md) 所列目录，可用 `--output PATH` 另存。需要逐炉完整的原始和重构张量、修复掩码、触顶标记及连续过程曲线的绘图采样值时，加 `--reconstructed PATH`。该选项输出的是离线分析归档，第三问仍使用原接口导出的在线特征。

使用已有 NPZ 目录重跑当前版本时，将其中旧的 `6B03205.npz` 换成 [已核验的新版导出](q1_q2/exports/6B03205.npz)。

## 第三问复现

从仓库根目录用当前十份 XLSB 和对应的十炉时延表重跑。暂用独立输出目录，避免覆盖合稿所引用的历史九炉实验图表。

    python -m q3.predict --lags q1_q2/results/signed_lags_current.csv --output q3/results-revised
    python -m q3.plot_results --results q3/results-revised

已有炉次接口导出时，可加 `--exports PATH` 并确认使用新版 `6B03205.npz`。脚本仍只在训练炉内汇总候选时延。历史第三问使用的 `B_audit/signed_lags.csv` 和成绩保留供追溯。

第三问的建模口径、逐炉结果和限制见 [第三问论文稿](q3/第三问论文稿.md)，三问的正文衔接见 [论文整合稿](docs/论文整合稿.md)。`summary.csv` 为分气体宏平均，`validation.csv` 为逐炉指标，`weights.csv` 为各折组合权重及时延，`contrasts.csv` 为配对误差比较，`predictions.csv` 为逐时刻预测。

## 共同约定

- 旧附件 1 的烟气全零，历史实验排除其标签。新版附件 1 的 1479 条烟气标签均通过基本筛查，可以用于更新后的逐炉验证。
- 跨炉光谱按真实波长对齐。附件 5 记录较短，单独分析。
- 逐炉留出，使用与附件版本匹配的标签和时延候选。标准化、降维和调参仅用训练炉。预测特征仅用当前及过去信息。
- 同刻和提前 10 秒实验使用同一目标时刻。时延相关峰不直接视为输运时间真值。
- 修改不同文件，提交前检查 git status，拉取远端变更后再推送。
