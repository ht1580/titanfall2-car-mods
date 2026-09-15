# Titanfall 2 CAR 模组

这里保存目前整理完成的 Northstar / R2Vanilla CAR 替换模组安装包。

## 当前版本

- `CAR.Mythic.Allfather-1.0.8.zip`：CAR 神话皮版本。
- `CAR.OutlandsAnnihilator-1.0.8.zip`：CAR 外域毁灭者版本，保留静态计数器；使用官方 RePak 1.4 新格式重建，并修正 DDS 压缩与 sRGB 标记。
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
5D77E20F6A4C2DFE21D819E820BDA1FC2B8D4C4E65354175075528B9976A2DDC  CAR.Mythic.Allfather-1.0.8.zip
0F675B6A5C48FB3AC9ACC056E39A99FF12E7B9D7EA2D747D29BAD8F1168BDA1A  CAR.OutlandsAnnihilator-1.0.8.zip
B82660255C62D75618EC15D0E6181DA8CD42F57812D47FFDD20E742BD8D8280D  CAR.RichMahogany-1.1.10.zip
```

详细核对记录位于 `docs/`。

## 原始制作资料

完整制作资料作为 Release 附件提供：

- [`CAR-Source-and-Final-Resources-2026-09-14.zip`](https://github.com/ht1580/titanfall2-car-mods/releases/download/v2026.09.14/CAR-Source-and-Final-Resources-2026-09-14.zip)
- 大小：521,575,582 字节
- SHA-256：`04E73F074C59B96F28CFCBD1B1DB681DCDA5BAED82521ECE3687B320B6C1F035`

主资料包包含制作工具、自动化脚本、SMD/QC、Blender 预览、模型和材质制作资源，以及三个展开后的模组和安装包。

RePak 1.4 更新后的脚本、map、材质、RPAK、1.0.8 成品和 Titanfall Mod Workbench 1.3.0 位于 Release 附件 `CAR-RePak-1.4-Source-Update-2026-09-14.zip`。Workbench 1.3.0 的 GUI 默认使用 RePak 1.4，仍可选择 1.2 兼容旧 map。
