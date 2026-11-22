---
title: "Hướng dẫn cài đặt — Gacha Setup cho Blender"
description: "Cách cài đặt add-on Gacha Setup trong Blender (khuyên dùng Blender 5.3, hỗ trợ Blender/Goo Engine 4.1+) với hỗ trợ FBX, BetterFBX và VMD."
---

# Hướng dẫn cài đặt

:::note[Khả năng tương thích của Blender]
**Khuyên dùng Blender 5.2.** Gacha Setup cũng tương thích với **Blender/Goo Engine 4.1+**. Nếu bạn sử dụng Blender **dưới 4.5**, hãy cài đặt **BetterFBX** để nhập mô hình.
:::

## Cài đặt từng bước

1. Tải xuống gói phát hành `Gacha_Setup-<version>.zip` mới nhất từ GitHub Releases.
2. Khởi chạy Blender 5.2 (khuyên dùng) hoặc Blender/Goo Engine 4.1+. Trên các phiên bản Blender dưới 4.5, hãy cài đặt BetterFBX trước.
3. Mở **Edit > Preferences > Add-ons**.
4. Nhấp vào menu thả xuống ở góc trên bên phải và chọn **Install from Disk...**
5. Chọn tệp `.zip` đã tải xuống và bật hộp kiểm của add-on.
6. Nhấn <kbd>N</kbd> trong 3D Viewport để mở bảng thanh bên **Character Setup Wizard**.

---

## Các phần phụ thuộc đi kèm

Add-on sẽ tự động kiểm tra và cài đặt các phần phụ thuộc con cần thiết khi được bật:

- **ExpyKit**: Tự động hóa việc chuyển đổi nhân vật Rigify.
- **UEFormat**: Cho phép nhập trực tiếp các mô hình Neverness to Everness (`.ueformat`).

---

:::tip[Mẹo nhanh]
Tại đây sẽ bổ sung thêm thông tin chi tiết về các tùy chọn cấu hình, kiểm tra cài đặt phần phụ thuộc tự động và khắc phục sự cố thiếu phần phụ thuộc.
:::
