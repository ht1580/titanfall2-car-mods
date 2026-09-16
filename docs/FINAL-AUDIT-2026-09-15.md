# 两套 CAR 成品核对与降档交接

核对时间：2026-09-15。没有启动游戏；本轮没有修改、覆盖或重新安装两套成品。按用户要求，在已定位问题、适合交给低用量模型继续实施的位置暂停。

## 结论

| 成品 | 本次结论 |
| --- | --- |
| 外域毁灭者 1.0.11 | 已检查的贴图像素、DDS 格式、RPak 分段、模型权重、机瞄绑定和资源路径未发现新的缺失；游戏内暗处效果及零 GUID 材质回退仍待确认。不能把此结果等同于游戏验收。 |
| 神话皮 1.1.1 | **不通过最终核对**。确认成品 RPak 仍含被提亮的底色；客户端粒子脚本的句柄类型与清理调用不匹配。尚未生成 1.1.2，不能让下一位误认为修复已完成。 |

## 两套共同通过的静态项目

- 成品 MDL 为 53 版；本次遍历顶点，骨骼索引、权重总和和顶点数值检查通过，未发现 NaN/无效权重。
- 机瞄模型权重全部在 `def_c_base`：外域第一/第三人称分别 2249/546 顶点，神话 5341/552 顶点。这里仅证明枪身绑定；不能承诺开火时画面完全不动，枪身动画和镜头反馈仍可能影响视觉。
- `muzzle_flash` 附件局部位移为约 `(0, 0.65, 0)`，此前枪口向枪身后移的改动保留。
- `LoadPriority=0`。外域包 6 张纹理、2 个材质；神话包 80 张纹理、48 个材质。两个 RPak 的页与分段分配核对均不需要补齐。
- 自定义材质路径都能对应到包内材质或本地 VMT。但四个模型各有一条材质的存储 GUID 为 0：外域 `car_outlands`，神话 `main_base_default`。对应名称的 `_skn`/`_fix` 哈希均在 RPak 资产表中，故不是缺少材质资源；是否依赖正常的路径回退仍未进行运行时确认，不能静默略过。

## 外域 1.0.11

上一轮 `rebuild-audit.json` 记录底色误差已从约 59/255 降至 0.08/255，使用明确的输入、输出 sRGB 转换。nml 为 BC5，gls 为 BC4，col/spc 为 BC7 sRGB，AO/cavity 为线性数据。模型和脚本哈希与 1.0.10 保持一致；恢复静态计数器、不带进化动画的方案保留。

正确的新成品在 `D:\TitanfallMods\01_最新安装包\CAR.OutlandsAnnihilator-1.0.11.zip` 或完整交接包的 output 中。`D:\TitanfallMods\CAR.OutlandsAnnihilator` 这个旧展开目录仍是 1.0.10，核对和安装时不要拿错。

## 神话 1.1.1 的明确问题

1. **底色重复编码仍在最终包中。** 实际 DDS 的数据片段已在成品 RPak 中找到，不是只看旧工程。眼睛源图 RGB 均值约 66/66/67，DDS 变为 134/134/134；其中一套羽毛由 57/53/60 变为 129/125/133。12 张底色的逐图结果见 `final-resource-audit.json`。主枪身一些图还包含既往补偿，不能只把所有 DDS 再统一压暗。
2. **粒子清理代码接口混用。** `array<entity> activeEffects` 存放 `StartParticleEffectOnEntity_ReturnEntity` 的结果，然后用 `IsValid` 和单参数 `EffectStop(effect)` 清理。客户端参考代码使用整数粒子句柄、`EffectDoesExist(handle)` 和 `EffectStop(handle, false, true)`。已核实两个回调名称及 `entity player`/`entity selectedWeapon` 参数是有依据的；不要误删正确的回调。`ReturnEntity` 在 Northstar 服务器相关脚本中有使用，本次没有确认它是客户端可用接口，不能只因查到同名调用就认定兼容。
3. **附加待核对项**：切枪短时间内重复触发线程、死亡/视图模型销毁后的清理、特效是否应随 pro_screen 进化开关更新。当前脚本只检查武器类型，未检查进化状态。

## 神话皮已具备的资源与实际边界

- 第一人称 100 个序列中存在 `mythic_motion`、`mythic_eye_motion`、`mythic_wing_motion` 三个独立循环层；第三人称保留核心层。普通序列没有再重复引用这些独立层。源权重核对脚本执行通过。
- 这些是已构建的重建动画，不能宣称是 Apex 完整动画原封不动移植；动态效果是否自然仍需用户反馈。
- PCF 文件及清单存在，眼睛、核心挂点存在；VMT/VTF 发光层存在。**资源存在不等于游戏里已经发光**，粒子脚本问题仍需修正。
- 11 组开火/换弹音效事件及 WAV 都在成品中，PCM16 / 48kHz 格式核对通过；实际触发和时序同步未代测。
- `pro_screen` 设置 `ui8_enable=0`，保留作为进化版本开关的方案。原始 MDL 内仍保留相关 RUI 定义，不能把“UI 被禁用”写成“所有 RUI 已从模型删除”。

## 下一位按此顺序继续

1. 先修粒子句柄链路：客户端使用 `array<int>`、`StartParticleEffectOnEntity`、`EffectDoesExist` 和带两个布尔参数的 `EffectStop`；保留已核实的回调签名。加入清晰的线程生命周期/过期请求处理，避免重复特效。
2. 按上一轮外域的离线重建方式，从神话原始 PNG 重建 col/spc；明确输入、输出颜色空间，用解码后的像素误差验收，不能只看 DDS 文件头。核对 gls/spc 现有格式与目标语义。保留发光遮罩的线性含义，避免重复 gamma。
3. 不改变模型、ADS、枪口、音效或独立动画。若改用 RePak 1.4，注意当前神话使用的是旧格式 map，必须进行显式转换；不能把旧 map 直接交给新工具，更不能借用外域脚本中硬编码的材质名称。
4. 重新核对两个人称、四套换色、进化/基础状态、自定义材质引用、RPak 内存分段和粒子资源，然后单独输出 **1.1.2 候选版**；不覆盖游戏安装。
5. 更新 GitHub 成品和增量资源。旧完整资源包仍可使用，新核对包提供的是后续检查点。没有用户游戏反馈前，不标记“彻底解决泛白/崩溃/光效”。

这些已定位的步骤可以先交给低用量编码模型、Medium 推理继续。只有遇到未解释的二进制加载/材质转换错误或新的复杂动画问题，再回到 Astra High。此为任务分工建议，不保证低档模型能独立排除所有后续问题。

## 技能安装

已从 [mattpocock/skills](https://github.com/mattpocock/skills/tree/main/skills/engineering/grill-with-docs) 安装 `grill-with-docs`，并安装其依赖 `grilling`、`domain-modeling`，位置为 `D:\CodexStorage\CodexHome\skills`。下一轮可用。本轮只完成安装与核对，没有擅自开启冗长需求访谈；用户已明确的约束不重复询问。

接口参考：[Northstar 粒子句柄示例](https://docs.northstar.tf/Modding/squirrel/functions/)、[Northstar 客户端源码](https://github.com/R2Northstar/NorthstarMods/tree/main/Northstar.Client/mod/scripts/vscripts)。下载的官方参考和命中位置保存在本地 `08_FinalAudit`。
