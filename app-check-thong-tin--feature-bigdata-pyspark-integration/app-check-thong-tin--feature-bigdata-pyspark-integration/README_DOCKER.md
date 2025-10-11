# Chạy ứng dụng bằng Docker (GUI qua trình duyệt)

Hướng dẫn này giúp bạn chạy ứng dụng Tkinter (GUI) trong container Docker, truy cập qua trình duyệt web (noVNC).

## Yêu cầu
- Docker và Docker Compose đã cài sẵn.
- Máy có thể truy cập `http://localhost:6080` từ trình duyệt.

## Cách chạy

1) Build và chạy container:

```bash
# Trong thư mục gốc dự án
docker compose up -d --build
```

2) Mở trình duyệt đến địa chỉ:

- http://localhost:6080

Bạn sẽ thấy màn hình desktop Xfce và ứng dụng GUI tự động chạy. Nếu chưa chạy, mở Terminal trong desktop và chạy:

```bash
cd /app && python app.py
```

3) Dừng container:

```bash
docker compose down
```

## Thư mục dữ liệu được mount

- `app-check-thong-tin--feature-bigdata-pyspark-integration/data` → `/app/data`
- `app-check-thong-tin--feature-bigdata-pyspark-integration/bigdata` → `/app/bigdata`

Bạn có thể chỉnh/sao chép dữ liệu đầu vào/đầu ra ở ngoài container, ứng dụng trong container sẽ thấy các thay đổi đó.

## Ghi chú PySpark/Java
- Container đã cài Java OpenJDK 11 và `pyspark` theo `requirements.txt`.
- Khi chạy tab Big Data, bạn có thể để trống `Spark master` (sẽ dùng mặc định `local[*]` trong script) hoặc chỉ định cụ thể nếu bạn có cluster.

## Cổng
- 6080: noVNC (truy cập GUI qua trình duyệt)
- 5901: VNC (tuỳ chọn, dành cho client VNC)

## Tuỳ chỉnh kích thước màn hình
Đặt biến môi trường `RESOLUTION` trong `docker-compose.yml` (mặc định `1366x768`).
