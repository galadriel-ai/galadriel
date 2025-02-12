import json
import socket


def save_env_vars_to_file(env_vars: dict, filepath: str = "/tmp/env_vars.sh"):
    with open(filepath, "w", encoding="utf-8") as f:
        for key, value in env_vars.items():
            f.write(f'export {key}="{value}"\n')


def main():
    print("Starting env var service...")
    client_socket = socket.socket(socket.AF_VSOCK, socket.SOCK_STREAM)
    cid = socket.VMADDR_CID_ANY
    client_port = 3000
    client_socket.bind((cid, client_port))
    client_socket.listen()

    while True:
        client_connection, _ = client_socket.accept()
        payload = client_connection.recv(4096)
        request = json.loads(payload.decode())

        if env_vars := request.get("env_vars"):
            save_env_vars_to_file(env_vars)  # Save to file

            response = json.dumps({"result": "OK"})
            client_connection.send(str.encode(response))
            client_connection.close()
            return  # Exit after saving env vars


if __name__ == "__main__":
    main()
