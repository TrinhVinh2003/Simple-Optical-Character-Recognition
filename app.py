import tkinter as tk
from tkinter import Canvas, Label, Frame, Button
from PIL import ImageGrab, Image, ImageDraw, ImageTk
import numpy as np
import cv2
import win32gui
from keras.models import load_model
import sys

# Đặt mã hóa đầu ra UTF-8
sys.stdout.reconfigure(encoding="utf-8")
# Load các mô hình từ file
cnn_model = load_model('mnist_cnn_model.h5')
softmax_model_weight = np.load("mnist_softmax_model.npy")

# Khởi tạo giao diện
root = tk.Tk()
root.title("Handwritten Character Recognition")
root.geometry("1200x600")  # Kích thước giao diện lớn gần bằng màn hình

# Phân chia bố cục chính
main_frame = Frame(root, width=1200, height=600)
main_frame.pack(fill="both", expand=True)

# Left Side (Drawing Area)
left_frame = Frame(main_frame, width=600, height=600, bg="white")
left_frame.grid(row=0, column=0, padx=20, pady=20)

# Vùng vẽ
canvas = Canvas(left_frame, width=400, height=200, bg="white")
canvas.pack(pady=10)

# Dùng để lưu trữ ảnh hiện tại trên canvas
image = Image.new("RGB", (400, 200), "white")
draw = ImageDraw.Draw(image)


# Chức năng vẽ trên Canvas
def paint(event):
    x1, y1 = (event.x - 5), (event.y - 5)
    x2, y2 = (event.x + 5), (event.y + 5)
    canvas.create_oval(x1, y1, x2, y2, fill="black", width=2)
    draw.line([x1, y1, x2, y2], fill="black", width=2)


canvas.bind("<B1-Motion>", paint)
# Hàm predict đối với mô hình softmax
def predict(X):
    h = np.dot(X,softmax_model_weight)
    softmax = np.exp(h)
    y_pred = softmax / np.sum(softmax, axis=1, keepdims=True)
    return y_pred

# Hàm lấy ảnh từ canvas và xử lý
def save_canvas():
    # Lấy ảnh từ canvas mà không cần phải chụp toàn màn hình

    HWND = canvas.winfo_id() # get the handle of the canvas
    rect = win32gui.GetWindowRect(HWND) # get the coordinate of the canvas
    # Chụp ảnh từ canvas và chuyển sang grayscale
    img = ImageGrab.grab(rect)
    img_np = np.array(img)
    gray = cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY)

    # Nhị phân hóa ảnh
    _, binary_image = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY_INV)
    binary_image = cv2.dilate(binary_image, np.ones((3,3)))
    # Tìm contour và bounding box
    contours, _ = cv2.findContours(
        binary_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    display_img = cv2.cvtColor(binary_image, cv2.COLOR_GRAY2RGB)
    cnn_display_image = display_img.copy()
    softmax_display_image = display_img.copy()
    # Vẽ bounding box
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        cv2.rectangle(cnn_display_image, (x, y), (x + w, y + h), (255, 0, 0), 2)
        cv2.rectangle(softmax_display_image, (x, y), (x + w, y + h), (255, 0, 0), 2)

        # Lấy bouding-box để đưa vào dự đoán số
        char_img = binary_image[y:y+h, x:x+w]
        resized_img = cv2.resize(char_img, (28, 28), interpolation=cv2.INTER_AREA)
        resized_img = resized_img / 255.0
        # Dự đoán với CNN
        cnn_img = resized_img.reshape(1, 28, 28, -1)
        cnn_prediction = cnn_model.predict(cnn_img)
        cnn_char = np.argmax(cnn_prediction)
        cv2.putText(
            cnn_display_image,
            f"{cnn_char}",
            (x +w//2, y -10),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 0, 255),
            2,
        )
        # Dự đoán với Softmax
        softmax_img = resized_img.reshape(1, -1)
        softmax_prediction = predict(softmax_img)
        softmax_char = np.argmax(softmax_prediction)
        cv2.putText(
            softmax_display_image,
            f"{softmax_char}",
            (x + w // 2, y - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 0, 255),
            2,
        )
    return cnn_display_image, softmax_display_image

# Hàm nhận diện và hiển thị kết quả
def recognize():
    cnn_display_img, softmax_display_img = save_canvas()
    img_display_cnn = ImageTk.PhotoImage(image=Image.fromarray(cnn_display_img))
    cnn_result_canvas.create_image(0, 0, image=img_display_cnn, anchor="nw")
    cnn_result_canvas.image = img_display_cnn
    
    # Hiển thị ảnh trên canvas Softmax Regression
    img_display_softmax = ImageTk.PhotoImage(image=Image.fromarray(softmax_display_img))
    softmax_result_canvas.create_image(0, 0, image=img_display_softmax, anchor="nw")
    softmax_result_canvas.image = img_display_softmax

# Các nút chức năng
button_frame = Frame(left_frame)
button_frame.pack(pady=10)
recognize_button = Button(button_frame, text="Nhận diện", command=recognize)
recognize_button.grid(row=0, column=0, padx=10)

reset_button = Button(button_frame, text="Reset", command=lambda: reset())
reset_button.grid(row=0, column=1, padx=10)

# Right Side (Results Display)
right_frame = Frame(main_frame, width=600, height=600, bg="lightgray")
right_frame.grid(row=0, column=1, padx=20, pady=20)

# Kết quả mô hình CNN
cnn_label = Label(right_frame, text="CNN:", font=("Arial", 14), bg="lightgray")
cnn_label.grid(row=0, column=0, sticky="w", pady=5)

cnn_result_canvas = Canvas(right_frame, width=400, height=200, bg="white")
cnn_result_canvas.grid(row=1, column=0, pady=5)

# Kết quả mô hình Softmax Regression
softmax_label = Label(
    right_frame, text="Softmax Regression:", font=("Arial", 14), bg="lightgray"
)
softmax_label.grid(row=2, column=0, sticky="w", pady=5)

softmax_result_canvas = Canvas(right_frame, width=400, height=200, bg="white")
softmax_result_canvas.grid(row=3, column=0, pady=5)


# Hàm reset canvas và các kết quả
def reset():
    canvas.delete("all")
    cnn_result_canvas.delete("all")
    softmax_result_canvas.delete("all")
    draw.rectangle([0, 0, 400, 200], fill="white")


# Chạy giao diện
root.mainloop()
