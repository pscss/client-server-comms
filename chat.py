import socket
import threading
import json
import os
import time

CONFIG_FILE = "chat_config.json"
PORT = 5000  # Fixed port for both listening and connecting

# Shared variables to hold the chat connection and signal when it’s ready.
chat_conn = None
chat_conn_lock = threading.Lock()
connection_established = threading.Event()


def load_config():
    """Load saved partner configuration (name and IP) if available."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print("Error reading configuration file:", e)
            return None
    return None


def save_config(partner_name, partner_ip):
    """Save partner configuration for future sessions with duplicacy check."""
    config = {"partner_name": partner_name, "partner_ip": partner_ip}
    try:
        # Check for duplicacy: if the file exists and the same config is saved, do nothing.
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                try:
                    existing_config = json.load(f)
                    if (
                        existing_config.get("partner_name") == partner_name
                        and existing_config.get("partner_ip") == partner_ip
                    ):
                        print("Configuration already saved, no update needed.")
                        return
                except json.JSONDecodeError:
                    # If file is corrupted, we'll overwrite it.
                    pass
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f)
        print("Configuration saved successfully.")
    except Exception as e:
        print("Error saving configuration:", e)


def server_thread_func():
    """
    Listens for an incoming connection on PORT.
    When a connection is accepted, if no connection has been established yet,
    it saves the connection and signals that the chat can begin.
    """
    global chat_conn
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server_sock.bind(("", PORT))
        server_sock.listen(1)
    except Exception as e:
        print(f"[Listener] Failed to bind/listen on port {PORT}: {e}")
        return

    # Set a timeout so we can periodically check if a connection is already made
    server_sock.settimeout(1)
    print(f"[Listener] Listening for incoming connections on port {PORT}...")

    while not connection_established.is_set():
        try:
            conn, addr = server_sock.accept()
            with chat_conn_lock:
                if chat_conn is None:
                    chat_conn = conn
                    connection_established.set()
                    print(f"[Listener] Incoming connection established from {addr}")
                else:
                    # Already have a connection; close the redundant one.
                    conn.close()
        except socket.timeout:
            continue
        except Exception as e:
            print(f"[Listener] Error: {e}")
            break
    server_sock.close()


def client_thread_func(partner_ip):
    """
    Repeatedly attempts to connect to the partner's IP on PORT.
    Once connected (and if no connection exists yet), saves the connection
    and signals that the chat can begin.
    """
    global chat_conn
    while not connection_established.is_set():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            s.connect((partner_ip, PORT))
            with chat_conn_lock:
                if chat_conn is None:
                    chat_conn = s
                    connection_established.set()
                    print(f"[Connector] Connected to partner at {partner_ip}:{PORT}")
                else:
                    s.close()  # A connection was already set up
            break
        except Exception:
            # Connection not yet available; wait a bit before retrying.
            time.sleep(1)


def send_messages(sock, my_name):
    """
    Reads user input and sends messages over the connection.
    Typing 'exit()' notifies the partner and closes the connection.
    """
    while True:
        msg = input("")
        if msg.strip() == "exit()":
            try:
                sock.sendall("USER_EXIT".encode())
            except Exception as e:
                print("Error sending exit message:", e)
            print("You have exited the chat.")
            sock.close()
            break
        else:
            message_to_send = f"{my_name}: {msg}"
            try:
                sock.sendall(message_to_send.encode())
            except Exception as e:
                print("Error sending message:", e)
                break


def receive_messages(sock):
    """
    Listens for incoming messages.
    When a 'USER_EXIT' message is received, informs the user that the partner is offline.
    """
    while True:
        try:
            data = sock.recv(1024)
            if not data:
                print("Connection closed by the partner.")
                break
            msg = data.decode()
            if msg == "USER_EXIT":
                print("The partner has exited the chat. They are offline.")
                break
            print(msg)
        except Exception as e:
            print("Error receiving message:", e)
            break


def chat_session(sock, my_name):
    """
    Starts the chat session by launching two threads:
    one for sending messages and one for receiving messages.
    """
    send_thread = threading.Thread(target=send_messages, args=(sock, my_name))
    recv_thread = threading.Thread(target=receive_messages, args=(sock,))
    send_thread.start()
    recv_thread.start()
    send_thread.join()
    recv_thread.join()


def main():
    print("Welcome to the P2P Chat App!")
    my_name = input("Enter your name: ").strip()

    # Get partner configuration (name and IP) from saved file or prompt user.
    config = load_config()
    if config:
        use_config = input("Saved configuration found. Use it? (Y/N): ").strip().lower()
        if use_config == "y":
            partner_name = config.get("partner_name")
            partner_ip = config.get("partner_ip")
            print(
                f"Using saved configuration: Partner Name: {partner_name}, IP: {partner_ip}"
            )
        else:
            partner_name = input("Enter your partner's name: ").strip()
            partner_ip = input("Enter your partner's IP address: ").strip()
    else:
        partner_name = input("Enter your partner's name: ").strip()
        partner_ip = input("Enter your partner's IP address: ").strip()

    # Start both the listener and connector threads.
    listener = threading.Thread(target=server_thread_func, daemon=True)
    connector = threading.Thread(
        target=client_thread_func, args=(partner_ip,), daemon=True
    )
    listener.start()
    connector.start()

    # Wait for connection established event with a timeout.
    if not connection_established.wait(timeout=60):
        print(
            "Unable to establish connection. Please check the partner's IP address and try again."
        )
        return

    # Save configuration only if connection is successfully established.
    save_config(partner_name, partner_ip)

    print("Chat connection established. You can start messaging now.")
    chat_session(chat_conn, my_name)

    # (Optional) Wait for the listener and connector threads to finish.
    listener.join()
    connector.join()


if __name__ == "__main__":
    main()
