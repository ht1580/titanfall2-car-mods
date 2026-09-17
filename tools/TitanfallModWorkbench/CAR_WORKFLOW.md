# CAR 制作与交付流程（2026-09-16）

## 当前交接状态

外域毁灭者 1.0.13-rui：ZIP/MDL 结构通过，弹药数字未解决。此前 pro_screen/ui8/bodygroup5 补丁操作的是击杀计数器，不能称为弹药 RUI 修复。

神话皮 1.1.5-rigidglow：取消独立装饰动画，眼睛/翅膀装饰刚性绑定枪身；含材质发光层，无 PCF。位置和光效等待实机确认。两个包均不能标记为最终验收通过。

当前报告：D:/TitanfallMods/13_FinalAudit_20260916/FINAL-AUDIT.md。

## 固定顺序

1. 根据实际成品版本及哈希选择输入，不以工作目录时间判断最新。原包、原模型、源贴图保留在 D 盘。明确第一/第三人称、基础/进化、换色范围。
2. 模型编辑保留弹匣和瞄具独立控制。眼睛/翅膀重绑时保持装配坐标，核对权重与逆绑定矩阵。对照编译后的模型；源 SMD 正确不代表转换后的模型正确。
3. RUI 单独验收：弹药面板绑定 weapon_ammo；Pro Screen 绑定 proscreen_int0。分别检查 UI 配置、合并后的武器配置、RUI 顶点/朝向/UV、父骨骼和遮挡。只查名称、数量或 bodygroup 不够。不能照搬其他武器的 UI 槽编号。
4. 材质从原始图重建。nml 使用 BC5、gls 使用 BC4；颜色图的 sRGB 输入/输出必须明确，数据遮罩按材质语义处理。解码最终包内贴图与原图比较，不能只查 DDS 头，不能靠统一压暗掩盖重复 gamma。
5. 光效分别记录材质发光与 PCF 粒子。VMT 存在、亮度参数增大或 Blender 发光均不能证明 TF2 已显示。全局 particles_manifest 覆盖需与原版完整比较，不把删掉 PCF 写成粒子修好。
6. 编译后核对 MDL v53、文件长度、骨骼索引、权重、RUI、bodygroup、换色、材质引用、枪口位置、RPak 依赖。已有精细二进制审计脚本继续使用；本工具的交付审计不替代它们。
7. 以独立的新版本目录打包，LoadPriority=0，不覆盖其他模组变量。相同 CAR 路径的替换包一次只启用一个；优先级为 0 不代表没有冲突。精简按引用关系做，不按文件名猜测删除。
8. 发布只称候选包：自动报告 static_structure_only / NOT_TESTED / PENDING。用户实机确认进图、弹药数字、计数器、开镜、换弹、机瞄、眼睛绑定、暗处材质和发光后，再在独立验收记录中登记版本/哈希/场景/反馈。

## 不通过 Codex 使用

运行现有工作台 app.py，模组校验自动附加 workflowReview，打包自动生成 ZIP.audit.json。此文档不意味着历史脚本已全部改造；旧 car_evolution_pipeline.py 等直接打包入口仍须补跑以下命令。

```powershell
python workflow_audit.py "D:\TitanfallMods\01_最新安装包\CAR.OutlandsAnnihilator-1.0.13-rui.zip" --output "D:\TitanfallMods\13_FinalAudit_20260916\outlands-workflow.json"
```

脚本只读取目录或单模组 ZIP，不启动游戏、不安装、不自动删文件。打包入口拒绝覆盖旧 ZIP、拒绝把 ZIP 写回模组目录。报告中的资源存在性不等于视觉效果通过。
