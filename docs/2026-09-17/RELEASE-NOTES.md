# Animated FX + TitanfallModWorkbench 1.4.0

本次交付把 CAR 神话皮与双重击 Hunter Safari 的动画、发光、内嵌 RUI 和静态核对流程固化为可重复执行的 Recipe。

## 模组成品

- `CAR.Mythic.Allfather-1.2.0-animatedfx.zip`
  - SHA-256: `6B56294AFB4B51D6ACE03C800A4F46D4B926EC9A26562A1C648AE3417B312B3D`
  - 第一人称序列：`mythic_motion`、`mythic_eye_motion`、`mythic_wing_motion`
  - 第三人称序列：`mythic_motion`
- `Codex.DoubleTake.HunterSafari-1.0.8-animatedfx.zip`
  - SHA-256: `1244CC5A96CB0F210085D4542D9A2B04A7FDB1CAF65F2F08EA3D0DC508E956CC`
  - 转环序列：`hunter_rotors_autoplay`
  - 保留 5 条第一人称内嵌 RUI；不覆盖原版武器数值。

## 工具与源码

- `TitanfallModWorkbench-1.4.0.exe`
  - SHA-256: `27F832E2EF5C74AAC7F5956019772BA571003AB3B9441EAE55FC1DCAA6E9563A`
- `TitanfallModWorkbench-1.4.0-Source.zip`
  - SHA-256: `42CBBEC675951E7DD9FBE1734BD196EA524E4F5E2458B6EFAF69049AFF99BFC8`
- `AnimatedFX-Complete-Source-2026-09-17.zip`
  - SHA-256: `A72B023188D60799C4BAC002DA1724B6B689F5F4E8C2ABCAEDD04378A7710836`
  - 包含展开后的两套模组、QC/SMD、贴图中间产物、编译日志、预览 `.blend`、自动化脚本、Workbench 源码与 EXE、双重击原始材质。

## 验证范围

- EXE `--self-test` 退出码 0。
- EXE 分别执行两份实际 `--run-fx-recipe`，退出码均为 0。
- 四个 ZIP 均通过中央目录与 CRC 完整性检查。
- 完成 MDL v53、预期序列、内嵌 RUI 数量、VMT `_rt_Camera`、PCF manifest 和脚本静态风险核对。
- 未启动游戏；画面位置、实际发光强度、音效与所有动态状态仍需实机验收。

