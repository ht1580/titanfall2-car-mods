# Titanfall 2 CAR 模组

这里保存目前整理完成的 Northstar / R2Vanilla CAR 替换模组安装包。

## 当前版本

- `CAR.Mythic.Allfather-1.0.8.zip`：CAR 神话皮版本。
- `CAR.OutlandsAnnihilator-1.0.6.zip`：CAR 外域毁灭者版本，保留静态计数器。
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
B8D06D75755E4DCFD771A5018FE9AB43BB29B892EBF502877BBE89AFB1461A8D  CAR.OutlandsAnnihilator-1.0.6.zip
B82660255C62D75618EC15D0E6181DA8CD42F57812D47FFDD20E742BD8D8280D  CAR.RichMahogany-1.1.10.zip
```

详细核对记录位于 `docs/`。
