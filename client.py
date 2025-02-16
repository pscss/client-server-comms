import socket

# Replace with the server VM's IP address
SERVER_IP = "192.168.1.100"
PORT = 5000

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
    client_socket.connect((SERVER_IP, PORT))
    message = "Hello from Client!"
    client_socket.sendall(message.encode())

    # Wait for the server's response
    data = client_socket.recv(1024)
    print(f"Received from server: {data.decode()}")
