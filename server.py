import socket

def send_to_server(data, host="127.0.0.1", port=5000):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))
    s.sendall(len(data).to_bytes(8, "big"))  # Send the size
    s.sendall(data)
    s.close()

def start_server(host="0.0.0.0", port=5000):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((host, port))
    s.listen(1)
    conn, addr = s.accept()
    raw_len = conn.recv(8)
    total_len = int.from_bytes(raw_len, "big")
    data = b""
    while len(data) < total_len:
        packet = conn.recv(4096)
        if not packet:
            break
        data += packet
    conn.close()
    s.close()
    return data
