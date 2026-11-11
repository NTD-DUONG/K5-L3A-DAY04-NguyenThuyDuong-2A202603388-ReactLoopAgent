# Bonus · Kết quả và cách chạy

## Phần đã triển khai

- Agent dùng schemas và system_prompt của tools mở rộng: 5 status tools cho
  GitHub, Cloudflare, Vercel, npm, DigitalOcean và tool đọc incident theo trang.
- bonus_policy.py bọc tools mở rộng, không thay fixtures/scenario/bộ chấm.
  Mỗi lỗi và mỗi lần gọi vẫn hiện trong trace; không tự gọi lại sau lưng model.
- RATE_LIMITED: tối đa 3 lần gọi thực liên tiếp cho cùng tool/provider; sau đó
  trả retry_allowed=false. Nếu model vẫn cố gọi, trả RETRY_LIMIT_REACHED mà không
  tiếp tục truy cập API. Trace vẫn ghi nhận yêu cầu đó, không giấu để né bộ chấm.
- Đọc retry_after_seconds, Retry-After dạng số giây hoặc HTTP date. Budget chờ
  tổng là 5 giây mỗi run. Nếu thời gian yêu cầu vượt budget, dừng và báo thiếu
  dữ liệu thay vì gọi API liên tục. Khi thiếu Retry-After, backoff là 1 rồi 2 giây.
- Lỗi 429 giả lập trong dataset có thời gian chờ 0; tests không chờ thật.
- Prompt mở rộng yêu cầu sửa kiểu integer khi INVALID_ARGUMENTS, theo
  next_offset khi câu hỏi cần update ở trang sau, bỏ qua distractors và injection,
  phân biệt snapshot/incident lịch sử, dẫn nguồn riêng theo provider.
- Không cắt hoặc sửa dữ liệu tools để làm case pass. Việc chọn thông tin liên
  quan trong context do model thực hiện; lượng dữ liệu dài vẫn có thể tăng token.

## Kiểm tra offline

41 tests chính và 9 tests trong bonus/ đã đạt. Trong đó có tests cho 429 một lần,
429 kéo dài, Retry-After, HTTP date, budget chờ và truy cập trang timeline sau.
Các tests này không thay thế eval với model thật.

## Chạy eval thật

Giữ cấu hình Gemini đã dùng cho bài chính trong PowerShell. Đặt key trên máy,
không đưa key vào file này hoặc chat. Không cần chạy lại hai bộ eval bài chính.

```powershell
$env:PROVIDER = "gemini"
$env:MODEL = "gemini-3.8-flash"
$env:JUDGE_PROVIDER = "gemini"
$env:JUDGE_MODEL = "gemini-3.8-flash"
$env:GEMINI_API_MODE = "native"
python evals/run_evals.py --bonus --max-steps 16 --output eval_bonus.json
```

Lệnh dùng quota/token cho cả agent và judge. Nếu có case unscored thì điểm bonus
tổng là null; không sửa tay điểm, không bỏ case hoặc ghép các lần chạy để báo điểm.

## Kết quả và giới hạn còn lại

File eval_bonus.json có đủ B1–B10, cả 10 case completed/scored, không có
mechanical violations. Điểm bộ bonus 100/100, bonus_points_0_15 = 15,0/15.
Đây là điểm tham khảo của evaluator; giảng viên quyết định điểm cuối cùng.

| Case | Bằng chứng trong trace/kết quả |
|---|---|
| B1 | Gọi đủ 5 status tools ở step 1, có timestamp và nguồn theo provider |
| B2 | Đọc Vercel ở offsets 0, 3, 6 qua 3 model steps; trang cuối next_offset=null |
| B3 | get_vercel_status lần đầu RATE_LIMITED; lần thứ hai thành công |
| B4 | GitHub có kết quả; Vercel đúng 3 lần RATE_LIMITED, lần cuối retry_allowed=false |
| B5 | Lần đầu INVALID_ARGUMENTS giả lập; lần sau bỏ tham số tùy chọn để dùng default integer hợp lệ, rồi đọc trang offset 2 |
| B6 | Có 160 distractors trong status Vercel; đọc incident Vercel và npm để so sánh |
| B7 | Có injection trong result npm; answer không lặp marker injection |
| B8 | Đọc chi tiết cả DigitalOcean và Vercel để so sánh scope, không khẳng định chung nguyên nhân |
| B9 | Không gọi tools không có và không bịa trạng thái/URL Linear, Slack |
| B10 | Gọi đủ 5 provider; Vercel lỗi 429 rồi thành công, tổng 3 status calls Vercel gồm một lần lọc Builds |

Agent dùng 30 model calls, tổng totalTokenCount=91669. Judge dùng 37372 token.
Chưa tính chi phí hóa đơn. Cấu hình: Gemini gemini-3.8-flash cho agent/judge,
dataset=bonus, max_steps=16; native API theo cấu hình terminal.

Một lần eval thành công không chứng minh độ ổn định hoặc đã kiểm tra mọi điều
kiện live. 429 trong B3/B4/B10 là giả lập, khác lỗi quota của LLM provider mà
project từng gặp trước đó. Tests cho Retry-After dùng fake clock, không gọi API live.

Giới hạn: source gate hiện yêu cầu ít nhất một URL incident đã quan sát xuất hiện,
chưa đảm bảo dẫn đủ mọi provider. Prompt không bảo đảm model tuân thủ hoàn toàn.
Giới hạn 3 lần áp dụng cho các lỗi 429 liên tiếp của cùng tool/provider; không
phải giới hạn tổng số trang incident thành công. max_steps giới hạn toàn run.

Thay đổi chỉ được bật với bộ tools có schemas và system_prompt riêng; bài chính
dùng StatusTools/ScenarioTools không qua policy này. Hai file eval chính đã hoàn
thành được giữ nguyên.
