# Ghi chú phân tích · Day 04

Họ và tên: Nguyễn Thùy Dương
MSSV: 2A202603388

## 1. Case được chọn

- H1: 96/100. Điểm bộ before: 99,77/100; đủ 22/22 case scored.
- Cấu hình: Gemini gemini-3.8-flash cho agent và judge, native API,
  snapshot core, max_steps=8, workers=1.
- Agent đọc incident GitHub ban đầu, incident liên quan và Cloudflare; đối chiếu
  thời gian/phạm vi, kết luận không có bằng chứng chung nguyên nhân.
- Answer chưa nêu dữ liệu bị cắt và không chứa URL incident trực tiếp.
  Judge chỉ ra thiếu lưu ý về truncated và số updates không đầy đủ.

## 2. Bằng chứng trong trace

Trong eval_before.json, case H1 có tool event get_incident_details cho GitHub
incident xr3myzj7ms51. Result có updates_total: 9, nhưng updates chỉ có 3 phần tử;
update tổng hợp có truncated: true. URL là https://stspg.io/pjgptg3cfc6n.

Tool đã báo giới hạn dữ liệu, nhưng answer không giải thích giới hạn đó.
Prompt ban đầu chỉ nhắc chung về giới hạn bằng chứng, chưa nêu rõ cách phản ứng
với hai dấu hiệu này. Đây là nguyên nhân có thể xảy ra, chưa chứng minh nhân quả.

Answer H1 không chứa URL nào trong ba URL incident đã quan sát, nhưng judge vẫn
cho evidence 20/20. Do đó phải đọc trace và answer, không chỉ tin điểm judge.

## 3. Thay đổi đã thực hiện

- agent.py: bổ sung prompt yêu cầu nêu rõ dữ liệu bị cắt hoặc timeline không
  đầy đủ khi có truncated=true hoặc updates_total lớn hơn số updates trả về.
- Nhắc rằng một incident không ảnh hưởng người dùng không loại trừ nguyên nhân
  khác, phù hợp gợi ý judge của A2 (99/100).
- Kiểm tra nguồn: lưu URL từ get_incident_details thành công; nếu final answer
  không chứa URL nào đã quan sát, ghi validation_missing_source và yêu cầu model
  sửa trong budget. Hết lượt thì trả max_steps.
- Phiên bản trước kiểm tra nguồn và prompt mới nằm ở
  versions/agent_before_source_validation.py, chạy bằng eval_baseline.py.
- Xử lý lỗi provider/tool và hỗ trợ schemas/prompt riêng có ở cả hai phiên bản,
  không phải biến thay đổi trong phép so sánh này.
- Không sửa fixtures, dataset hay bộ chấm để tăng điểm.

## 4. So sánh hai lần chạy

| Chỉ số | eval_before.json | eval_after.json |
|---|---|---|
| Điểm tổng | 99,77 | 100,00 |
| Điểm H1 | 96 | 100 |
| Điểm A2 | 99 | 100 |
| Model calls của agent | 56 | 59 |
| Tổng totalTokenCount của agent | 80071 | 99769 |
| Tổng totalTokenCount của judge | 50914 | 52451 |
| Event validation_missing_source | 0 | 5 |

Hai file có config giống nhau và đều đủ 22/22 case scored, không có case unscored.
Mode native và workers=1 được giữ nguyên theo cấu hình terminal; runner không
ghi hai giá trị này trong config JSON. Chưa tính chi phí vì chưa có dữ liệu hóa đơn.

Điểm tổng tăng 0,23; H1 tăng 4 điểm và A2 tăng 1 điểm. 20 case còn lại giữ 100.
Trong answer H1 sau cải tiến, agent đã nêu rõ incident liên quan có 9 updates
nhưng chỉ trả 3 và có truncated=true, đồng thời dẫn URL của cả GitHub và Cloudflare.
Đây là bằng chứng trực tiếp về thay đổi hành vi, bên cạnh điểm judge.

Đổi lại, số model calls tăng 3 và token agent tăng 19698 (khoảng 24,60%). Có 5
event yêu cầu bổ sung nguồn trong toàn bộ trace sau cải tiến. Không thể quy toàn
bộ token tăng cho source validation vì output và đường gọi tool cũng có thể thay đổi.

Lỗi H1 đã được khắc phục trong lần chạy này. Chưa thấy lỗi mới qua rubric và
mechanical checks, nhưng 100 điểm không chứng minh mọi câu trả lời đều hoàn hảo.
Các giới hạn kiểm tra nguồn và độ ổn định vẫn còn như mục 5.

## 5. Giới hạn

- Judge dùng cùng model với agent nên có thể thiên lệch; H1 thiếu URL nhưng
  evidence vẫn đạt 20/20. Điểm eval không thay thế điểm lab.
- Snapshot ngày 09/11/2026 không chứng minh trạng thái hiện tại.
- Một lần chạy mỗi phiên bản không chứng minh tính ổn định.
- Kiểm tra URL chỉ yêu cầu ít nhất một URL đã quan sát xuất hiện; chưa chứng minh
  mọi claim hoặc mọi provider đều có nguồn đúng.
- Có cả thay đổi prompt và kiểm tra nguồn; không thể quy biến động điểm cho riêng
  một thay đổi nếu không có thí nghiệm bổ sung.
- Các lần trước có 429 và lỗi judge. Hai bản hiện tại đều đủ 22 case scored;
  không bỏ case hoặc sửa tay điểm.
