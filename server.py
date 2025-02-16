import socket

# Listen on all available interfaces on port 5000
HOST = ""
PORT = 5000

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
    server_socket.bind((HOST, PORT))
    server_socket.listen()
    print(f"Server is listening on port {PORT}...")

    # Wait for a connection
    connection, client_address = server_socket.accept()
    with connection:
        print(f"Connected by {client_address}")
        while True:
            data = connection.recv(1024)
            if not data:
                break  # Client closed connection
            message = data.decode()
            print(f"Received from client: {message}")

            # Process or respond to the message
            response = f"Server received: {message}"
            connection.sendall(response.encode())
