# Titanfall Mod Workbench

## 1.5.0 全自动武器替换

“全自动替换”页会扫描 Apex `common.rpak` 中的武器皮肤设置，并扫描 Titanfall 2 VPK 中的第一人称/第三人称武器模型。选择一个来源皮肤和一个替换目标后，程序自动执行：

1. 用 RSX 2.3.0 建立当前 Apex 资产索引，并用兼容版 RSX 导出 SMD；
2. 用 Harmony 解压目标 v53 MDL，再由 Crowbar 自动恢复完整 QC、射击、换弹和切枪动画；
3. 将 Apex 网格映射到目标骨架，缺失的装饰骨向最近可用祖先绑定；
4. 生成独立 VTF/VMT 材质，不写全局 RPak 图层；
5. 用 StudioMDL 与 MDLShit 生成单文件 v53 MDL，并从原版目标继承模型 RUI；
6. 以原版模型路径封装 Northstar Mod 和 ZIP，固定 `LoadPriority: 0`，不写 weapon 脚本。

首次使用先配置 Apex、Titanfall 2、SFM/StudioMDL 路径，然后点“扫描 Apex + Titanfall 2”。命令行等价入口：

```powershell
TitanfallModWorkbench.exe --scan-assets
TitanfallModWorkbench.exe --auto-replace D:\path\recipe.json
```

模板见 `auto-replace-recipe-template.json`。程序完成的是离线生成和静态结构核对；游戏内位置、遮挡和动作观感仍需使用者验收。

一个可以脱离 Codex 使用的 Windows 图形工具，整合 Apex / Titanfall 2 武器模型移植中重复、容易出错的步骤。

## 已整合功能

- 自动寻找 Apex、Titanfall 2、R2Vanilla、Source Filmmaker、StudioMDL 和 Blender。
- 内置 RSX 命令行版，支持 RPak 补丁链、GUID/名称筛选、模型皮肤序号、SMD/CAST/RMDL 导出和 CSV 资产表。
- 内置未压缩 Titanfall 2 VPK 解包器；遇到 LZHAM 时可直接打开随程序附带的 Harmony VPK Tool。
- 内置 SMD 骨骼名称映射、材质名替换和 TF2 细节材质面保留。
- Blender 后台一键流程：骨架映射、位置/旋转/缩放/镜像、SMD 导入导出、`.blend` 保存和 PNG 预览渲染。
- 贴图编辑：尺寸、亮度、对比度、饱和度、法线绿通道翻转，以及缺失 PBR 通道的安全默认图生成。
- 同时输出 Source VTF/VMT 与 RePak DDS/map；RePak 成品会自动装入 Northstar `paks` 并生成注册文件。
- 内置脚本编辑器支持撤销、旧文件备份和只读用途的中文辅助翻译；可编辑本地 JSON 词典扩充术语。
- 从素材暂存目录自动生成 `mod.json`、保持默认 `LoadPriority: 0`、静态核对并打包 ZIP。
- 调用 StudioMDL 编译，再用 MDLShit 转换为 Titanfall MDL v53。
- 内置 RePak 1.2 与 1.4；按当前模组兼容策略，新项目和图形界面默认使用 1.2，同时内置 TexConv、Legion+ 和 Crowbar。
- Northstar 模组静态核对、重复模组名扫描、松散文件冲突扫描、ZIP 打包、自动备份安装和安装后哈希核对。
- B3 桃心花木与 CAR Rich Mahogany 当前 Apex 模型的提取预设。
- 动画/特效 Recipe：按 ILM 与 UV 自动生成随骨骼移动的发光覆盖层，写入安全的 `Sine`/`TextureScroll` VMT，追加幂等的 `autoplay` 序列，并按骨骼名称恢复 MDL 内嵌 RUI。
- 特效静态审计会检查脚本 `Path`/`RunOn`、缺少粒子清单的 PCF、可能污染屏幕图层的 `_rt_Camera`、动画序列和最低 RUI 数量。模型/VMT 可以完成的效果不会自动生成 Gnut 或 PCF。

## 使用顺序

1. 在“环境与工具”点击“自动检测”，核对游戏、SFM 和 Blender 路径。
2. 在“资产解包”选择预设或输入资产 GUID，导出 SMD。当前 Apex 模型推荐保持“跳过动画后处理”。
3. 在“模型与打包”把 Apex SMD 映射到一个已验证的 TF2 SMD 骨架，并填写独立材质路径。
4. 编辑或生成 QC 后依次执行 StudioMDL、MDLShit 和 RePak。
   也可以点击“一键执行全部已填写步骤”，自动串行完成 Blender、StudioMDL、MDL v53 和 RPak。
5. 在“Northstar 成品”核对模组、扫描冲突、生成 ZIP，然后备份并安装。

配置、报告和安装备份保存在：

`%LOCALAPPDATA%\TitanfallModWorkbench`

## 本次流程固化的经验

- 模型与材质是两条独立链。外观看起来粗糙时，先比较三角面和顶点，再检查 albedo、normal、gloss、specular、AO 和 cavity，避免无效地重复换模型。
- RSX 的无界面模式必须传 `--loadwhitelist`。当前 Apex 的模型导出可使用 `-skippostload --loadwhitelist mdl_`，否则动画后处理可能失败。
- 同一模型的皮肤序号必须从模型的 skin family 核对。当前桃心花木的 `Raygun retheme` 是序号 2。
- Apex 新模型增加骨骼时，必须按骨骼名称重映射，不能直接沿用骨骼编号；未参与蒙皮的辅助骨骼可以丢弃。
- TF2 专用的极小细节材质面有时承担扳机或材质引用作用。映射时可以从已知正常的参考 SMD 保留指定材质面。
- Northstar 的 `LoadPriority` 不能代替冲突控制。武器 keyvalues 应只包含模型/RUI 真正需要的键，避免重新声明伤害、后坐力、ADS 和其他模组变量。
- MDL v53 只保存材质路径；VTF/VMT 或 RPak 材质是独立文件。RPAK 需要在 `paks/rpak.json` 中正确注册，并与 STARPAK 配对。
- 静态核对只能证明结构、版本、签名和文件一致性。最终位置、动画、透明穿模和 RUI 仍需在游戏中观察。

## 构建

在 PowerShell 中运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

输出：`dist\TitanfallModWorkbench.exe`

构建后可运行 `TitanfallModWorkbench.exe --self-test`。结果写入
`%LOCALAPPDATA%\TitanfallModWorkbench\logs`，用于确认单文件 EXE 解压后的内置工具路径有效。

重复项目可以复制 `project-template.json`，填写路径和参数后执行：

```powershell
TitanfallModWorkbench.exe --run-project D:\mods\my-weapon.json
```

相对路径以 JSON 文件所在目录为准；执行报告仍写入程序日志目录。

独立动画与发光流程可以复制 `animated-fx-recipe-template.json`，然后在 GUI 的“动画 / 发光特效 / RUI 固化流程”执行，或运行：

```powershell
TitanfallModWorkbench.exe --run-fx-recipe D:\mods\my-weapon-fx.json
```

Recipe 的每一步均可省略。工具只生成资源和静态审计，不安装模组，也不启动游戏。
