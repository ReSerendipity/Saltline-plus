# Saltline Plus

《Saltline / 盐线》的非官方增强版：在保留原作单文件玩法的基础上，增加了玩家道具、敌人变体、固定炮塔与副武器。

**原版游戏（原作者）**：<https://claude.ai/artifact/BGY1SztrAYcJQHSsnHHGmp>  
**本仓库**：<https://github.com/ReSerendipity/Saltline-plus>

> 本仓库是原作的**非官方改版**，与原作者无隶属关系。原作的代码、素材、商标及其他权利归原作者所有。
>
> **本仓库未附任何许可证（No license）**，不授予复制、分发、商用或再许可的权利；公开仅为学习与非商业交流。若原作者要求，将立即删除本仓库及构建产物。

---

## 相较于原版增加的内容

### 1. 玩家工具层
- 三个道具槽：`1/2/3` 选择，`Q` 使用。
- 五种道具：
  - **EMP 脉冲雷**：范围内敌人眩晕 4 秒，不造成伤害。
  - **烟幕罐**：9 秒烟幕，遮挡敌人视线，不阻挡玩家子弹。
  - **诱饵信标**：8 秒内持续吸引附近敌人调查。
  - **弹药箱**：补充 60 发备弹。
  - **医疗针**：恢复 50 生命。
- HUD 道具 chip（名称、剩余次数、选中高亮）；每次切断中继补充 1 次充能。

### 2. 右键瞄准修复
- 第一次右键即可进入 ADS（原版第一次右键被指针锁定吃掉）。
- 在 `window` 捕获阶段阻止画布以外的右键菜单与右键拖动。

### 3. 敌人角色变体
- **盾犬**：正面装甲，正面伤害 ×0.15；背面与弱点正常受伤。
- **维修无人机**：不攻击，14 m 内为友军持续治疗（约 12 HP/s）。
- 巡逻与三波敌人中混入盾犬/维修机。

### 4. 固定炮塔
- 货场、码头各 1 个固定炮塔（共 2 个）。
- 炮头跟踪玩家，红色激光预警 0.9 秒后发射 22 伤害慢速弹。
- 正面装甲 ×0.35，后部散热口为弱点 ×1.6。
- 可被 EMP 眩晕 4 秒（垂头 + 停火）。

### 5. 副武器：BREACH-12 下挂霰弹
- `X` 在 PAC-9 步枪与 BREACH-12 霰弹之间切换。
- 两套独立弹药池：步枪 30/150，霰弹 4/24。
- 霰弹单发 6 弹丸、每丸 18 伤害、90 rpm；后坐与枪口焰更强。
- HUD 自动切换武器名与弹药显示。

### 6. 四语与工程化
- 新增内容均接入 `zh / ja / ko / en` 四语。
- 拆分为可维护源码，并提供构建与静态验收脚本。

---

## 操作

| 操作 | 按键 |
|---|---|
| 移动 / 视角 | `WASD` / 鼠标 |
| 开火 / 瞄准 | 左键 / 右键 |
| 换弹 | `R` |
| 道具槽 | `1` `2` `3` |
| 使用道具 | `Q` |
| 切换主/副武器 | `X` |
| 切断中继 | 在中继处按住 `E` |
| 跳跃 / 冲刺 / 蹲下 | `Space` / `Shift` / `C` |
| 暂停 | `Esc` |

触屏与手柄沿用原版操作。

---

## 构建与运行

需要 Node.js 18+。

```bash
node build.mjs      # 生成 dist/Saltline.html
node verify.mjs     # 静态验收，期望 35/35
```

运行：

```bash
cd dist
python -m http.server 8766
# 打开 http://127.0.0.1:8766/Saltline.html
```

也可以直接用浏览器打开 `dist/Saltline.html`。

可选：校验原始单文件未被改动（原文件不在仓库内）：

```powershell
$env:SALTLINE_ORIGINAL="C:\path\to\盐线-Saltline.html"
node verify.mjs
```

---

## 项目结构

```
saltline/
  src/
    shell.html            # 原 HTML/CSS + 首页公告样式
    i18n.js               # i18n 运行时与四语字典
    vendor/three.min.js   # three.js 原样片段
    game.js               # 游戏主逻辑（含菜单、敌人、武器）
    gadgets/              # 道具：core / emp / smoke / support
    i18n/                 # 道具与首页公告的四语文案
  build.mjs               # 拼接为单 HTML
  verify.mjs              # 静态验收（35 项）
  tools/                  # 各阶段浏览器回归脚本
  dist/Saltline.html      # 构建产物（可直接游玩）
```

---

## 验收状态

- `node build.mjs` + `node verify.mjs`：35/35。
- 浏览器回归：
  - 主线：3 中继 → 撤离 → `complete`。
  - 道具：EMP 眩晕、烟幕遮挡、诱饵/弹药/医疗。
  - 敌人变体：盾犬正面/背面/弱点、维修机治疗且不开火。
  - 炮塔：跟踪、预警开火、装甲/弱点、EMP 眩晕、击杀回收。
  - 副武器：切换、独立弹药、6 弹丸、换弹、HUD。

---

## Credits

- Original game: **Saltline** — <https://claude.ai/artifact/BGY1SztrAYcJQHSsnHHGmp>
- All original code, art direction, audio and design belong to the original author.
- This repository is an unofficial fan build and is not affiliated with or endorsed by the original author.

## License

**No license.** This repository does not grant any license to the original work or to the modifications. All rights remain with their respective authors. Do not redistribute or use commercially without permission from the original author.
