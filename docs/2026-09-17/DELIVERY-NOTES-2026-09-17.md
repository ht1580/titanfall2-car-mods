# 神话皮与双重击动画/特效交付说明

## 神话皮 1.2.0-animatedfx

- 第一人称恢复三条互不挂接到普通 CAR 动作的循环序列：`mythic_motion`、`mythic_eye_motion`、`mythic_wing_motion`。
- 第三人称保留核心循环 `mythic_motion`。
- 眼睛、翅膀和核心继续使用原 Apex 骨骼权重；枪身与原 CAR 动作保持原关系。
- 发光采用随网格和骨骼移动的 `UnlitTwoTexture` 材质，使用 `Sine` 与 `TextureScroll` 代理产生脉冲和流动。
- 删除旧包中的自定义 PCF、粒子清单和客户端粒子挂载脚本，避免再次触发 `Invalid particle system index`。
- 保留 RePak 1.2 生成的纹理/材质分包，`LoadPriority` 为 0。

## 双重击 1.0.8-animatedfx

- 保留原版双重击的可选瞄具、弹药 RUI、镜内准星 RUI 和 pro-screen RUI；模型内共有 5 个 RUI 记录。
- 三个 Apex 转环分别保留独立骨骼，并使用 `hunter_rotors_autoplay` 循环旋转。
- 根据 Hunter Safari 的 ILM 与 UV 生成动态发光覆盖层：第一人称 660 个三角面，第三人称 94 个三角面。
- 动态层使用 `Sine` 与 `TextureScroll`，没有使用全屏 `_rt_Camera`，避免影响地图画面图层。
- 没有覆盖 `mp_weapon_doubletake.txt`，原版瞄具和 UI 逻辑继续由游戏数据提供。
- 保留 RePak 1.2 生成的纹理/材质分包，`LoadPriority` 为 0。

## 静态检查

- 两个 MDL 均完成 StudioMDL 编译和 MDLShit 转换。
- 神话皮独立序列标志包含 `delta + autoplay`；双重击转环序列包含 `loop + autoplay`。
- 两个 ZIP 均通过完整性检查，包内没有 PCF 或 Gnut 粒子挂载脚本。
- 双重击编译器自动拆分了顶点数较高的第一人称网格；这是 StudioMDL 的成功编译提示，不是失败。还保留了一条原模型已有的重复附件参数警告。
- 未启动游戏，运行时表现需由实际游戏确认。

## 参考流程

- Northstar MDL Modding: https://docs.northstar.tf/Modding/guides/tools/MDLModding/
- Northstar RPak Modding: https://docs.northstar.tf/Modding/guides/tools/rpakmodding/
- RePak: https://github.com/r-ex/RePak
- 本地参考：B3 小帮手进化皮与 CNS144 R301 神话皮；两者的稳定动态效果均以模型序列/VMT 代理为主。
