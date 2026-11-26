# 炉次接口 v1

## 附件 1 修订

默认输入 `work_b/Data/Attachment 1. Heat No. 6B03205.xlsb` 为主办方修订版，收到时的文件名为 `附件1.炉号-6B03205.xlsb`。旧版原文件保留在 `work_b/legacy/Attachment 1. Heat No. 6B03205.xlsb`。导出器接受两版表头，NPZ 字段及 CO₂、CO 顺序相同。

共享导出为 [6B03205.npz](exports/6B03205.npz)。全炉 1479 个 0.5 s 时刻均通过烟气标签基本筛查，可参与评分。按原始序号（从 1 开始），第 500、501、1300 条的 (CO₂, CO) 分别为 (18.71, 31.96)、(18.71, 31.96)、(12.64, 42.14)。新旧导出的时间、实际波长、光谱、累计氧、后向流量和光谱质量标记逐项相同。历史实验中旧版的两列烟气全零，旧版标签仍全部判为不可评分。

从仓库根目录复现，指定一个新的输出文件名：

```powershell
python -m q1_q2.export_heat "work_b/Data/Attachment 1. Heat No. 6B03205.xlsb" "../6B03205-revised.npz"
```

## 接口字段与联调示例

从仓库目录运行。指定新的 NPZ 文件名；脚本会回读并逐字段比较。依赖 numpy、pyxlsb==1.0.10。示例假定工作区布局与本次联调相同。

```powershell
python -m pip install numpy pyxlsb==1.0.10
python q1_q2/export_heat.py "work_b/Data/Attachment 2. Heat No. 6B03206.xlsb" "../6B03206-check.npz" --window 1
```

```python
import numpy as np

with np.load("../6B03206-check.npz", allow_pickle=False) as d:
    print(d["heat_id"].item(), d["spectrum"].shape)
    clipped = (d["quality_flags"] & 2) != 0
    print(d["time_s"][[0, -1]], clipped.sum())
```

| 字段 | 形状和含义 | 在预测时刻 t 的可用性 |
|---|---|---|
| heat_id | 标量，工作表炉号 | 炉次标识，仅用于分组 |
| time_s | T，按原序号从 0 起每步 0.5 s | 当前 |
| wavelength_nm | W，原工作簿波长表头，nm | 当前炉仪器配置 |
| spectrum | T × W，原始强度，单位按题面 W/cm² | 当前及过去 |
| oxygen_cumulative | T，原始累计耗氧量，m³，含起始读数 | 当前及过去 |
| oxygen_flow | T，(V[i]−V[i−k])/(0.5k)，m³/s，时间戳对应右端点；前 k 点 NaN | 当前及过去。k=1 为接口基线，未做平滑 |
| flow_window_steps | 标量 k，可用 --window 指定 | 固定参数 |
| co2、co | 两个长度 T 的原始序列，按题面解释为瞬时体积流量 m³/s | 延迟测量；用于构建标签，使用时需记录预测目标时刻 |
| quality_flags | T × W 的 uint8 位掩码，1 非有限值，2 恰为 65535，4 负强度，0 表示以上检查均未触发 | 逐点生成，可在线取得。触顶只记录候选截幅 |
| gas_label_eligible | T 的布尔数组，单行须非负且有限，整炉双气体全零时全为假 | 整炉事后标签筛查，不能作预测输入 |

所有连续原始量使用 float64。逐炉原坐标导出，无跨炉拟合。这里未做离线光谱平滑，后续双侧滤波、跨时刻插值或用全炉均值归一化的结果须另存并标明使用未来数据。相邻通道整条轨迹相同与波长表头重复分别检查。烟气标签为真仅表示通过基本筛查。

k=1 时用右端点流量乘对应区间时长，求和后与末值减初值核对；更长窗口的移动平均会改变首尾覆盖。附件 2 的首个累计读数为 2.07 m³，末值 3321.13 m³，积分核对目标为 3319.06 m³。

绘制原始过程诊断六联图需要 reportlab。运行 `python q1_q2/plot_process.py "../6B03206-check.npz" "../6B03206-process.svg"`。排放量以首条记录为零点，按相邻烟气流量作梯形积分；全零炉次仅展示记录积分。十炉数值核查见 q1_q2/heat_checks.csv，累计量的差分积分闭合只验证索引及单位换算。

