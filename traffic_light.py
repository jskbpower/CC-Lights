"""
红绿灯状态指示灯 - 守护进程
COM口配置在文件头部 PORT 变量，迁移时只需改这里
"""
import serial, sys, os, time, subprocess, ctypes

# ═══════════════════════════════════════
#  迁移时只需改这一行
PORT = 'COM4'
# ═══════════════════════════════════════

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
QUEUE_FILE = os.path.join(BASE_DIR, 'light_queue.txt')
PID_FILE = os.path.join(BASE_DIR, 'light_daemon.pid')
LOG_FILE = os.path.join(BASE_DIR, 'light_daemon.log')
POS_FILE = os.path.join(BASE_DIR, 'light_pos.txt')

# 命令对照:
# S = 新消息 → 🟡 黄灯（UserPromptSubmit）
# Y = 工作中 → 🟡 黄灯（PreToolUse）
# W = 等你回复 → 🔴 红灯（PostToolUse AskUserQuestion）
# R = 出错 → 🔴 红灯（PostToolUseFailure / PermissionRequest）
# G = 空闲 → 🟢 绿灯（Stop / StopFailure）
# F = 闪烁黄灯 → 💡 闪3次后恢复（PreCompact）
# O = 全灭（SessionEnd）

VALID_CMDS = set('SYGRWFO')

def log(msg):
    t = time.strftime('%H:%M:%S')
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(f'[{t}] {msg}\n')
    except:
        pass

# ── 串口写入（带超时 + flush）─────────────
def _ser_write(ser, data):
    try:
        ser.write(data)
        ser.flush()
    except Exception as e:
        log(f'串口写入失败: {e}')

# ── 闪烁黄灯 ─────────────────────────────
def _flash_yellow(ser):
    for _ in range(3):
        _ser_write(ser, b'Y'); time.sleep(0.2)
        _ser_write(ser, b'O'); time.sleep(0.2)

# ── Hook 入口：只写队列，不关心 daemon ────
def hook_send(cmd):
    """纯写队列，<50ms 返回，绝不阻塞"""
    try:
        with open(QUEUE_FILE, 'a') as f:
            f.write(f'{cmd}\n')
    except:
        pass
    # fire-and-forget 启动 daemon
    _start_daemon()

# ── 启动/检查 daemon ─────────────────────
def _is_running():
    """快速检查 daemon（原生 Windows API，不创建子进程，<1ms）"""
    try:
        with open(PID_FILE) as f: pid = int(f.read())
        h = ctypes.windll.kernel32.OpenProcess(
            0x0400 | 0x0010, False, pid)  # QUERY | VM_READ
        if not h:
            try: os.remove(PID_FILE)
            except: pass
            return False
        try:
            buf = ctypes.create_unicode_buffer(260)
            if ctypes.windll.psapi.GetModuleBaseNameW(h, None, buf, 260):
                return buf.value.lower().startswith('python')
        except:
            pass
        finally:
            ctypes.windll.kernel32.CloseHandle(h)
        try: os.remove(PID_FILE)
        except: pass
    except: pass
    return False

def _start_daemon():
    if _is_running(): return
    try:
        subprocess.Popen(
            [sys.executable, __file__, '--daemon'],
            creationflags=0x08000000,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except:
        pass

# ── 守护进程 ─────────────────────────────
def run_daemon():
    pid = os.getpid()
    with open(PID_FILE, 'w') as f: f.write(str(pid))
    log(f'daemon 启动 (PID={pid})')

    # 打开串口
    ser = None
    for retry in range(3):
        try:
            ser = serial.Serial(PORT, 9600, timeout=1, write_timeout=1)
            ser.setDTR(False)
            time.sleep(2)
            ser.flushInput()
            ser.reset_output_buffer()
            log(f'串口 {PORT} 已打开')
            break
        except Exception as e:
            log(f'串口打开失败(第{retry+1}次): {e}')
            time.sleep(2)

    if ser is None:
        log(f'串口 {PORT} 打开失败，daemon 退出')
        try: os.remove(PID_FILE)
        except: pass
        return

    last_cmd = ''
    last_line = 0  # 已处理的行数
    # 每个状态的保持时间（秒）
    HOLD_TIMES = {'G': 2.0, 'R': 0.5, 'W': 0.5, 'S': 0.3, 'Y': 0.3, 'O': 0.3}
    last_change = 0

    try:
        while True:
            try:
                # 读取新增的命令（按行数追踪，避免字节位置问题）
                cmds = []
                with open(QUEUE_FILE, 'r') as f:
                    lines = f.readlines()

                if len(lines) > last_line:
                    for line in lines[last_line:]:
                        line = line.strip().upper()
                        if line and line in VALID_CMDS:
                            cmds.append(line)
                    last_line = len(lines)
                    with open(POS_FILE, 'w') as pf: pf.write(str(last_line))

                # 处理命令（按顺序，每个状态按 HOLD_TIMES 保持）
                for cmd in cmds:
                    if cmd == last_cmd:
                        continue
                    # 确保上一个状态显示足够久
                    elapsed = time.time() - last_change
                    prev_hold = HOLD_TIMES.get(last_cmd, 0.5)
                    if elapsed < prev_hold and last_change > 0:
                        time.sleep(prev_hold - elapsed)

                    if cmd == 'F':
                        _flash_yellow(ser)
                        last_cmd = ''
                    elif cmd == 'G' and last_cmd == 'W':
                        pass  # 不覆盖等你回复
                    elif cmd == 'W':
                        _ser_write(ser, b'R'); last_cmd = 'W'
                    elif cmd == 'S':
                        _ser_write(ser, b'Y'); last_cmd = 'Y'
                    else:
                        _ser_write(ser, cmd.encode()); last_cmd = cmd
                    last_change = time.time()

            except Exception as e:
                log(f'daemon 循环错误: {e}')
            time.sleep(0.1)

    except Exception as e:
        log(f'daemon 异常退出: {e}')
    finally:
        if ser:
            try: ser.close()
            except: pass
        for f in (PID_FILE, POS_FILE):
            try: os.remove(f)
            except: pass
        log('daemon 已退出')

# ── 入口 ─────────────────────────────────
if __name__ == '__main__':
    if len(sys.argv) >= 2 and sys.argv[1] == '--daemon':
        run_daemon()
    elif len(sys.argv) >= 2:
        c = sys.argv[1].upper()
        if c in VALID_CMDS:
            hook_send(c)
