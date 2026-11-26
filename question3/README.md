# 第三问十炉复现

主实验和补充实验读取同一批炉次。附件 1 使用主办方修订版本，原始 1,479 条烟气标签均通过基本筛查。时延来自 q1_q2/results/signed_lags_current.csv，每折只汇总训练炉候选。

从仓库根目录执行：

    python -m pip install -r paper/requirements.txt
    python -m question3.reproduce
    python paper/build_pdf.py apmcm26315849

第一条安装运行依赖。第二条从 work_b/Data 下的十份正式 XLSB 导出临时 NPZ。与正文相配套的数值、配对表和图写回各自的 results 目录。已有修订后的完整十炉 NPZ 可传入 --exports PATH。复现流程先用两套实际入口验证炉号、标签标记和附件 1 的核对点。

## 评价口径

- 主分析从目标时刻 10 s 起评分，同刻与提前 10 s 的模型使用相同的 13,389 个炉次–目标时刻。各炉单独计算 MAE 后十炉等权。
- 配对检验从目标时刻 30 s 起评分，覆盖 12,989 个炉次–目标时刻。供氧历史模型及其加入光谱的版本使用相同的训练权重、岭惩罚和目标，过程模型逐条与本轮主实验预测核对。
- 补充光谱基线按行等权训练。固定惩罚的历史对照、嵌套窗口选择以及触顶和时延敏感性实验均使用十炉。所有外层实验每折留一炉，内层只用剩余训练炉。
- 历史冻结预测另用 a1006a1 的预测和新版标签评分，结果单列。原始九炉稿和结果可从 a1006a1 追溯。

## 结果

- [两组比较的十炉宏 MAE、改善炉数和配对重采样区间](results/paired_summary_10s.csv)
- [两组比较的逐炉差值](results/paired_by_heat_10s.csv)
- [固定惩罚的补充模型](results/metrics.csv) · [嵌套窗口结果](results/window_selection.csv)
- [触顶敏感性](results/clip_test_10s.csv) · [训练炉时延敏感性](results/lag_test_10s.csv)
- [修订前附件 1 冻结预测的补评分](results/frozen_attachment1_10s.csv)
- [英文合稿](../paper/manuscript-en.md) · [主分析逐炉指标](../q3/results/validation.csv)
