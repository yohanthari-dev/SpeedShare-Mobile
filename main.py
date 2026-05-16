import flet as ft
import socket
import os
import threading
import struct
import time
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# --- 🔒 PRIVACY KEY ---
STATIC_KEY = b'SpeedShareProSecureKey32Bytes!!!'
aesgcm = AESGCM(STATIC_KEY)


def main(page: ft.Page):
    page.title = "SpeedShare Pro"
    page.theme_mode = ft.ThemeMode.DARK
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.scroll = ft.ScrollMode.AUTO

    client_socket = [None]
    pc_ip_address = [None]

    title_lbl = ft.Text("🚀 SPEEDSHARE MOBILE PRO", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_400)
    status_lbl = ft.Text("📡 Looking for SpeedShare PC Server...", size=14, color=ft.Colors.ORANGE_400,
                         weight=ft.FontWeight.BOLD)

    progress_bar = ft.ProgressBar(width=300, value=0, color=ft.Colors.BLUE_400, bgcolor=ft.Colors.GREY_800)
    progress_lbl = ft.Text("Ready", size=12, color=ft.Colors.GREY_400)

    # --- AUTO DISCOVERY ---
    def discover_pc():
        udp_client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            udp_client.bind(('', 9998))
        except:
            return

        while True:
            try:
                data, addr = udp_client.recvfrom(1024)
                msg = data.decode('utf-8')
                if msg.startswith("SPEEDSHARE_SERVER_PING"):
                    ip = msg.split("||")[1]
                    pc_ip_address[0] = ip
                    status_lbl.value = f"🟢 Found PC Server! Connecting..."
                    status_lbl.color = ft.Colors.BLUE_300
                    page.update()

                    try:
                        client_socket[0] = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        client_socket[0].connect((ip, 9999))
                        status_lbl.value = f"⚡ Connected Securely ({ip})"
                        status_lbl.color = ft.Colors.GREEN_400
                        send_files_btn.disabled = False
                        send_folder_btn.disabled = False
                        page.update()
                        break
                    except:
                        status_lbl.value = "❌ Connection Refused. Retrying..."
                        status_lbl.color = ft.Colors.RED_400
                        page.update()
            except:
                pass
            time.sleep(1)

    threading.Thread(target=discover_pc, daemon=True).start()

    def on_result(e):
        if e.files or e.path:
            progress_lbl.value = "🔄 Preparing transfer..."
            page.update()
            threading.Thread(target=transfer_process, args=(e,), daemon=True).start()

    file_picker = ft.FilePicker()
    file_picker.on_result = on_result
    page.overlay.append(file_picker)

    # --- AES-GCM STREAMING ENGINE ---
    def transfer_process(e):
        try:
            items_to_send = []
            if e.files:
                for f in e.files:
                    if f.path: items_to_send.append((f.path, os.path.basename(f.path)))
            elif e.path:
                root_dir = e.path
                base_name = os.path.basename(root_dir)
                for root, dirs, files in os.walk(root_dir):
                    for file in files:
                        abs_path = os.path.join(root, file)
                        rel_path = os.path.join(base_name, os.path.relpath(abs_path, root_dir))
                        items_to_send.append((abs_path, rel_path))

            if not items_to_send: return

            total_items = len(items_to_send)
            for index, (abs_path, rel_path) in enumerate(items_to_send):
                filesize = os.path.getsize(abs_path)

                header = f"{rel_path}||{filesize}".encode('utf-8')
                header_len = len(header)
                client_socket[0].sendall(struct.pack('!I', header_len) + header)

                start_time = time.time()
                bytes_sent = 0

                with open(abs_path, 'rb') as f:
                    while True:
                        chunk = f.read(64 * 1024)
                        if not chunk: break

                        nonce = os.urandom(12)
                        ciphertext = aesgcm.encrypt(nonce, chunk, None)
                        encrypted_chunk = nonce + ciphertext
                        chunk_len = len(encrypted_chunk)

                        client_socket[0].sendall(struct.pack('!I', chunk_len) + encrypted_chunk)
                        bytes_sent += len(chunk)
                        progress_bar.value = bytes_sent / filesize

                        elapsed = time.time() - start_time
                        if elapsed > 0:
                            speed = (bytes_sent / (1024 * 1024)) / elapsed
                            progress_lbl.value = f"🔒 [{index + 1}/{total_items}] Sending: {os.path.basename(rel_path)} ({speed:.1f} MB/s)"
                        page.update()

                client_socket[0].recv(7)

            progress_lbl.value = "✅ All Data Sent Safely with AES-GCM!"
            progress_bar.value = 1.0
            page.update()

        except Exception as ex:
            progress_lbl.value = f"❌ Error: {str(ex)}"
            page.update()

    send_files_btn = ft.Button(
        content=ft.Text("📁 Select & Send Files", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
        disabled=True, width=260, height=55, on_click=lambda _: file_picker.pick_files(allow_multiple=True)
    )

    send_folder_btn = ft.Button(
        content=ft.Text("📂 Select & Send Full Folder", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
        disabled=True, width=260, height=55, on_click=lambda _: file_picker.get_directory_path()
    )

    page.add(
        ft.Container(height=40),
        title_lbl,
        ft.Container(height=15),
        status_lbl,
        ft.Divider(height=40, color=ft.Colors.GREY_800),
        send_files_btn,
        ft.Container(height=10),
        send_folder_btn,
        ft.Container(height=40),
        progress_bar,
        ft.Container(height=5),
        progress_lbl
    )


if __name__ == "__main__":
    ft.run(main)