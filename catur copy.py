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
        self.previous_board_state = None
        
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
            
    # def update_frame(self):
    #     ret, frame = self.cap.read()
    #     if ret:
    #         # Tampilkan frame asli di label kiri
    #         display_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    #         h, w, ch = display_frame.shape
    #         bytes_per_line = ch * w
    #         q_img = QImage(display_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
    #         self.video_label.setPixmap(QPixmap.fromImage(q_img).scaled(
    #             self.video_label.width(), self.video_label.height(), 
    #             Qt.KeepAspectRatio, Qt.SmoothTransformation
    #         ))
            
    #         # Deteksi papan catur
    #         self.detect_chessboard(frame)

    # def update_frame(self):
    #     if self.cap is None or not self.cap.isOpened():
    #         return
    #     ret, frame = self.cap.read()
    #     if not ret:
    #         return

    #     display_frame = frame.copy()

    #     if self.chessboard_corners is not None:
    #         square_images, squares = self.extract_squares(frame, self.chessboard_corners)
    #         current_board_state = {}

    #         for idx, square_img in enumerate(square_images):
    #             if square_img is None:
    #                 continue
    #             piece_present = self.detect_piece(square_img)
    #             current_board_state[idx] = 1 if piece_present else 0

    #         if self.previous_board_state:
    #             from_square = None
    #             to_square = None

    #             for idx in range(64):
    #                 prev = self.previous_board_state.get(idx, 0)
    #                 curr = current_board_state.get(idx, 0)
    #                 if prev == 1 and curr == 0:
    #                     from_square = idx
    #                 elif prev == 0 and curr == 1:
    #                     to_square = idx

    #             if from_square is not None and to_square is not None:
    #                 print(f"Move detected: {from_square} -> {to_square}")
    #                 # Optional: update state to reflect move
    #                 current_board_state[to_square] = self.previous_board_state[from_square]
    #                 current_board_state[from_square] = 0

    #         self.previous_board_state = current_board_state

    #         # Draw rectangles for squares with pieces
    #         for idx, (x, y, w, h) in enumerate(squares):
    #             if current_board_state.get(idx, 0):
    #                 cv2.rectangle(display_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

    #     display_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
    #     height, width, channel = display_frame.shape
    #     bytes_per_line = 3 * width
    #     q_img = QImage(display_frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
    #     self.video_label.setPixmap(QPixmap.fromImage(q_img))
        
    #     self.detect_chessboard(frame)
    
    def capture_frame(self):
        if self.cap and self.is_camera_active:
            ret, frame = self.cap.read()
            if ret:
                self.detect_chessboard(frame, show_result=True)
                self.status_label.setText("Status: Frame diambil untuk analisis")
    
    def extract_squares(self, frame, corners):
        # corners: 49 points from findChessboardCorners, shape (49,1,2)
        if corners is None or len(corners) != 49:
            return [], []

        # Reshape to 7x7 grid of points
        corners = corners.reshape(7, 7, 2)

        # Extrapolate to get 9x9 grid of intersection points (8x8 squares)
        # Using linear extrapolation on edges as you do in draw_chess_coordinates
        def extrapolate_edges(points_7):
            # points_7 shape (7,2)
            vector = (points_7[0] - points_7[1])
            left_extra = points_7[0] + vector
            vector = (points_7[-1] - points_7[-2])
            right_extra = points_7[-1] + vector
            return np.vstack([left_extra, points_7, right_extra])

        # Build 9x7 points
        rows_9x7 = []
        for i in range(7):
            row = corners[i]
            extended_row = extrapolate_edges(row)
            rows_9x7.append(extended_row)
        rows_9x7 = np.array(rows_9x7)  # (7,9,2)

        # Now extrapolate columns to get 9x9 grid
        grid_9x9 = []
        for j in range(9):
            col = rows_9x7[:, j, :]
            extended_col = extrapolate_edges(col)
            grid_9x9.append(extended_col)
        grid_9x9 = np.array(grid_9x9).transpose(1,0,2)  # (9,9,2)

        squares = []
        square_images = []
        frame_h, frame_w = frame.shape[:2]

        for i in range(8):
            for j in range(8):
                # Four corners of the square
                pts = np.array([
                    grid_9x9[i][j],
                    grid_9x9[i][j+1],
                    grid_9x9[i+1][j+1],
                    grid_9x9[i+1][j]
                ], dtype=np.float32)

                # Get bounding rect
                x, y, w, h = cv2.boundingRect(pts.astype(np.int32))

                # Safety check inside frame boundaries
                x = max(x, 0)
                y = max(y, 0)
                w = min(w, frame_w - x)
                h = min(h, frame_h - y)

                # Extract square image ROI
                square_img = frame[y:y+h, x:x+w].copy()

                squares.append((x, y, w, h))
                square_images.append(square_img)

        return square_images, squares

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
            
            # # Gambar kotak-kotak dan koordinat papan catur
            # result_img = self.draw_chess_coordinates(result_img, refined_corners)
            
            # # Deteksi benda di atas kotak papan catur
            # result_img = self.detect_piece(gray, result_img, refined_corners)
            
            square_images, squares = self.extract_squares(gray, refined_corners)
            
            result_img = self.detect_piece(square_images, result_img)

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
            
    # def detect_pieces(self, gray, img, corners):
    #     if len(corners) != 49:  # 7x7 titik pertemuan
    #         return img
        
    #     # Perkirakan perspektif papan catur
    #     corners = corners.reshape(7, 7, 2)
        
    #     # Ekstrapolasi seperti pada fungsi draw_chess_coordinates
    #     # Untuk menyederhanakan, kita bisa fokus pada pusat setiap kotak
    #     # dan periksa intensitas pixel atau fitur lainnya
        
    #     # Kalkulasi pusat setiap kotak
    #     square_centers = np.zeros((8, 8, 2))
        
    #     # Ekstrapolasi ke 8x8 lengkap seperti sebelumnya
    #     top_edge = corners[0]
    #     bottom_edge = corners[6]
        
    #     top_row_vector = (top_edge[0] - bottom_edge[0]) / 6
    #     top_extra_row = np.array([top_edge[i] + top_row_vector for i in range(7)])
        
    #     bottom_row_vector = (bottom_edge[0] - top_edge[0]) / 6
    #     bottom_extra_row = np.array([bottom_edge[i] + bottom_row_vector for i in range(7)])
        
    #     all_rows = np.vstack([top_extra_row.reshape(-1, 2), corners.reshape(-1, 2), bottom_extra_row.reshape(-1, 2)])
    #     all_rows = all_rows.reshape(9, 7, 2)
        
    #     left_extra_col = np.zeros((9, 2))
    #     right_extra_col = np.zeros((9, 2))
        
    #     for i in range(9):
    #         left_vector = (all_rows[i][0] - all_rows[i][1]) / 1
    #         right_vector = (all_rows[i][6] - all_rows[i][5]) / 1
            
    #         left_extra_col[i] = all_rows[i][0] + left_vector
    #         right_extra_col[i] = all_rows[i][6] + right_vector
        
    #     final_corners = np.zeros((9, 9, 2))
        
    #     for i in range(9):
    #         for j in range(7):
    #             final_corners[i][j+1] = all_rows[i][j]
            
    #         final_corners[i][0] = left_extra_col[i]
    #         final_corners[i][8] = right_extra_col[i]
        
    #     # Hitung pusat setiap kotak
    #     for i in range(8):
    #         for j in range(8):
    #             # Kalkulasi pusat
    #             square_centers[i][j] = np.mean([
    #                 final_corners[i][j],
    #                 final_corners[i][j+1],
    #                 final_corners[i+1][j+1],
    #                 final_corners[i+1][j]
    #             ], axis=0)
        
    #     # Metode sederhana deteksi bidak:
    #     # Periksa intensitas warna dan kontras di sekitar pusat kotak
    #     result_img = img.copy()
    #     column_labels = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
    #     row_labels = ['8', '7', '6', '5', '4', '3', '2', '1']
        
    #     for i in range(8):
    #         for j in range(8):
    #             center = tuple(square_centers[i][j].astype(int))
    #             radius = int(np.linalg.norm(final_corners[i][j] - final_corners[i+1][j+1]) / 6)
                
    #             # Ambil region of interest
    #             x1 = max(0, center[0] - radius)
    #             y1 = max(0, center[1] - radius)
    #             x2 = min(gray.shape[1] - 1, center[0] + radius)
    #             y2 = min(gray.shape[0] - 1, center[1] + radius)
                
    #             if x1 >= x2 or y1 >= y2:
    #                 continue
                    
    #             roi = gray[y1:y2, x1:x2]
                
    #             # Deteksi bidak dengan memeriksa standar deviasi atau metode lain
    #             # Metode ini sederhana tetapi bisa diganti dengan deteksi objek lebih canggih
    #             if roi.size > 0:
    #                 std_dev = np.std(roi)
    #                 mean_intensity = np.mean(roi)
                    
    #                 # Jika standar deviasi tinggi, mungkin ada bidak (tepi objek)
    #                 # Dan jika intensitas rata-rata berbeda dari sekitarnya
    #                 piece_detected = std_dev > 25  # Nilai threshold dapat disesuaikan
                    
    #                 if piece_detected:
    #                     # Tandai kotak dengan bidak
    #                     coord_text = column_labels[j] + row_labels[i]
    #                     piece_type = self.board_state.get(coord_text,"unknown") # Mark Detected piece
    #                     self.board_state[coord_text] = piece_type
    #                     # Gambar lingkaran merah pada pusat kotak
    #                     cv2.circle(result_img, center, radius, (0, 0, 255), 2)
                        
    #                     # Label teks untuk kotak dengan objek
    #                     cv2.putText(result_img, f"{coord_text}: {piece_type}*", 
    #                                (center[0] - 40, center[1] + 5),
    #                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        
    #     return result_img

    def detect_piece(self, square_img):
        # Simple heuristic piece detection based on pixel variance or thresholding
        if square_img is None or square_img.size == 0:
            return False

        gray = cv2.cvtColor(square_img, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        piece_pixels = cv2.countNonZero(thresh)
        total_pixels = thresh.shape[0] * thresh.shape[1]
        ratio = piece_pixels / total_pixels

        # Heuristic threshold, tune this based on your lighting/environment
        return ratio > 0.05
    
    def detect_pieces_on_board(self, frame, squares):
        result_img = frame.copy()
        for square_name, pts in squares.items():
            x1, y1 = np.min(pts, axis=0).astype(int)
            x2, y2 = np.max(pts, axis=0).astype(int)
            square_img = frame[y1:y2, x1:x2]

            if self.detect_piece(square_img):
                # Draw a circle or label to indicate a piece
                cx, cy = int((x1 + x2) / 2), int((y1 + y2) / 2)
                cv2.circle(result_img, (cx, cy), 10, (0, 0, 255), -1)
        return result_img


    def update_frame(self):
        if self.cap is None or not self.cap.isOpened():
            return
        ret, frame = self.cap.read()
        if not ret:
            return

        display_frame = frame.copy()

        if self.chessboard_corners is not None:
            square_images, squares = self.extract_squares(frame, self.chessboard_corners)
            current_board_state = {}

            for idx, square_img in enumerate(square_images):
                if square_img is None:
                    continue
                piece_present = self.detect_piece(square_img)
                current_board_state[idx] = 1 if piece_present else 0

            if self.previous_board_state:
                from_square = None
                to_square = None

                for idx in range(64):
                    prev = self.previous_board_state.get(idx, 0)
                    curr = current_board_state.get(idx, 0)
                    if prev == 1 and curr == 0:
                        from_square = idx
                    elif prev == 0 and curr == 1:
                        to_square = idx

                if from_square is not None and to_square is not None:
                    print(f"Move detected: {from_square} -> {to_square}")
                    # Update board state
                    current_board_state[to_square] = self.previous_board_state[from_square]
                    current_board_state[from_square] = 0

            self.previous_board_state = current_board_state

            # Draw rectangles around squares with pieces
            for idx, (x, y, w, h) in enumerate(squares):
                if current_board_state.get(idx, 0):
                    cv2.rectangle(display_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

        display_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
        height, width, channel = display_frame.shape
        bytes_per_line = 3 * width
        q_img = QImage(display_frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
        self.video_label.setPixmap(QPixmap.fromImage(q_img))

        self.detect_chessboard(frame)

    def closeEvent(self, event):
        # Pastikan sumber daya dibebaskan saat menutup aplikasi
        if self.cap:
            self.cap.release()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ChessBoardDetector()
    window.show()

    sys.exit(app.exec_())