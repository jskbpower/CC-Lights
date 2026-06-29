## Claude Code红绿灯状态指示灯系统

桌面有一个实体红绿灯，通过 USB 串口控制，指示 Claude Code 的工作状态。

### 使用方法
将setup_traffic_light.py和traffic_light.py放到全局.claude目录下，添加settings.json里的内容到你的settings.json文件中。修改traffic_light.py中硬件对应的串口号。告诉Claude Code已安装桌面红绿灯状态指示灯系统，运行python setup_traffic_light.py进行初始化。

### 完整 Hook 配置（共 9 个）
```
SessionStart               → G (打开终端后绿灯待命)
UserPromptSubmit           → S (发消息开始工作)
PreToolUse                 → Y (调用工具中)
PostToolUse AskUserQuestion→ W (提问等你回复)
PostToolUseFailure         → R (工具出错)
PermissionRequest          → R (请求权限)
PreCompact                 → F (压缩上下文前闪烁)
Stop                       → G (回复完成变绿，按Stop按钮不会触发此hook)
SessionEnd                 → O (关闭终端后灭灯)
```

### 命令与灯光逻辑
- `S` = 新消息 → 🟡 黄灯（UserPromptSubmit）
- `Y` = 工作中 → 🟡 黄灯（PreToolUse），覆盖 W ⭐
- `W` = 等你回复 → 🔴 红灯（PostToolUse AskUserQuestion），被 S/Y 清除
- `R` = 出错 → 🔴 红灯（PostToolUseFailure / PermissionRequest），可恢复
- `F` = 闪烁黄灯 → 💡 闪3次后恢复（PreCompact）
- `G` = 空闲 → 🟢 绿灯（Stop / SessionStart），不覆盖 W
- `O` = 全灭（SessionEnd）

### 硬件
- Arduino (ATmega328P-AU), 9600波特率
- 4针共阴极红绿灯模块: D8→红灯, D9→黄灯, D10→绿灯
