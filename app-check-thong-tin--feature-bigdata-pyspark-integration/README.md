cách mở app nhấn đúp vào launcher.bat là chạy 

Big Data (PySpark)
-------------------
Trong tab "Big Data (Spark)" của ứng dụng, bạn có thể chạy xử lý dữ liệu URL với PySpark dành cho tập lớn:

1) Chọn file CSV đầu vào có cột `url`. Mặc định: `data/urls.csv`.
2) Chọn file từ khóa vi phạm `.txt`. Mặc định: `data/keywords_violation.txt`.
3) Chọn thư mục xuất kết quả. Mặc định: `bigdata/violated_urls.csv` (Spark sẽ ghi dạng thư mục chứa file CSV).
4) (Tùy chọn) Nhập Spark master: ví dụ `local[*]` hoặc `spark://host:7077`.
5) Bấm "Chạy xử lý với Spark" để bắt đầu; nhật ký sẽ hiện trực tiếp trong ứng dụng.

Chạy bằng dòng lệnh:

```bash
python bigdata/process_urls.py --urls data/urls.csv --keywords data/keywords_violation.txt --output bigdata/violated_urls.csv --master local[*]
```

Yêu cầu: đã cài đặt Java phù hợp và `pyspark` (xem `requirements.txt`).
