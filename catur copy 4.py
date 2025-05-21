import cv2
import numpy as np
import time
import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QLabel, QPushButton, QGridLayout)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap

class ChessDetector:
    def __init__(self):
        # Konstanta untuk deteksi papan catur
        self.min_square_size = 20  # Ukuran minimum kotak papan catur
        self.max_square_size = 150  # Ukuran maksimum kotak papan catur
        
        # Klasifikasi warna bidak catur
        self.piece_colors = {
            "putih": ((180, 180, 180), (255, 255, 255)),  # range HSV untuk bidak putih
            "hitam": ((0, 0, 0), (80, 80, 80))  # range HSV untuk bidak hitam
        }
        
        # Dictionary untuk menyimpan status papan catur sebelumnya
        self.previous_board_state = None
        
        # Nama-nama bidak catur
        self.piece_names = {
            "p": "pion hitam",
            "P": "pion putih", 
            "r": "benteng hitam",
            "R": "benteng putih",
            "n": "kuda hitam", 
            "N": "kuda putih",
            "b": "gajah hitam", 
            "B": "gajah putih", 
            "q": "ratu hitam", 
            "Q": "ratu putih", 
            "k": "raja hitam", 
            "K": "raja putih",
            ".": "kosong"
        }
        
        # Dictionary untuk menyimpan lokasi gambar template bidak
        self.piece_templates = {}
        
        # Inisialisasi papan catur
        self.board = None
        self.squares = []
        
        # Variabel untuk mengumpulkan info perpindahan
        self.move_history = []
    
    def detect_chessboard(self, frame):
        """Mendeteksi papan catur dalam frame"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Adaptasi threshold untuk menemukan kontur papan
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        _, threshold = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Cari kontur
        contours, _ = cv2.findContours(threshold, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        
        # Urutkan kontur berdasarkan area
        contours = sorted(contours, key=cv2.contourArea, reverse=True)
        
        chessboard_contour = None
        
        # Cari kontur yang berpotensi menjadi papan catur (mendekati persegi atau persegi panjang)
        for contour in contours:
            perimeter = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
            
            # Papan catur seharusnya memiliki 4 sudut
            if len(approx) == 4:
                area = cv2.contourArea(contour)
                
                # Filter berdasarkan area minimum
                if area > 10000:  # Minimum area untuk papan catur
                    chessboard_contour = approx
                    break
        
        if chessboard_contour is None:
            return None, None
        
        # Identifikasi sudut papan catur
        corners = self.sort_corners(chessboard_contour.reshape(4, 2))
        
        # Perspektif transformasi untuk memperbaiki pandangan
        width = 400  # Lebar papan catur output
        height = 400  # Tinggi papan catur output
        
        # Matriks transformasi
        dst_points = np.array([[0, 0], [width, 0], [width, height], [0, height]], dtype=np.float32)
        transformation_matrix = cv2.getPerspectiveTransform(corners, dst_points)
        warped = cv2.warpPerspective(frame, transformation_matrix, (width, height))
        
        return warped, corners
    
    def sort_corners(self, corners):
        """Mengurutkan sudut papan catur (kiri atas, kanan atas, kanan bawah, kiri bawah)"""
        rect = np.zeros((4, 2), dtype=np.float32)
        
        # Hitung jumlah koordinat
        s = corners.sum(axis=1)
        rect[0] = corners[np.argmin(s)]  # Kiri atas
        rect[2] = corners[np.argmax(s)]  # Kanan bawah
        
        # Hitung selisih koordinat
        diff = np.diff(corners, axis=1)
        rect[1] = corners[np.argmin(diff)]  # Kanan atas
        rect[3] = corners[np.argmax(diff)]  # Kiri bawah
        
        return rect.astype(np.float32)
    
    def create_chessboard_grid(self, warped_image):
        """Membuat grid 8x8 pada papan catur"""
        height, width = warped_image.shape[:2]
        square_size = width // 8
        
        squares = []
        for i in range(8):
            row = []
            for j in range(8):
                x1 = j * square_size
                y1 = i * square_size
                x2 = (j + 1) * square_size
                y2 = (i + 1) * square_size
                
                # Koordinat kotak catur
                square = {
                    'coords': (x1, y1, x2, y2),
                    'position': (7 - i, j),  # Konversi ke notasi algebraik (0,0 = a8)
                    'notation': chr(97 + j) + str(8 - i)  # Konversi ke a1, b2, dll
                }
                row.append(square)
            squares.append(row)
        
        return squares
    
    def detect_pieces(self, warped_image, squares):
        """Mendeteksi bidak catur pada papan"""
        board_state = [['.' for _ in range(8)] for _ in range(8)]
        
        for i in range(8):
            for j in range(8):
                square = squares[i][j]
                x1, y1, x2, y2 = square['coords']
                
                # Potong gambar kotak
                square_img = warped_image[y1:y2, x1:x2]
                
                # Konversi ke HSV untuk deteksi warna
                hsv_img = cv2.cvtColor(square_img, cv2.COLOR_BGR2HSV)
                
                # Hitung rata-rata warna di kotak
                avg_color = np.mean(square_img, axis=(0, 1))
                
                # Deteksi apakah ada bidak di kotak berdasarkan kontras
                gray_square = cv2.cvtColor(square_img, cv2.COLOR_BGR2GRAY)
                _, thresh = cv2.threshold(gray_square, 127, 255, cv2.THRESH_BINARY)
                contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                # Hitung standar deviasi nilai piksel
                std_dev = np.std(gray_square)
                
                # Bandingkan dengan standar deviasi treshold untuk menentukan keberadaan bidak
                is_piece_present = std_dev > 30  # Threshold bisa disesuaikan
                
                if is_piece_present:
                    # Tentukan warna bidak (putih atau hitam)
                    if np.mean(gray_square) > 130:  # Threshold untuk bidak putih
                        piece_color = "P"  # Pion putih sebagai default
                    else:
                        piece_color = "p"  # Pion hitam sebagai default
                    
                    # Untuk sederhananya, kita hanya deteksi warna bidak
                    # Di aplikasi nyata, perlu model ML untuk mengenali jenis bidak
                    board_state[i][j] = piece_color
        
        return board_state
    
    def detect_piece_moves(self, current_board_state):
        """Mendeteksi perpindahan bidak catur"""
        if self.previous_board_state is None:
            self.previous_board_state = current_board_state
            return None
        
        moves = []
        
        # Bandingkan status papan saat ini dengan sebelumnya
        for i in range(8):
            for j in range(8):
                if self.previous_board_state[i][j] != current_board_state[i][j]:
                    # Ada perubahan, kemungkinan perpindahan bidak
                    if self.previous_board_state[i][j] != '.' and current_board_state[i][j] == '.':
                        # Bidak dipindahkan dari posisi ini
                        from_notation = chr(97 + j) + str(8 - i)
                        moves.append(("from", from_notation, self.previous_board_state[i][j]))
                    
                    if self.previous_board_state[i][j] == '.' and current_board_state[i][j] != '.':
                        # Bidak dipindahkan ke posisi ini
                        to_notation = chr(97 + j) + str(8 - i)
                        moves.append(("to", to_notation, current_board_state[i][j]))
        
        # Update status papan sebelumnya
        self.previous_board_state = [row[:] for row in current_board_state]
        
        return moves
    
    def draw_board_overlay(self, frame, corners, board_state):
        """Menggambar overlay pada papan catur"""
        if corners is None:
            return frame
        
        # Buat salinan frame
        overlay = frame.copy()
        
        # Gambar titik sudut papan catur
        for corner in corners:
            x, y = corner
            cv2.circle(overlay, (int(x), int(y)), 5, (0, 255, 0), -1)
        
        # Gambar kontur papan catur
        cv2.polylines(overlay, [np.int32(corners)], True, (0, 255, 0), 2)
        
        # Jika sudut terdeteksi, tambahkan label koordinat
        if corners is not None and len(corners) == 4:
            # Tambahkan label koordinat
            labels = ['a8', 'h8', 'h1', 'a1']  # Sesuai dengan urutan sudut yang diharapkan
            for i, corner in enumerate(corners):
                x, y = corner
                cv2.putText(overlay, labels[i], (int(x) - 20, int(y) - 10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
        
        return overlay
    

class ChessDetectionApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Deteksi Papan Catur")
        self.setGeometry(100, 100, 1200, 700)
        
        # Inisialisasi detector
        self.detector = ChessDetector()
        
        # Setup GUI
        self.setup_ui()
        
        # Buka kamera
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            print("Tidak dapat membuka kamera")
            sys.exit()
        
        # Setup timer untuk update frame
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)  # Update setiap 30ms (sekitar 33 FPS)
        
        # Status
        self.last_move_time = time.time()
        self.current_board_state = None
        self.move_history = []
    
    def setup_ui(self):
        # Widget utama
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout utama
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Panel kiri untuk tampilan kamera
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_panel.setLayout(left_layout)
        
        # Label untuk menampilkan frame kamera
        self.camera_view = QLabel()
        self.camera_view.setAlignment(Qt.AlignCenter)
        self.camera_view.setMinimumSize(640, 480)
        left_layout.addWidget(self.camera_view)
        
        # Panel kanan untuk tampilan papan catur dan info
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        right_panel.setLayout(right_layout)
        
        # Label untuk menampilkan papan catur terdeteksi
        self.board_view = QLabel("Papan Catur")
        self.board_view.setAlignment(Qt.AlignCenter)
        self.board_view.setMinimumSize(400, 400)
        right_layout.addWidget(self.board_view)
        
        # Grid untuk status papan catur
        board_status_widget = QWidget()
        self.board_status_layout = QGridLayout()
        board_status_widget.setLayout(self.board_status_layout)
        
        # Inisialisasi grid 8x8 untuk status papan
        self.board_status_labels = []
        for i in range(8):
            row_labels = []
            for j in range(8):
                label = QLabel(".")
                label.setAlignment(Qt.AlignCenter)
                label.setStyleSheet("background-color: " + ("white" if (i + j) % 2 == 0 else "gray") + "; min-width: 30px; min-height: 30px;")
                self.board_status_layout.addWidget(label, i, j)
                row_labels.append(label)
            self.board_status_labels.append(row_labels)
        
        right_layout.addWidget(board_status_widget)
        
        # Label untuk menampilkan perpindahan bidak
        self.move_info = QLabel("Belum ada perpindahan terdeteksi")
        right_layout.addWidget(self.move_info)
        
        # Tombol kontrol
        control_layout = QHBoxLayout()
        
        self.start_button = QPushButton("Mulai")
        self.start_button.clicked.connect(self.start_detection)
        control_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("Berhenti")
        self.stop_button.clicked.connect(self.stop_detection)
        control_layout.addWidget(self.stop_button)
        
        self.reset_button = QPushButton("Reset")
        self.reset_button.clicked.connect(self.reset_detection)
        control_layout.addWidget(self.reset_button)
        
        right_layout.addLayout(control_layout)
        
        # Tambahkan panel ke layout utama
        main_layout.addWidget(left_panel, 1)
        main_layout.addWidget(right_panel, 1)
    
    def update_frame(self):
        # Baca frame dari kamera
        ret, frame = self.cap.read()
        
        if not ret:
            print("Tidak dapat menerima frame dari kamera")
            return
        
        # Deteksi papan catur
        warped, corners = self.detector.detect_chessboard(frame)
        
        # Update tampilan kamera dengan overlay
        if corners is not None:
            frame = self.detector.draw_board_overlay(frame, corners, None)
        
        # Konversi frame untuk QLabel
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_image)
        self.camera_view.setPixmap(pixmap.scaled(self.camera_view.width(), self.camera_view.height(), Qt.KeepAspectRatio))
        
        # Jika papan catur terdeteksi, lakukan analisis
        if warped is not None:
            # Konversi warped untuk QLabel
            rgb_warped = cv2.cvtColor(warped, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_warped.shape
            bytes_per_line = ch * w
            qt_warped = QImage(rgb_warped.data, w, h, bytes_per_line, QImage.Format_RGB888)
            warped_pixmap = QPixmap.fromImage(qt_warped)
            self.board_view.setPixmap(warped_pixmap.scaled(self.board_view.width(), self.board_view.height(), Qt.KeepAspectRatio))
            
            # Buat grid papan catur
            squares = self.detector.create_chessboard_grid(warped)
            
            # Deteksi bidak catur
            board_state = self.detector.detect_pieces(warped, squares)
            self.current_board_state = board_state
            
            # Update tampilan status papan
            for i in range(8):
                for j in range(8):
                    self.board_status_labels[i][j].setText(board_state[i][j])
            
            # Deteksi perpindahan bidak per interval waktu
            current_time = time.time()
            if current_time - self.last_move_time > 1.0:  # Deteksi setiap 1 detik
                moves = self.detector.detect_piece_moves(board_state)
                if moves:
                    move_text = "Perpindahan terdeteksi:\n"
                    for move_type, notation, piece in moves:
                        piece_name = self.detector.piece_names.get(piece, "bidak tidak dikenal")
                        if move_type == "from":
                            move_text += f"{piece_name} dipindahkan dari {notation}\n"
                        else:
                            move_text += f"{piece_name} dipindahkan ke {notation}\n"
                    
                    self.move_info.setText(move_text)
                    self.move_history.append(move_text)
                self.last_move_time = current_time
    
    def start_detection(self):
        if not self.timer.isActive():
            self.timer.start(30)
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
    
    def stop_detection(self):
        if self.timer.isActive():
            self.timer.stop()
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
    
    def reset_detection(self):
        # Reset status papan
        self.detector.previous_board_state = None
        self.move_history = []
        self.move_info.setText("Belum ada perpindahan terdeteksi")
        
        # Reset tampilan status papan
        for i in range(8):
            for j in range(8):
                self.board_status_labels[i][j].setText(".")
    
    def closeEvent(self, event):
        # Tutup kamera saat aplikasi ditutup
        if self.cap.isOpened():
            self.cap.release()
        event.accept()

# Tambahan: fungsi untuk mendeteksi jenis bidak menggunakan template matching
def detect_piece_type(square_img, templates):
    """Mendeteksi jenis bidak menggunakan template matching"""
    best_match_val = -float('inf')
    best_match_type = None
    
    gray_square = cv2.cvtColor(square_img, cv2.COLOR_BGR2GRAY)
    
    for piece_type, template in templates.items():
        gray_template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
        
        # Lakukan template matching
        result = cv2.matchTemplate(gray_square, gray_template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(result)
        
        if max_val > best_match_val and max_val > 0.6:  # Threshold kecocokan
            best_match_val = max_val
            best_match_type = piece_type
    
    return best_match_type

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ChessDetectionApp()
    window.show()
    sys.exit(app.exec_())