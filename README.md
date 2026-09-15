# Titanfall 2 CAR 模组

这里保存目前整理完成的 Northstar / R2Vanilla CAR 替换模组安装包。

## 当前版本

- `CAR.Mythic.Allfather-1.1.0.zip`：CAR 神话皮版本；第一人称将核心、眼睛和左右翅膀拆为三个独立循环动画，枪身保持固定；第三人称保留核心循环，避免重新引入翅膀错位。枪口弹道与枪口特效起点沿枪管向后移动 0.65 模型单位。
- `CAR.OutlandsAnnihilator-1.0.10.zip`：CAR 外域毁灭者版本，保留静态计数器和 1.0.9 不透明材质修复；枪口弹道与枪口特效起点沿枪管向后移动 0.65 模型单位。
- `CAR.RichMahogany-1.1.10.zip`：CAR 桃心花木版本，包含机瞄绑定修正。

三个 CAR 替换模组互斥，同一时间只启用一个。

## 安装

1. 关闭游戏和 Northstar。
2. 解压需要使用的 ZIP。
3. 将解压得到的模组文件夹放入 `Titanfall2/R2Vanilla/mods/`。
4. 移走或禁用另外两个 CAR 替换模组以及旧版本，避免模型、材质或脚本相互覆盖。
5. 启动 Northstar。

这些包的 `LoadPriority` 均按当前兼容方案设置为 `0`。本轮只做了资源结构、模型引用、材质路径和打包内容核对，尚未代替用户进行游戏内验证。

## 文件校验（SHA-256）

```text
7C366931C0969E26D3CC9EDC5FE134E393039243E9A8DEF65A03A0345136956D  CAR.Mythic.Allfather-1.1.0.zip
07AD35CF1BB6726247336276A412CBE7120C6A0C136E1849AFD62BEEECAE0776  CAR.OutlandsAnnihilator-1.0.10.zip
B82660255C62D75618EC15D0E6181DA8CD42F57812D47FFDD20E742BD8D8280D  CAR.RichMahogany-1.1.10.zip
```

详细核对记录位于 `docs/`。

## 原始制作资料

完整制作资料作为 Release 附件提供：

- [`CAR-Source-and-Final-Resources-2026-09-14.zip`](https://github.com/ht1580/titanfall2-car-mods/releases/download/v2026.09.14/CAR-Source-and-Final-Resources-2026-09-14.zip)
- 大小：521,575,582 字节
- SHA-256：`04E73F074C59B96F28CFCBD1B1DB681DCDA5BAED82521ECE3687B320B6C1F035`

主资料包包含制作工具、自动化脚本、SMD/QC、Blender 预览、模型和材质制作资源，以及三个展开后的模组和安装包。

RePak 1.4 更新后的脚本、map、材质、RPAK、1.0.8 成品和 Titanfall Mod Workbench 1.3.0 位于 Release 附件 [`CAR-RePak-1.4-Source-Update-2026-09-14.zip`](https://github.com/ht1580/titanfall2-car-mods/releases/download/v2026.09.14/CAR-RePak-1.4-Source-Update-2026-09-14.zip)，SHA-256 为 `1F5E76A35D4A4514DB43F1EF7F6122BEA39003F3443DD81F92089F1F1C8CA16A`。

外域毁灭者 1.0.9 的暗处泛白修复脚本、材质 JSON/UBER 和核对记录位于 [`CAR-Outlands-Material-Fix-Source-1.0.9.zip`](https://github.com/ht1580/titanfall2-car-mods/releases/download/v2026.09.14/CAR-Outlands-Material-Fix-Source-1.0.9.zip)，SHA-256 为 `11A101890A5AADC75C7629DC8C0F27A5B41374DAE8BD3AE851AF18043D7F21C1`。

两套 1.0.10 模组的枪口附件源 QC 与核对记录位于 [`CAR-Muzzle-Attachment-Source-1.0.10.zip`](https://github.com/ht1580/titanfall2-car-mods/releases/download/v2026.09.14/CAR-Muzzle-Attachment-Source-1.0.10.zip)，SHA-256 为 `B9B336E4CD4C202828B9443FB02F3BB586F559F3F7618EBD02F1907ADB91B7B5`。

神话皮 1.1.0 的独立动画脚本、SMD/QC、绑定核对和 Blender 动画预览位于 [`CAR-Mythic-Independent-Animation-Source-1.1.0.zip`](https://github.com/ht1580/titanfall2-car-mods/releases/download/v2026.09.14/CAR-Mythic-Independent-Animation-Source-1.1.0.zip)，SHA-256 为 `A970161F7EED038C055028E7679E8F62971C7EA3CA9503ECD4574649EDB693BF`。

神话皮 1.0.9 的 PCF 文本源、已编译 PCF、Northstar 粒子清单、客户端挂载脚本和带 VFX 挂点的 QC 位于 [`CAR-Mythic-PCF-Source-Update-1.0.9.zip`](https://github.com/ht1580/titanfall2-car-mods/releases/download/v2026.09.14/CAR-Mythic-PCF-Source-Update-1.0.9.zip)，SHA-256 为 `92689514E04F87EC051FA9B38E6D85EC29A8D392AB60518E41AB78CB3620663A`。

可直接下载 [`TitanfallModWorkbench-1.3.0.exe`](https://github.com/ht1580/titanfall2-car-mods/releases/download/v2026.09.14/TitanfallModWorkbench-1.3.0.exe)。Workbench 1.3.0 的 GUI 默认使用 RePak 1.4，仍可选择 1.2 兼容旧 map。
