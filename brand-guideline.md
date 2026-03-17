# Focus by Epione - Brand Guideline

---

## 1. Logo

### Logo Mark (Icon)
Biểu tượng chính: **Pulse Rings** - 3 vòng tròn đồng tâm tỏa ra từ 1 chấm tròn solid ở giữa. Tượng trưng cho sự tập trung (focus) và sóng kết nối.

**Cấu trúc:**
- Vòng ngoài: r=55, stroke 1.5px, opacity 25%
- Vòng giữa: r=42, stroke 2px, opacity 40%
- Vòng trong: r=28, stroke 2.5px, opacity 65%
- Chấm center: r=12, solid fill

### Logo Full (Icon + Wordmark)
- Icon bên trái, wordmark bên phải
- "FOCUS" - Bold 700, letter-spacing 3-4px
- "by Epione" - Regular 400, letter-spacing 1.5-2px

### Các phiên bản
| File | Mô tả |
|------|--------|
| `logo-icon.svg` | Icon only - nền sáng |
| `logo-icon-white.svg` | Icon only - nền tối |
| `logo-full.svg` | Full logo - nền sáng |
| `logo-full-white.svg` | Full logo - nền tối |

### Quy tắc sử dụng
- Khoảng cách an toàn (clear space): bằng đường kính chấm center (r=12) ở tất cả các phía
- Không xoay, kéo méo, đổ bóng, hoặc thay đổi tỷ lệ icon/text
- Kích thước tối thiểu: icon 24px, full logo 120px width
- Trên nền sáng: dùng bản default. Trên nền tối (#282828 hoặc đậm hơn): dùng bản white

---

## 2. Color Palette

### Primary Colors

| Tên | Hex | RGB | Sử dụng |
|-----|-----|-----|---------|
| **Accent** | `#10069F` | 16, 6, 159 | Brand chính, CTA, links, active states |
| **Accent Dark** | `#0A0470` | 10, 4, 112 | Hover states, emphasis |
| **Black** | `#282828` | 40, 40, 40 | Text chính, headings |
| **White** | `#FFFFFF` | 255, 255, 255 | Background chính |

### Secondary Colors

| Tên | Hex | Sử dụng |
|-----|-----|---------|
| **Gray** | `#EDEDED` | Borders, dividers, background phụ |
| **Text Secondary** | `#888888` | Body text phụ, captions |
| **Text Hint** | `#BBBBBB` | Placeholder, disabled text |

### Semantic Colors

| Tên | Hex | Sử dụng |
|-----|-----|---------|
| **Success** | `#22C55E` | Trạng thái thành công, online |
| **Warning** | `#F59E0B` | Cảnh báo |
| **Error** | `#EF4444` | Lỗi, trạng thái nguy hiểm |

### Glow / Overlay

| Tên | Value | Sử dụng |
|-----|-------|---------|
| **Glow 1** | `rgba(16,6,159, 0.08)` | Hover glow gần |
| **Glow 2** | `rgba(16,6,159, 0.04)` | Hover glow xa |
| **Icon BG** | `rgba(16,6,159, 0.06)` | Background cho icon containers |

### Splash Screen (Dark Theme)

| Tên | Hex | Sử dụng |
|-----|-----|---------|
| **Splash BG** | `#0A0520` | Background splash screen |
| **Splash Text** | `#7070CC` | Text trên splash |
| **Splash Muted** | `#5050AA` | Text phụ trên splash |

---

## 3. Typography

### Font Family
**Nunito Sans** - Google Fonts
```
https://fonts.googleapis.com/css2?family=Nunito+Sans:wght@400;500;600;700&display=swap
```

### Font Weights

| Weight | Name | Sử dụng |
|--------|------|---------|
| 400 | Regular | Body text, captions, "by Epione" |
| 500 | Medium | Emphasis nhẹ |
| 600 | SemiBold | Buttons, labels, nav items |
| 700 | Bold | Headings, "FOCUS" wordmark, card titles |

### Type Scale (Mobile-first)

| Element | Size | Weight | Letter-spacing |
|---------|------|--------|----------------|
| Logo "FOCUS" | 16px | 700 | 3px |
| Logo "by Epione" | 9px | 400 | 1.5px |
| H1 | 28-32px | 700 | - |
| H2 Section | 22-24px | 700 | - |
| H3 Card Title | 14-16px | 700 | - |
| Body | 14px | 400 | - |
| Caption | 11-13px | 400 | - |
| Button | 13-14px | 600 | - |
| Badge | 10-11px | 600 | - |

### Line Height
- Body text: 1.6
- Headings: 1.2-1.3
- UI elements: 1.0-1.2

---

## 4. Spacing & Layout

### Spacing Scale

| Token | Value | Sử dụng |
|-------|-------|---------|
| `--space-gap` | 8px | Gap nhỏ giữa elements |
| `--space-card` | 12px | Padding trong card |
| `--space-page` | 16px | Padding page, margin giữa sections |
| `--space-section` | 16px | Khoảng cách giữa sections |

### Border Radius

| Token | Value | Sử dụng |
|-------|-------|---------|
| `--radius-badge` | 10px | Badges, tags |
| `--radius-input` | 8px | Input fields |
| `--radius-thumb` | 8px | Thumbnails |
| `--radius-card` | 12px | Cards, containers |
| `--radius-sheet` | 16px | Bottom sheets, modals |
| `--radius-button` | 24px | Buttons (pill shape) |

### Max Width
- Content container: **1080px** (desktop)
- Mobile-first design, scale up

---

## 5. Component Patterns

### Buttons
- **Primary**: Background `#10069F`, text white, radius 24px, padding 10-14px 20-28px
- **Outline**: Border `#EDEDED`, text `#10069F`, transparent bg
- **Hover**: Background darkens to `#0A0470`, glow effect với box-shadow
- Font: Nunito Sans 600, 13-14px

### Cards
- Background white, border 1px `#EDEDED`, radius 12px
- Hover: border-color chuyển sang `#10069F`, glow shadow
- Padding: 16-20px

### Navigation
- Fixed top, background `rgba(255,255,255,0.92)` + backdrop-filter blur(20px)
- Border bottom: 0.5px `#EDEDED`
- Logo trái, CTA phải

### Icons
- Container: 44-56px, background `rgba(16,6,159,0.06)`, border-radius 12px
- Sử dụng inline SVG, stroke style, color `#10069F`

---

## 6. Animation

### Pulse Logo Animation
```css
@keyframes pulse-ring {
  0%, 100% { transform: scale(1); opacity: var(--ring-opacity); }
  50% { transform: scale(1.04); opacity: calc(var(--ring-opacity) * 1.3); }
}
```
- Duration: 2s, ease-in-out, infinite
- Staggered delay: 0s, 0.15s, 0.3s cho 3 rings

### General Transitions
- UI transitions: `all 0.2s ease`
- Hover effects: scale + glow
- Không dùng animation quá 3s

---

## 7. Brand Voice

### Tên thương hiệu
- **Chính thức**: Focus by Epione
- **Sản phẩm**: FocusBooth
- **Logo text**: "FOCUS" (all caps) + "by Epione" (sentence case)

### Tone of Voice
- Chuyên nghiệp nhưng thân thiện
- Ngắn gọn, rõ ràng, đi thẳng vào vấn đề
- Tự tin nhưng không phô trương
- Data-driven: luôn có số liệu/bằng chứng cụ thể

### Tagline Patterns
- "Đúng người. Đúng lúc. Đo được."
- "Thêm tiện ích, thêm doanh thu, không mất gì"

---

## 8. Do's & Don'ts

### Do
- Dùng đúng màu `#10069F` cho brand accent
- Giữ clear space quanh logo
- Dùng Nunito Sans cho mọi text
- Mobile-first responsive design
- Pill-shaped buttons (radius 24px)

### Don't
- Không dùng gradient trên logo
- Không đổi màu accent sang tone khác
- Không dùng font khác ngoài Nunito Sans
- Không dùng sharp corners cho buttons (luôn bo tròn)
- Không đặt logo trên background có pattern phức tạp
