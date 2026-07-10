import http.server
import socketserver
import mimetypes
import os
import subprocess
import sys
import atexit
import time

# 强制覆盖 .js 的 MIME 类型
mimetypes.add_type('application/javascript', '.js')
mimetypes.add_type('application/javascript', '.mjs')

FRONTEND_PORT = 8080
<<<<<<< Updated upstream
BACKEND_PORT = 8000
START_BACKEND = os.getenv('MOZHI_START_BACKEND', '1') != '0'
REQUIRE_BACKEND = os.getenv('MOZHI_REQUIRE_BACKEND', '0') == '1'
=======
BACKEND_PORT = 8001
>>>>>>> Stashed changes

# 项目根目录（frontend 的上一级）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(PROJECT_ROOT, 'backend')


class Handler(http.server.SimpleHTTPRequestHandler):
    def guess_type(self, path):
        # 强制覆盖 .js 文件的 MIME 类型
        if path.endswith('.js') or path.endswith('.mjs'):
            return 'application/javascript'
        return super().guess_type(path)


def start_backend():
    """在子进程中启动后端 uvicorn 服务"""
    # 检测虚拟环境 Python 解释器
    venv_python = os.path.join(PROJECT_ROOT, '.venv', 'Scripts', 'python.exe')
    if not os.path.exists(venv_python):
        venv_python = os.path.join(PROJECT_ROOT, '.venv', 'bin', 'python')
    if not os.path.exists(venv_python):
        venv_python = sys.executable  #  fallback 到当前 Python

    cmd = [
        venv_python, '-m', 'uvicorn',
        'app.main:app',
        '--host', '127.0.0.1',
        '--port', str(BACKEND_PORT),
        '--reload',
    ]

    # 启动后端子进程，工作目录设为 backend/
    proc = subprocess.Popen(
        cmd,
        cwd=BACKEND_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    # 注册退出时自动结束后端进程
    def kill_backend():
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

    atexit.register(kill_backend)

    # 简单读取并打印后端输出（非阻塞，只打印前几行确认启动）
    import threading

    def stream_output():
        for line in proc.stdout:
            print(f'[Backend] {line}', end='')

    threading.Thread(target=stream_output, daemon=True).start()

    return proc


def print_backend_help():
    print('!!! Backend failed to start.')
    print('>>> Frontend will still start so you can test the UI without a local model.')
    print('>>> To install backend dependencies, run from project root:')
    print('    pip install -r backend/requirements.txt')
    print('>>> Useful dev switches:')
    print('    MOZHI_START_BACKEND=0   Start frontend only')
    print('    MOZHI_REQUIRE_BACKEND=1  Exit when backend fails')
    print()


def main():
    backend_proc = None

    if START_BACKEND:
        # 启动后端
        print(f'>>> Starting backend at http://localhost:{BACKEND_PORT} ...')
        backend_proc = start_backend()

        # 等待一小段时间让后端启动
        time.sleep(2)

        if backend_proc.poll() is not None:
            print_backend_help()
            if REQUIRE_BACKEND:
                sys.exit(1)
        else:
            print(f'>>> Backend is running (PID: {backend_proc.pid})')
            print(f'>>> API docs: http://localhost:{BACKEND_PORT}/docs\n')
    else:
        print('>>> MOZHI_START_BACKEND=0, skipping backend startup.')
        print('>>> Frontend offline fallback will be used if the API is unavailable.\n')

    # 启动前端静态服务器
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    with socketserver.TCPServer(('', FRONTEND_PORT), Handler) as httpd:
        print(f'>>> Frontend serving at http://localhost:{FRONTEND_PORT}')
        print('>>> Press Ctrl+C to stop both servers\n')
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print('\n>>> Shutting down servers...')


if __name__ == '__main__':
    main()
