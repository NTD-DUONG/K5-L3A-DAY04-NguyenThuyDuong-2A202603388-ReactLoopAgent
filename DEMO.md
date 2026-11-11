# Demo bài chính · Day 04

## Trình bày trong 3–5 phút

1. Agent tự viết bằng Python, không dùng framework. LLM chọn tool; Python thực
   thi và trả observation vào lịch sử hội thoại, sau đó gọi LLM tiếp.
2. Mỗi model call là một step. Giữ nguyên assistant message để không mất tool
   call và thông tin provider; trả tool result với đúng tool_call_id. Xử lý hết
   các calls trước khi gọi model lượt tiếp.
3. Provider lỗi thì trả error và trace; tool lỗi thì trả observation để model
   có thể báo thiếu dữ liệu hoặc sửa tham số. Output bị cắt không được completed.
4. Demo H1: agent theo liên kết incident GitHub rồi đối chiếu Cloudflare.
   Bản before chưa nêu timeline bị lược bỏ; bản after có cảnh báo 3/9 updates,
   truncated=true và URL nguồn. H1 tăng từ 96 lên 100.
5. Demo kiểm tra nguồn bằng E2 after: trace có validation_missing_source khi
   draft thiếu URL; model nhận yêu cầu sửa, rồi trả câu trả lời có nguồn.
6. Điểm toàn bộ tăng 99,77 lên 100; calls tăng 56 lên 59, token agent tăng khoảng
   24,60%. Judge là ước lượng, không phải điểm chấm lab. Một lần chạy chưa đủ
   chứng minh ổn định; cả prompt và kiểm tra nguồn thay đổi nên chưa tách được
   đóng góp của từng thay đổi.

## Demo bằng dữ liệu đã chạy thật, không gọi API

Các lệnh chỉ đọc file eval, không thay đổi kết quả và không dùng API key:

```powershell
python demo_trace.py --file eval_before.json --case H1
python demo_trace.py --file eval_after.json --case H1
python demo_trace.py --file eval_after.json --case E2
```

Đây là phát lại trace đã lưu, không phải một lần chạy model mới.

## Tái chạy với Gemini khi cần

Đặt key vào GEMINI_API_KEY trên máy, không đưa key vào tài liệu hoặc Git.

```powershell
$env:PROVIDER = "gemini"
$env:MODEL = "gemini-3.8-flash"
$env:JUDGE_PROVIDER = "gemini"
$env:JUDGE_MODEL = "gemini-3.8-flash"
$env:GEMINI_API_MODE = "native"
python run.py 'GitHub Actions hiện có sự cố không? Hãy kiểm tra incident gần đây.'
```

Lần chạy mới gọi API thật, có thể dùng quota và sinh kết quả khác. Không cần
chạy lại hai bộ eval đã hoàn thành chỉ để demo.

## Các câu hỏi cần giải thích được

- Vì sao tool_call_id phải đúng? Để provider ghép observation với yêu cầu tool.
- Vì sao nhiều calls phải xử lý hết? Mỗi yêu cầu tool cần có kết quả tương ứng.
- Vì sao snapshot không trả lời được trạng thái hiện tại? Dữ liệu đã được lưu
  từ thời điểm trước đó, không phải đọc status trực tiếp.
- Vì sao 3/9 updates cần cảnh báo? Chưa có toàn bộ timeline để kết luận đầy đủ.
- Kiểm tra nguồn có chứng minh mọi claim đúng không? Không; chỉ kiểm tra có ít
  nhất một URL incident đã quan sát xuất hiện trong câu trả lời.
- Vì sao dùng native Gemini? Chế độ thử nghiệm tương thích API gốc. Không khẳng
  định việc đổi endpoint đã giải quyết 429; nguyên nhân các lỗi trước chưa rõ.
- Vì sao có eval_baseline.py? Chạy hàm agent đã lưu trước cải tiến với nguyên bộ
  evaluator, không sửa dataset, expected hoặc grading.

## Kiểm tra offline trên PowerShell

Một số tests gốc kiểm tra adapter mặc định, nên bỏ biến mode native trong lúc
chạy tests rồi khôi phục. Không cần key và không gọi Internet.

```powershell
$savedGeminiMode = $env:GEMINI_API_MODE
Remove-Item Env:GEMINI_API_MODE -ErrorAction SilentlyContinue
python -m unittest discover -s tests -v
python -m unittest discover -s bonus -p 'test_*.py' -v
$env:GEMINI_API_MODE = $savedGeminiMode
```

## Đưa bài lên GitHub

Chạy từng lệnh riêng, sau khi đã đọc code và NOTES.md:

```powershell
git add .gitignore agent.py providers.py NOTES.md DEMO.md demo_trace.py eval_baseline.py versions/agent_before_source_validation.py tests/test_robustness.py tests/test_gemini_native.py eval_before.json eval_after.json
git diff --cached --stat
git commit -m "Complete status agent loop and before-after evaluation"
git push origin main
```

Các script chẩn đoán key/API được giữ tại máy; danh sách trên không đưa chúng
hoặc bản sao lưu eval chưa đủ case vào commit. Không dùng git add .env.

Mở repo để kiểm tra đã có agent.py, NOTES.md và hai file eval; sau đó tự dán link
repo vào bài Day 04 trên LMS bằng tài khoản cá nhân:

https://github.com/NTD-DUONG/K5-L3A-DAY04-NguyenThuyDuong-2A202603388-ReactLoopAgent

https://aithucchien.vinuni.edu.vn

## Demo bonus

eval_bonus.json đủ 10/10 case scored, điểm 100/100, quy đổi tham khảo 15/15.
Chi tiết và giới hạn trong BONUS_NOTES.md; 41 tests chính và 9 tests bonus đạt.

```powershell
python demo_trace.py --file eval_bonus.json --case B2
python demo_trace.py --file eval_bonus.json --case B4
```

B2 thể hiện pagination 0 → 3 → 6. B4 thể hiện Vercel bị 429 ba lần, lần cuối
retry_allowed=false; agent dừng và vẫn báo thông tin GitHub. Đây là 429 giả lập
của status tool, không phải lỗi quota của Gemini.

Các file bổ sung cho commit bonus: agent.py, bonus_policy.py, bonus/test_policy.py,
eval_bonus.json, BONUS_NOTES.md, NOTES.md, DEMO.md và demo_trace.py.
