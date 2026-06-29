## 红绿灯状态指示灯系统

桌面有一个实体红绿灯，通过 USB 串口控制，指示 Claude Code 的工作状态。

### 文件
- 全局 settings: `C:\Users\VDTesting\.claude\settings.json`
- 驱动脚本: `C:\Users\VDTesting\.claude\traffic_light.py`
- 迁移助手: `C:\Users\VDTesting\.claude\setup_traffic_light.py`
- 项目级 settings: `.claude\settings.local.json`（优先级高于全局）
- COM 口: **COM4**（迁移时改 `traffic_light.py` 顶部的 `PORT` 变量）
- 依赖: `pip install pyserial`
- 日志: `~/.claude/light_daemon.log`

### 迁移到新机器
1. 拷贝整个 `.claude` 文件夹到新机器的 `%USERPROFILE%`
2. 改 `traffic_light.py` 顶部的 `PORT`
3. 运行 `python setup_traffic_light.py`（自动更新 settings.json 中的路径）
4. 搞定，无需手动改 10 处路径

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

### 关键经验
1. **Arduino 复位问题**: 每次打开串口 DTR 跳变导致复位。解法 → daemon 常驻 + `setDTR(False)` + 2秒等待
2. **命令覆盖问题**: 多个 hook 同时写文件会互相覆盖。解法 → 队列追加 + 递增序号
3. **红灯不灭**: AskUserQuestion 后 W（红灯）不应被 Stop 的 G（绿灯）覆盖，但应该被 PreToolUse 的 Y（开始工作）清除。解法 → Y 覆盖 W
4. **daemon 重启序号重置**: 杀死 daemon 后 `read_pos` 和序号不一致。解法 → daemon 启动时自动对齐序号到队列最大值
5. **hook 卡死**: `send()` 内等待 daemon 启动（轮询3秒）会阻塞 hook → Claude 完全卡死。解法 → 纯异步启动，写队列即返回，绝不阻塞
6. **hook %USERPROFILE% 不展开**: 在 hook 命令中用 `%USERPROFILE%` 环境变量不会展开， hook 环境不走 cmd.exe。解法 → 用迁移助手自动替换路径
7. **hook 写崩恢复**: PreToolUse 退出码=2 会拦截所有工具。解法 → 删 `settings.json` hooks 或 `taskkill /F /IM python.exe`
8. **PID 回收误判**: `OpenProcess()` 返回有效句柄但 PID 已被回收给其他进程。解法 → 用 `GetModuleBaseNameW` 确认是 python.exe
9. **按 Stop 不触发 Stop hook**: Claude Code 的 Stop 按钮不会触发 Stop 钩子，只有正常回复完成才会。所以 Stop hook 只管正常变绿，不用管 Stop 按钮
10. **代码鲁棒性要点**:
    - 所有 `except` 记录日志到 `light_daemon.log`，不静默吞错误
    - 通过行数追踪（`last_line`）替代字节位置（`read_pos`），避免 Windows 文本模式 `tell()` 不准
    - 串口打开失败自动重试 3 次，全部失败则 daemon 退出
    - `ser.write()` 设 `write_timeout=1` 防止串口写入无限阻塞
    - 每次写入后 `flush()` 确保命令立即发送到 Arduino
    - 各状态独立保持时间（G=2s, R/W=0.5s, S/Y/O=0.3s），避免快速切换人眼看不见
    - `_is_running()` 用原生 Windows API（`OpenProcess` + `GetModuleBaseNameW`），不创建子进程

### 硬件
- Arduino (ATmega328P-AU), 9600波特率
- 4针共阴极红绿灯模块: D8→红灯, D9→黄灯, D10→绿灯
