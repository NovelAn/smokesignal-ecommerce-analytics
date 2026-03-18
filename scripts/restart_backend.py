"""
重启后端服务器
"""
import subprocess
import time
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("检查端口 8000...")

# 查找占用端口的进程
try:
    result = subprocess.run(
        ['netstat', '-ano'],
        capture_output=True,
        text=True,
        encoding='gbk',
        errors='ignore'
    )

    for line in result.stdout.split('\n'):
        if ':8000' in line and 'LISTENING' in line:
            parts = line.split()
            if len(parts) >= 5:
                pid = parts[-1]
                print(f"发现进程 {pid} 占用端口 8000，正在终止...")
                try:
                    subprocess.run(['taskkill', '/F', '/PID', pid],
                                   capture_output=True,
                                   encoding='gbk',
                                   errors='ignore')
                    print(f"✅ 已终止进程 {pid}")
                except Exception as e:
                    print(f"⚠️ 无法终止进程: {e}")
except Exception as e:
    print(f"错误: {e}")

print("\n等待端口释放...")
time.sleep(3)

print("\n启动后端服务器...")
print("=" * 50)
print("后端 API: http://localhost:8000/api")
print("按 Ctrl+C 停止服务器")
print("=" * 50)

# 启动后端服务器
subprocess.run(
    [sys.executable, '-m', 'uvicorn', 'backend.main:app', '--host', '0.0.0.0', '--port', '8000', '--log-level', 'warning']
)
