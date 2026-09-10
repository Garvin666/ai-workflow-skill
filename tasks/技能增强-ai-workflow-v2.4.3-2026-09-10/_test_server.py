"""临时测试服务器：模拟 200/404/403(Cloudflare 反爬)/403(普通拒绝)/401，用于验证 check_links 分类。"""
from http.server import BaseHTTPRequestHandler, HTTPServer

class H(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        if self.path == "/ok":
            self.send_response(200); self.send_header("Content-Type", "text/html")
            self.end_headers(); self.wfile.write(b"ok")
        elif self.path == "/cf":
            self.send_response(403); self.send_header("Server", "cloudflare")
            self.send_header("cf-ray", "8a1b2c3d4e5f-LAX"); self.end_headers()
        elif self.path == "/waf":
            self.send_response(403); self.send_header("Server", "AkamaiGHost"); self.end_headers()
        elif self.path == "/plain403":
            self.send_response(403); self.send_header("Server", "nginx"); self.end_headers()
        elif self.path == "/login":
            self.send_response(401); self.end_headers()
        else:
            self.send_response(404); self.end_headers()
    def log_message(self, *a):  # 静音
        pass

HTTPServer(("127.0.0.1", 8731), H).serve_forever()
