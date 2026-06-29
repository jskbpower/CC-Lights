"""
红绿灯系统 - 安装/迁移助手
换机器时:
  1. 把整个 .claude 文件夹拷到新机器的 %USERPROFILE% 下
  2. 改 traffic_light.py 顶部的 PORT
  3. 运行: python setup_traffic_light.py
  搞定, 无需手动改 settings.json
"""
import os, sys, re, subprocess

BASE = os.path.dirname(os.path.abspath(__file__))
SETTINGS = os.path.join(BASE, 'settings.json')
SCRIPT = os.path.join(BASE, 'traffic_light.py')

def get_current_username():
    try:
        import ctypes
        buf = ctypes.create_unicode_buffer(256)
        size = ctypes.c_ulong(256)
        ctypes.windll.advapi32.GetUserNameW(buf, ctypes.byref(size))
        return buf.value
    except:
        return os.environ.get('USERNAME', '')

def update_hooks():
    """替换 settings.json 中所有用户路径为当前用户"""
    if not os.path.exists(SETTINGS):
        print('[-] 找不到 settings.json')
        return False

    with open(SETTINGS, 'r', encoding='utf-8') as f:
        content = f.read()

    new_path = SCRIPT.replace('\\', '/')
    old_paths = re.findall(r'(python\s+)([^\s]*traffic_light\.py)', content)

    if not old_paths:
        print('[-] 未找到 traffic_light.py 路径')
        return False

    for prefix, old_path in old_paths:
        if old_path != new_path:
            content = content.replace(old_path, new_path)

    with open(SETTINGS, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f'[OK] Hook 路径已更新: {new_path}')
    return True

def check_com_port():
    with open(SCRIPT, 'r', encoding='utf-8') as f:
        for line in f:
            m = re.match(r"PORT\s*=\s*'(COM\d+)'", line.strip())
            if m:
                print(f'[i] COM 口: {m.group(1)}')
                return m.group(1)
    print('[-] 未找到 PORT 配置')
    return None

def test_script():
    try:
        result = subprocess.run(
            [sys.executable, SCRIPT, 'G'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        stderr_text = result.stderr.decode('utf-8', errors='replace') if result.stderr else ''
        if result.returncode == 0:
            print('[OK] 脚本测试通过')
            return True
        else:
            print(f'[!] 脚本测试失败 (exit={result.returncode})')
            if stderr_text: print(f'    {stderr_text.strip()}')
            return False
    except subprocess.TimeoutExpired:
        print('[!] 脚本超时')
        return False
    except Exception as e:
        print(f'[!] 脚本测试异常: {e}')
        return False

if __name__ == '__main__':
    print('=' * 40)
    print('  红绿灯系统 - 安装/迁移助手')
    print(f'  用户: {get_current_username()}')
    print('=' * 40)
    print()

    ok = True
    ok &= update_hooks()
    port = check_com_port()
    ok &= test_script()

    print()
    if ok:
        print('[OK] 配置完成! 如 COM 口不对请修改 traffic_light.py 顶部的 PORT 变量')
    else:
        print('[!] 部分检查未通过, 请按提示修复')
