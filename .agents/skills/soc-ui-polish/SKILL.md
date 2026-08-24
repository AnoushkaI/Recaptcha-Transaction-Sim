---
name: soc-ui-polish
description: Enforces enterprise dark-mode SOC visual design in Streamlit with consistent color-coded action status badges and risk classification badges.
---

# SOC UI Polish — Enterprise Dark-Mode Design Standard

## Color Palette

| State | Color | Hex | Usage |
|---|---|---|---|
| BLOCKED / HIGH_RISK | Crimson | `#EF4444` | Blocked badges, HIGH RISK labels, critical alerts |
| CHALLENGED / SUSPICIOUS | Amber | `#F59E0B` | Challenge badges, SUSPICIOUS labels, warnings |
| ALLOWED / SAFE | Emerald | `#10B981` | Allow badges, SAFE labels, healthy state |
| Background | Deep Navy | `#0B0F17` | Page background |
| Panel | Dark Slate | `#111318` | Card/panel backgrounds |
| Border | Dim Blue | `#1e2433` | Panel borders, dividers |
| Text Primary | Light Slate | `#e2e8f0` | Main text |
| Text Secondary | Muted | `#64748b` | Labels, timestamps, metadata |
| Accent | Blue | `#4f7aff` | Selected states, links |

## Action Status Badge Specification

### 🛑 BLOCKED Badge
```html
<span style="background:rgba(239,68,68,0.18);color:#EF4444;border:1px solid rgba(239,68,68,0.4);
border-radius:5px;padding:3px 10px;font-size:10px;font-weight:800;letter-spacing:0.5px;">
  🛑 BLOCKED BY RULE R-001
</span>
```

### ⚠️ CHALLENGED Badge
```html
<span style="background:rgba(245,158,11,0.18);color:#F59E0B;border:1px solid rgba(245,158,11,0.4);
border-radius:5px;padding:3px 10px;font-size:10px;font-weight:800;letter-spacing:0.5px;">
  ⚠️ CHALLENGED (OTP/CAPTCHA)
</span>
```

### ✅ ALLOWED Badge
```html
<span style="background:rgba(16,185,129,0.12);color:#10B981;border:1px solid rgba(16,185,129,0.3);
border-radius:5px;padding:3px 10px;font-size:10px;font-weight:800;letter-spacing:0.5px;">
  ✅ ALLOWED
</span>
```

## Layout Rules

1. Action badges appear on the **right side** of each transaction card, **below** the Risk Classification badge.
2. The Deploy Prevention Rule CTA must be a **full-width primary button** with a red/orange gradient to convey urgency.
3. SOC Audit Log tab uses a **chronological feed** (newest at top) with colored event-type pills.
4. Active Rules table uses alternating row shading with rule-type labels (`CONDITION RULE`, `CODE RULE`).
5. All timestamps must display in `HH:MM:SS` format in the Audit Log tab.
