---
title: "Multi-role personas + FB Community content"
description: "Add role selector (B2B/B2C/Technician), role-specific prompts, and Facebook Community tab with rule-compliant posting"
status: pending
priority: P1
effort: 6h
branch: feat/multi-role-fb-community
tags: [roles, prompts, ui, fb-community, design]
created: 2026-03-17
---

# Multi-Role Personas + Facebook Community Expansion

## Current State Summary

The app has 5 source files:
- `app.py` — 7 Flask routes: `/api/generate`, `/api/research`, `/api/image`, `/api/design`, `/api/upload-image`, plus static serving
- `agent.py` — `EpioneSalesAgent` class with `generate()`, `generate_from_image()`, `research_from_url()`. Calls `get_prompt(content_type)` to get system prompt
- `prompts.py` — `BRAND_CONTEXT` + `WRITING_STYLE` constants, 8 content-type prompts (linkedin, facebook, outreach, ideas, casestudy, research, image, topic). All hardcoded to B2B sale persona. `get_prompt(content_type)` returns formatted prompt
- `design_generator.py` — `DesignGenerator.create_post()` generates branded HTML posts with gradient overlay, Epione logo, headline/subtext/CTA
- `templates/index.html` — SPA with tabs, JS calls `/api/generate` with `{type, prompt}`

Key insight: The `get_prompt()` function is the single control point. All content flows through `agent.generate(content_type, user_input)` -> `get_prompt(content_type)` -> Claude API. Adding roles means extending this function to accept a `role` parameter.

---

## Architecture Decision

**Approach: Role as a prompt modifier, not a separate agent class.**

Reason: The agent logic (call Claude, manage history) is identical across roles. Only the system prompt changes. So the cheapest, most correct change is:
1. Add `ROLE_CONTEXT` dict in `prompts.py` (parallel to `BRAND_CONTEXT`)
2. Change `get_prompt(content_type)` -> `get_prompt(content_type, role="sale_b2b")`
3. Each prompt template gets `{role_context}` injected alongside `{brand_context}`
4. Frontend sends `role` alongside `type` in every API call

For FB Community: add a new content type `"fb_community"` with its own prompt that includes community rules from user input.

---

## Phase 1: Role System in prompts.py (~1.5h)

### 1.1 Add ROLE_CONTEXTS dict

```python
ROLE_CONTEXTS = {
    "sale_b2b": """
## VAI TRO: Sale B2B
- Ban la sale B2B Epione, tu van giai phap khong gian lam viec cho doanh nghiep
- Giong: chuyen nghiep, tu van (consultative selling), empathy voi pain point doanh nghiep
- Doi tuong: CEO, HR Director, Office Manager, PM cong ty thau D&D
- Goc nhin: ROI, nang suat nhan vien, giai phap tong the, du an lon
- Cach xung ho: "toi"/"minh" nhu dang chia se kinh nghiem tu van
""",
    "sale_b2c": """
## VAI TRO: Sale B2C
- Ban la tu van vien Epione cho khach hang ca nhan va ho gia dinh
- Giong: than thien, gan gui, tap trung vao loi ich ca nhan
- Doi tuong: freelancer lam viec tai nha, nguoi quan tam suc khoe khi ngoi lam viec, gia dinh setup home office
- Goc nhin: suc khoe ca nhan, trai nghiem su dung, tham my khong gian song
- Cach xung ho: "minh" nhu dang chia se voi ban be
- KHONG dung tu chuyen nganh qua sau, KHONG noi ve ROI doanh nghiep
""",
    "ky_thuat_vien": """
## VAI TRO: Ky thuat vien / Chuyen gia
- Ban la chuyen gia ky thuat ve booth cach am va noi that ergonomic
- Giong: chuyen mon, giao duc, chia se kien thuc thuc te
- Doi tuong: nguoi quan tam den ky thuat, cach lam, nguyen ly hoat dong
- Goc nhin: thong so ky thuat, cach lap dat, bao tri, so sanh ky thuat
- Cach xung ho: "toi" nhu chuyen gia dang giai thich
- TAP TRUNG vao: cach am hoat dong the nao, ergonomic la gi, huong dan chon san pham theo ky thuat
""",
}
```

### 1.2 Modify get_prompt()

```python
def get_prompt(content_type: str, role: str = "sale_b2b") -> str:
    role_context = ROLE_CONTEXTS.get(role, ROLE_CONTEXTS["sale_b2b"])

    prompts = {
        "linkedin": LINKEDIN_PROMPT.format(
            brand_context=BRAND_CONTEXT,
            writing_style=WRITING_STYLE,
            role_context=role_context,
        ),
        # ... same for all other prompts
    }
    return prompts.get(content_type, prompts["linkedin"])
```

### 1.3 Add `{role_context}` to each prompt template

Every prompt template (LINKEDIN_PROMPT, FACEBOOK_PROMPT, etc.) gets `{role_context}` added after the first line. Example:

```python
LINKEDIN_PROMPT = """{role_context}

{brand_context}

{writing_style}

Viet bai LinkedIn...
"""
```

The opening line of each prompt currently says "Ban la sale B2B o Epione..." -- these lines should be REMOVED because the role context now handles this. Each prompt should focus only on the content type format/structure.

### 1.4 Adjust WRITING_STYLE per role (optional, defer)

`WRITING_STYLE` can stay shared. The role context already overrides tone. If needed later, create `WRITING_STYLE_B2C` etc., but YAGNI for now.

---

## Phase 2: Agent + API Changes (~0.5h)

### 2.1 agent.py — pass role through

```python
def generate(self, content_type: str, user_request: str, role: str = "sale_b2b") -> str:
    system_prompt = get_prompt(content_type, role=role)
    # ... rest unchanged
```

Same for `generate_from_image()` and `research_from_url()`.

### 2.2 app.py — extract role from request

In `/api/generate`:
```python
role = data.get("role", "sale_b2b")
result = agent.generate(content_type, user_input, role=role)
```

In `/api/image`:
```python
role = request.form.get("role", "sale_b2b")
result = agent.generate_from_image(image_path=filepath, user_request=extra, platform="instagram", role=role)
```

In `/api/research`:
```python
role = data.get("role", "sale_b2b")
# pass to agent.research_from_url (needs role param added)
```

---

## Phase 3: UI Role Selector (~1h)

### 3.1 Add role selector in the nav bar (global, affects all tabs)

Place it in the `.nav` element, right side. It's a small button group, always visible.

```html
<div class="role-selector">
  <span class="role-label">Vai tro:</span>
  <button class="role-btn active" data-role="sale_b2b">Sale B2B</button>
  <button class="role-btn" data-role="sale_b2c">Sale B2C</button>
  <button class="role-btn" data-role="ky_thuat_vien">Ky thuat</button>
</div>
```

CSS: reuse existing `.tab` / `.plat-chip` pattern -- pill buttons, highlight active.

### 3.2 JS: Track selected role, send with all API calls

```javascript
let currentRole = 'sale_b2b';

document.querySelectorAll('.role-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.role-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    currentRole = btn.dataset.role;
  });
});
```

In `generate()`:
```javascript
body: JSON.stringify({ type: currentType, prompt, role: currentRole })
```

In `analyzeImage()`:
```javascript
formData.append('role', currentRole);
```

In `generateFromTopic()`:
```javascript
body: JSON.stringify({ type: 'topic', prompt: ..., role: currentRole })
```

### 3.3 Update nav subtitle to reflect current role

When role changes, update `.nav-sub` text:
- sale_b2b: "B2B Sales Content Agent"
- sale_b2c: "B2C Sales Content Agent"
- ky_thuat_vien: "Technical Content Agent"

---

## Phase 4: FB Community Tab (~2h)

### 4.1 New tab in index.html

Add between existing tabs:
```html
<button class="tab" data-type="fb_community">Cong dong FB</button>
```

### 4.2 New mode card: `mode-fb-community`

UI flow:
1. **Community name** (text input) -- e.g., "Hoi thiet ke noi that"
2. **Community rules** (textarea) -- user pastes the group's rules here
3. **Topic/prompt** (textarea) -- what to write about
4. **Generate button**

```html
<div class="card mode-card" id="mode-fb-community" style="display:none">
  <h2>Viet bai cho Cong dong Facebook</h2>
  <p class="desc">Tao bai viet tuan thu quy dinh nhom FB -- dan cau hoi, chia se kinh nghiem, khong quang cao lo lieu</p>

  <label class="step-label">Ten cong dong</label>
  <input type="text" id="fb-community-name" placeholder="VD: Hoi thiet ke noi that Viet Nam">

  <label class="step-label" style="margin-top:16px;">Quy dinh nhom (paste quy dinh vao day)</label>
  <textarea id="fb-community-rules" placeholder="Paste quy dinh cua nhom FB vao day... VD: Khong dang quang cao, khong spam link..." style="min-height:80px;"></textarea>

  <label class="step-label" style="margin-top:16px;">Noi dung muon viet</label>
  <textarea id="fb-community-prompt" placeholder="VD: Chia se kinh nghiem chon booth cach am cho van phong nho"></textarea>

  <div style="margin-top:14px; display:flex; gap:8px; align-items:center;">
    <button class="btn btn-primary" id="btn-fb-community" onclick="generateFBCommunity()">Tao bai viet</button>
    <div class="loading" id="loading-fb-community">
      <div class="spinner"></div>
      <span>Dang viet...</span>
    </div>
  </div>
</div>
```

### 4.3 Community rules storage (localStorage)

Save rules per community name so user doesn't re-paste every time:

```javascript
function saveCommunityRules(name, rules) {
  const saved = JSON.parse(localStorage.getItem('fb_community_rules') || '{}');
  saved[name] = rules;
  localStorage.setItem('fb_community_rules', JSON.stringify(saved));
}

function loadCommunityRules(name) {
  const saved = JSON.parse(localStorage.getItem('fb_community_rules') || '{}');
  return saved[name] || '';
}
```

Auto-load when community name input changes (on blur). Auto-save when generating.

Optional: dropdown of previously saved communities.

### 4.4 JS: generateFBCommunity()

```javascript
async function generateFBCommunity() {
  const name = document.getElementById('fb-community-name').value.trim();
  const rules = document.getElementById('fb-community-rules').value.trim();
  const prompt = document.getElementById('fb-community-prompt').value.trim();
  if (!prompt) return;

  // Save rules
  if (name && rules) saveCommunityRules(name, rules);

  const fullPrompt = [
    name ? `Cong dong: ${name}` : '',
    rules ? `QUY DINH NHOM:\n${rules}` : '',
    `Noi dung can viet: ${prompt}`,
  ].filter(Boolean).join('\n\n');

  setLoading('loading-fb-community', true);
  try {
    const res = await fetch('/api/generate', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ type: 'fb_community', prompt: fullPrompt, role: currentRole })
    });
    const data = await res.json();
    if (data.error) throw new Error(data.error);
    showOutput(data.content);
  } catch (e) {
    showOutput('Loi: ' + e.message);
  } finally {
    setLoading('loading-fb-community', false);
  }
}
```

### 4.5 Tab switching logic update

In the tab click handler, add `fb_community` case:
```javascript
} else if (currentType === 'fb_community') {
  document.getElementById('mode-fb-community').style.display = 'block';
}
```

### 4.6 New prompt in prompts.py: FB_COMMUNITY_PROMPT

```python
FB_COMMUNITY_PROMPT = """{role_context}

{brand_context}

{writing_style}

## NHIEM VU: Viet bai cho CONG DONG FACEBOOK

Bai viet nay se dang trong NHOM Facebook (khong phai fanpage). Quy tac:

1. KHONG quang cao truc tiep. Chia se kien thuc, kinh nghiem, cau hoi, hoac thao luan.
2. Giong van nhu thanh vien binh thuong dang hoi/chia se, KHONG phai brand dang dang.
3. Khong dung logo, khong goi ten brand o dau bai.
4. Co the nhac den san pham/giai phap mot cach tu nhien nhu "minh dang dung loai booth XYZ" hoac tra loi khi ai hoi.
5. Neu co QUY DINH NHOM, PHAI tuan thu 100%.

Format bai:
- Mo: cau hoi hoac chia se thuc te (1-2 cau)
- Than: noi dung chinh, ngan gon (3-5 cau)
- Ket: cau hoi mo de tao thao luan

DO DAI: 50-100 tu. Ngan hon bai LinkedIn/Facebook brand.

Chi viet NOI DUNG bai dang, san sang copy-paste. KHONG kem ghi chu, phan tich.
"""
```

Add to `get_prompt()` dict:
```python
"fb_community": FB_COMMUNITY_PROMPT.format(
    brand_context=BRAND_CONTEXT,
    writing_style=WRITING_STYLE,
    role_context=role_context,
),
```

---

## Phase 5: Community Design Post (Optional, ~1h)

### 5.1 Community post design = simpler than brand post

FB community posts should NOT look like brand ads. Two options:
- **Option A (recommended):** No design generation for community posts. Just text. Community posts that look designed = instant spam flag.
- **Option B:** Minimal design -- no brand logo, no CTA button, just clean text card or simple image+text. More like an "infographic snippet."

**Decision: Skip design for community posts.** The value of community posts is authenticity. Adding Epione branding defeats the purpose. If user wants design, they can use the existing "Anh -> Content" tab.

---

## Implementation Checklist

### Files to modify:

| File | Changes |
|------|---------|
| `prompts.py` | Add `ROLE_CONTEXTS` dict, add `FB_COMMUNITY_PROMPT`, modify `get_prompt()` to accept `role` param, add `{role_context}` to all prompt templates, remove hardcoded "sale B2B" from prompt opening lines |
| `agent.py` | Add `role` param to `generate()`, `generate_from_image()`, `research_from_url()`. Pass to `get_prompt()` |
| `app.py` | Extract `role` from request data in `/api/generate`, `/api/image`, `/api/research` routes. Pass to agent methods |
| `templates/index.html` | Add role selector in nav, add FB Community tab + mode card, add `currentRole` JS variable, send `role` in all fetch calls, add `generateFBCommunity()`, add localStorage logic for community rules, update tab switching |

### No new files needed.

### No new dependencies.

---

## Execution Order

1. **prompts.py** first -- this is the core change, can be tested with `python -c "from prompts import get_prompt; print(get_prompt('linkedin', 'sale_b2c')[:200])"`
2. **agent.py** -- add role param, trivial
3. **app.py** -- extract role from requests, trivial
4. **templates/index.html** -- UI changes, test in browser

Each phase is independently testable. Phase 1-3 can be done without any frontend changes (default role = sale_b2b = current behavior).

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Prompt too long with role_context + brand_context + writing_style | Higher token cost, possible truncation | Role context is ~100 words each. Total prompt ~800 words. Well within limits. |
| Community rules paste = very long text | Could exceed context window | Rules go in user message, not system prompt. Claude handles long user messages fine. Cap at textarea maxlength if needed. |
| Role selector confusing for single-user app | User forgets to switch role | Show current role prominently in nav. Subtitle text changes to confirm. |
| localStorage for community rules lost on clear | Minor inconvenience | Acceptable for v1. Can add JSON export/import later if needed. |

---

## Out of Scope (Deferred)

- Per-role `WRITING_STYLE` variants -- current shared style works. Revisit if B2C tone needs fundamentally different rules.
- Community rules auto-fetch from FB URL -- requires FB login/scraping, fragile. Manual paste is reliable.
- Role-specific topic chips in the "Chon chu de" tab -- current topics are B2B focused. Can add role-aware topics later.
- Multi-language support -- all Vietnamese for now.
- Community post analytics/history.
