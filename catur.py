import sys
import cv2
import numpy as np
import pygame
import threading
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QComboBox
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import Qt, QTimer

class ChessBoardDetector(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Inisialisasi interface GUI
        self.setWindowTitle("Pendeteksi Papan Catur")
        self.setGeometry(100, 100, 1200, 800)

        #Dictionary Posisi Pion
        self.board_state = self.init_board()
        
        # Widget utama dan layout
        central_widget = QWidget()
        main_layout = QHBoxLayout()
        
        # Layout kiri untuk tampilan video
        left_layout = QVBoxLayout()
        self.video_label = QLabel("Video akan ditampilkan di sini")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(640, 480)
        left_layout.addWidget(self.video_label)
        
        # Tombol dan kontrol
        controls_layout = QHBoxLayout()
        
        # Dropdown untuk memilih kamera
        self.camera_combo = QComboBox()
        self.camera_combo.addItem("Kamera Default (0)", 0)
        for i in range(1, 5):  # Mencoba beberapa indeks kamera
            self.camera_combo.addItem(f"Kamera {i}", i)
        self.camera_combo.currentIndexChanged.connect(self.change_camera)
        controls_layout.addWidget(self.camera_combo)
        
        # Tombol start/stop
        self.start_button = QPushButton("Mulai")
        self.start_button.clicked.connect(self.toggle_camera)
        controls_layout.addWidget(self.start_button)
        
        # Tombol capture
        self.capture_button = QPushButton("Capture")
        self.capture_button.clicked.connect(self.capture_frame)
        controls_layout.addWidget(self.capture_button)
        
        left_layout.addLayout(controls_layout)
        
        # Layout kanan untuk tampilan hasil analisis papan catur
        right_layout = QVBoxLayout()
        self.result_label = QLabel("Hasil deteksi papan catur akan ditampilkan di sini")
        self.result_label.setAlignment(Qt.AlignCenter)
        self.result_label.setMinimumSize(640, 480)
        right_layout.addWidget(self.result_label)
        
        # Status label
        self.status_label = QLabel("Status: Kamera tidak aktif")
        right_layout.addWidget(self.status_label)
        
        # Menggabungkan layout
        main_layout.addLayout(left_layout)
        main_layout.addLayout(right_layout)
        
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
        
        # Variabel untuk video capture
        self.cap = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.is_camera_active = False
        
        # Variabel untuk papan catur
        self.chessboard_corners = None
        self.square_size = 50  # Ukuran default kotak papan catur
        self.board_detected = False

        
    def init_board(self):
        board = {}
        column = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']

        # identification for pawn
        for i in range(8):
            board[column[i] + '2'] = 'white_pawn'
            board[column[i] + '7'] = 'black_pawn'
        # identification for king etc
        order = ['rook', 'knight', 'bishop', 'queen', 'king', 'bishop', 'knight', 'rook']
        for i in range(8):
            board[column[i] + '1'] = f'white_{order[i]}'
            board[column[i] + '8'] = f'black_{order[i]}'
        return board

    def change_camera(self):
        # Mengubah kamera yang digunakan
        if self.is_camera_active:
            self.toggle_camera()  # Matikan kamera dulu
            self.toggle_camera()  # Hidupkan kamera dengan indeks baru
    
    def toggle_camera(self):
        if not self.is_camera_active:
            # Memulai kamera
            camera_index = self.camera_combo.currentData()
            self.cap = cv2.VideoCapture(camera_index)
            
            if self.cap.isOpened():
                self.is_camera_active = True
                self.timer.start(30)  # Update setiap 30ms (sekitar 33 FPS)
                self.start_button.setText("Stop")
                self.status_label.setText(f"Status: Kamera aktif (indeks: {camera_index})")
            else:
                self.status_label.setText(f"Status: Gagal membuka kamera (indeks: {camera_index})")
        else:
            # Menghentikan kamera
            self.timer.stop()
            if self.cap:
                self.cap.release()
            self.is_camera_active = False
            self.start_button.setText("Mulai")
            self.status_label.setText("Status: Kamera tidak aktif")
            
    def update_frame(self):
        ret, frame = self.cap.read()
        if ret:
            # Tampilkan frame asli di label kiri
            display_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = display_frame.shape
            bytes_per_line = ch * w
            q_img = QImage(display_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
            self.video_label.setPixmap(QPixmap.fromImage(q_img).scaled(
                self.video_label.width(), self.video_label.height(), 
                Qt.KeepAspectRatio, Qt.SmoothTransformation
            ))
            
            # Deteksi papan catur
            self.detect_chessboard(frame)
    
    def capture_frame(self):
        if self.cap and self.is_camera_active:
            ret, frame = self.cap.read()
            if ret:
                self.detect_chessboard(frame, show_result=True)
                self.status_label.setText("Status: Frame diambil untuk analisis")
    
    def detect_chessboard(self, frame, show_result=False):
        # Konversi ke grayscale untuk deteksi
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Coba deteksi papan catur 7x7 (8x8 kotak memiliki 7x7 titik pertemuan)
        ret, corners = cv2.findChessboardCorners(gray, (7, 7), None)
        
        result_img = frame.copy()
        
        if ret:
            # Perbaiki sudut dengan subpixel accuracy
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
            refined_corners = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
            
            # Gambar papan catur yang terdeteksi
            cv2.drawChessboardCorners(result_img, (7, 7), refined_corners, ret)
            
            # Simpan corners untuk penggunaan lebih lanjut
            self.chessboard_corners = refined_corners
            self.board_detected = True
            
            # Gambar kotak-kotak dan koordinat papan catur
            result_img = self.draw_chess_coordinates(result_img, refined_corners)
            
            # Deteksi benda di atas kotak papan catur
            result_img = self.detect_pieces(gray, result_img, refined_corners)
            
            status_text = "Papan catur terdeteksi"
        else:
            status_text = "Papan catur tidak terdeteksi"
            self.board_detected = False
        
        if show_result or self.board_detected:
            # Tampilkan hasil di label kanan
            display_result = cv2.cvtColor(result_img, cv2.COLOR_BGR2RGB)
            h, w, ch = display_result.shape
            bytes_per_line = ch * w
            q_img = QImage(display_result.data, w, h, bytes_per_line, QImage.Format_RGB888)
            self.result_label.setPixmap(QPixmap.fromImage(q_img).scaled(
                self.result_label.width(), self.result_label.height(), 
                Qt.KeepAspectRatio, Qt.SmoothTransformation
            ))
            
            if show_result:
                self.status_label.setText(f"Status: {status_text}")
    
    def draw_chess_coordinates(self, img, corners):
        if len(corners) != 49:  # 7x7 titik pertemuan
            return img
        
        # Perkirakan perspektif papan catur dan buat kotak-kotak
        # Kita perlu menyusun corners menjadi 7x7 grid
        corners = corners.reshape(7, 7, 2)
        
        # Ekstrak 4 sudut papan catur
        top_left = np.float32([corners[0][0]])
        top_right = np.float32([corners[0][6]])
        bottom_left = np.float32([corners[6][0]])
        bottom_right = np.float32([corners[6][6]])
        
        # Gambar garis batas papan catur
        # Kita perlu mengekstrapolasi untuk mendapatkan kotak penuh 8x8
        
        # Ekstrapolasi ke kiri
        left_edge_vector = (corners[0][0] - corners[6][0]) / 6
        right_edge_vector = (corners[0][6] - corners[6][6]) / 6
        
        # Ekstrapolasi ke atas dan bawah untuk mendapatkan 8x8 penuh
        top_edge = corners[0]
        bottom_edge = corners[6]
        
        # Ekstrapolasi ke atas
        top_row_vector = (top_edge[0] - bottom_edge[0]) / 6
        top_extra_row = np.array([top_edge[i] + top_row_vector for i in range(7)])
        
        # Ekstrapolasi ke bawah
        bottom_row_vector = (bottom_edge[0] - top_edge[0]) / 6
        bottom_extra_row = np.array([bottom_edge[i] + bottom_row_vector for i in range(7)])
        
        # Ekstrapolasi ke kiri dan kanan
        all_rows = np.vstack([top_extra_row.reshape(-1, 2), corners.reshape(-1, 2), bottom_extra_row.reshape(-1, 2)])
        all_rows = all_rows.reshape(9, 7, 2)
        
        # Sekarang kita perlu kolom ekstra di kiri dan kanan
        left_extra_col = np.zeros((9, 2))
        right_extra_col = np.zeros((9, 2))
        
        for i in range(9):
            left_vector = (all_rows[i][0] - all_rows[i][1]) / 1
            right_vector = (all_rows[i][6] - all_rows[i][5]) / 1
            
            left_extra_col[i] = all_rows[i][0] + left_vector
            right_extra_col[i] = all_rows[i][6] + right_vector
        
        # Semua titik sudut 9x9 (untuk 8x8 kotak)
        final_corners = np.zeros((9, 9, 2))
        
        for i in range(9):
            for j in range(7):
                final_corners[i][j+1] = all_rows[i][j]
            
            final_corners[i][0] = left_extra_col[i]
            final_corners[i][8] = right_extra_col[i]
        
        # Gambar grid dan label
        board_img = img.copy()
        
        # Label kolom dan baris
        column_labels = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
        row_labels = ['8', '7', '6', '5', '4', '3', '2', '1']
        
        # Gambar kotak dan koordinat
        for i in range(8):
            for j in range(8):
                # Mendapatkan 4 sudut kotak
                square_corners = np.array([
                    final_corners[i][j],
                    final_corners[i][j+1],
                    final_corners[i+1][j+1],
                    final_corners[i+1][j]
                ], dtype=np.int32)
                
                # Gambar kotak
                if (i + j) % 2 == 0:
                    color = (240, 217, 181)  # kotak putih
                else:
                    color = (181, 136, 99)  # kotak hitam
                
                cv2.fillPoly(board_img, [square_corners], color)
                cv2.polylines(board_img, [square_corners], True, (0, 0, 0), 1)
                
                # Tambahkan koordinat
                coord_text = column_labels[j] + row_labels[i]
                text_point = tuple(np.mean(square_corners, axis=0).astype(int))
                
                # Pilih warna teks yang kontras
                if (i + j) % 2 == 0:
                    text_color = (0, 0, 0)  # hitam untuk kotak putih
                else:
                    text_color = (255, 255, 255)  # putih untuk kotak hitam
                
                # Gunakan font yang lebih kecil dan sesuaikan posisi
                font = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = 0.5
                thickness = 1
                text_size = cv2.getTextSize(coord_text, font, font_scale, thickness)[0]
                
                text_x = text_point[0] - text_size[0] // 2
                text_y = text_point[1] + text_size[1] // 2
                
                cv2.putText(board_img, coord_text, (text_x, text_y), font, font_scale, text_color, thickness)
        
        # Blending image asli dengan papan catur yang digambar
        alpha = 0.6  # Transparansi
        result = cv2.addWeighted(img, 1-alpha, board_img, alpha, 0)
        
        return result
    
    # def move_piece(self, old_pos, new_pos):
    #     piece = self.board_state.get(old_pos)
    #     if piece:
    #         self.board_state[new_pos] = piece
    #         del self.board_state[old_pos]
    #     else:
    #         self.board_state[new_pos] = "unknown"
            
    def detect_pieces(self, gray, img, corners):
        if len(corners) != 49:  # 7x7 titik pertemuan
            return img
        
        # Perkirakan perspektif papan catur
        corners = corners.reshape(7, 7, 2)
        
        # Ekstrapolasi seperti pada fungsi draw_chess_coordinates
        # Untuk menyederhanakan, kita bisa fokus pada pusat setiap kotak
        # dan periksa intensitas pixel atau fitur lainnya
        
        # Kalkulasi pusat setiap kotak
        square_centers = np.zeros((8, 8, 2))
        
        # Ekstrapolasi ke 8x8 lengkap seperti sebelumnya
        top_edge = corners[0]
        bottom_edge = corners[6]
        
        top_row_vector = (top_edge[0] - bottom_edge[0]) / 6
        top_extra_row = np.array([top_edge[i] + top_row_vector for i in range(7)])
        
        bottom_row_vector = (bottom_edge[0] - top_edge[0]) / 6
        bottom_extra_row = np.array([bottom_edge[i] + bottom_row_vector for i in range(7)])
        
        all_rows = np.vstack([top_extra_row.reshape(-1, 2), corners.reshape(-1, 2), bottom_extra_row.reshape(-1, 2)])
        all_rows = all_rows.reshape(9, 7, 2)
        
        left_extra_col = np.zeros((9, 2))
        right_extra_col = np.zeros((9, 2))
        
        for i in range(9):
            left_vector = (all_rows[i][0] - all_rows[i][1]) / 1
            right_vector = (all_rows[i][6] - all_rows[i][5]) / 1
            
            left_extra_col[i] = all_rows[i][0] + left_vector
            right_extra_col[i] = all_rows[i][6] + right_vector
        
        final_corners = np.zeros((9, 9, 2))
        
        for i in range(9):
            for j in range(7):
                final_corners[i][j+1] = all_rows[i][j]
            
            final_corners[i][0] = left_extra_col[i]
            final_corners[i][8] = right_extra_col[i]
        
        # Hitung pusat setiap kotak
        for i in range(8):
            for j in range(8):
                # Kalkulasi pusat
                square_centers[i][j] = np.mean([
                    final_corners[i][j],
                    final_corners[i][j+1],
                    final_corners[i+1][j+1],
                    final_corners[i+1][j]
                ], axis=0)
        
        # Metode sederhana deteksi bidak:
        # Periksa intensitas warna dan kontras di sekitar pusat kotak
        result_img = img.copy()
        column_labels = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
        row_labels = ['8', '7', '6', '5', '4', '3', '2', '1']
        
        for i in range(8):
            for j in range(8):
                center = tuple(square_centers[i][j].astype(int))
                radius = int(np.linalg.norm(final_corners[i][j] - final_corners[i+1][j+1]) / 6)
                
                # Ambil region of interest
                x1 = max(0, center[0] - radius)
                y1 = max(0, center[1] - radius)
                x2 = min(gray.shape[1] - 1, center[0] + radius)
                y2 = min(gray.shape[0] - 1, center[1] + radius)
                
                if x1 >= x2 or y1 >= y2:
                    continue
                    
                roi = gray[y1:y2, x1:x2]
                
                # Deteksi bidak dengan memeriksa standar deviasi atau metode lain
                # Metode ini sederhana tetapi bisa diganti dengan deteksi objek lebih canggih
                if roi.size > 0:
                    std_dev = np.std(roi)
                    mean_intensity = np.mean(roi)
                    
                    # Jika standar deviasi tinggi, mungkin ada bidak (tepi objek)
                    # Dan jika intensitas rata-rata berbeda dari sekitarnya
                    piece_detected = std_dev > 25  # Nilai threshold dapat disesuaikan
                    
                    if piece_detected:
                        # Tandai kotak dengan bidak
                        coord_text = column_labels[j] + row_labels[i]
                        piece_type = self.board_state.get(coord_text,"unknown") # Mark Detected piece
                        self.board_state[coord_text] = piece_type
                        # Gambar lingkaran merah pada pusat kotak
                        cv2.circle(result_img, center, radius, (0, 0, 255), 2)
                        
                        # Label teks untuk kotak dengan objek
                        cv2.putText(result_img, f"{coord_text}: {piece_type}*", 
                                   (center[0] - 40, center[1] + 5),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        
        return result_img
        
    def closeEvent(self, event):
        # Pastikan sumber daya dibebaskan saat menutup aplikasi
        if self.cap:
            self.cap.release()
        event.accept()

# class Chessgame(threading.Thread):
#     def __init__(self, board_state_ref, sizesquare = 80):
#         super().__init__()
#         self.board_state_ref = board_state_ref
#         self.sizesquare = sizesquare
#         self.running = True
#         self.width = 8 * sizesquare
#         self.height = 8 * sizesquare
#         self.labelscolumn = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
#         self.labelsrow = ['8', '7', '6', '5', '4', '3', '2', '1']
        
#         pygame.init()
#         self.screen = pygame.display.set_mode((self.width, self.height))
#         pygame.display.set_caption("Chess Board Viewer")
#         self.font = pygame.font.SysFont("Arial", 16)

#     def draw_board(self):
#         colors = [(240, 217, 181), (181, 136, 99)]
#         for row in range(8):
#             for col in range(8):
#                 square_color = colors[(row + col) % 2]
#                 rect = pygame.Rect(col * self.sizesquare, row * self.sizesquare, self.sizesquare, self.sizesquare)
#                 pygame.draw.rect(self.screen, square_color, rect)

#                 coord = self.labelscolumn[col] + self.labelsrow[row]
#                 piece = self.board_state_ref.get(coord, "")
#                 if piece and piece != "unknown":
#                     # Draw text
#                     text_surface = self.font.render(piece.replace("white_", "W_").replace("black_", "B_"), True, (0, 0, 0))
#                     text_rect = text_surface.get_rect(center=rect.center)
#                     self.screen.blit(text_surface, text_rect)

#     def run(self):
#         clock = pygame.time.Clock()
#         while self.running:
#             for event in pygame.event.get():
#                 if event.type == pygame.QUIT:
#                     self.running = False

#             self.screen.fill((0, 0, 0))
#             self.draw_board()
#             pygame.display.flip()
#             clock.tick(10)  # Limit to 10 FPS

#         pygame.quit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ChessBoardDetector()
    window.show()
    # gamechess = Chessgame(window.board_state)
    # gamechess.start()

    sys.exit(app.exec_())
    # gamechess.running = False
    # gamechess.join()