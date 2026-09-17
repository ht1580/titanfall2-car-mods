# TitanfallModWorkbench 1.5.0

本版新增“全自动替换”：扫描 Apex 武器皮肤与 Titanfall 2 武器模型后，可直接选择来源和目标并生成 Northstar 模组。

自动流程包括：RSX 2.3 资产索引、兼容 RSX SMD 导出、Harmony LZHAM VPK 提取、Crowbar v53 QC/动画恢复、骨架名称映射、松散 VTF/VMT、StudioMDL、MDLShit v53、第一人称原版 RUI 固化、第一/第三人称模型及 ZIP 打包。

验证结果：

- 索引：Apex 3,065 个武器皮肤；Titanfall 2 82 个第一人称目标。
- 源码模式完整生成：第一人称与第三人称均成功，两个模型均为 v53。
- 独立 EXE 完整生成：退出码 0，成品 ZIP 与审计文件存在。
- 生成模组不包含 weapon 脚本、RPak、外置 VVD/VTX；LoadPriority 为 0。
- 游戏内运行未代替用户测试，状态保留为 `NOT_TESTED`。

GUI 使用：打开“全自动替换”，先扫描，筛选并选择 Apex 来源与 TF2 目标，填写输出目录后执行。

CLI：

```powershell
TitanfallModWorkbench.exe --scan-assets
TitanfallModWorkbench.exe --auto-replace D:\path\recipe.json
```
